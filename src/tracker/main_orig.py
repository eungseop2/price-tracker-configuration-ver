from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from .alert import check_and_alert
from .browser_scraper import (
    BrowserScrapeError,
    collect_lowest_offer_via_browser,
    collect_current_offer_via_browser
)
from .config import TargetConfig, load_config
from .gsheet_store import GoogleSheetStore
from .naver_api import (
    NaverShoppingSearchClient,
    collect_lowest_offer_via_api,
    collect_mall_inventory,
    collect_mall_items,
    _normalized_item,
)
from .notifier import send_price_alert
from .report import send_daily_report
from .util import calc_change_metrics, clean_text, dump_json, utc_now_iso, is_night_time_kst

logger = logging.getLogger("naver_price_tracker")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


async def _collect_one(client: NaverShoppingSearchClient, target: TargetConfig, app_config, artifacts_dir: str) -> dict:
    """?⑥씪 ?寃??섏쭛 諛?NO_MATCH ???먮룞 ?대갚 濡쒖쭅"""
    result = None
    
    if target.mode == "api_query":
        try:
            result = collect_lowest_offer_via_api(client, app_config, target)
        except Exception as e:
            # 401, 429, ?ㅽ듃?뚰겕 ?ㅻ쪟 ?깆? ?대갚?섏? ?딄퀬 ?덉쇅 諛쒖깮 (main 猷⑦봽?먯꽌 泥섎━)
            raise e

        # API 寃곌낵媛 NO_MATCH?닿퀬 fallback_url???덈뒗 寃쎌슦?먮쭔 釉뚮씪?곗? ?대갚
        if result.get("status") == "NO_MATCH" and target.fallback_url:
            logger.info("API NO_MATCH -> Browser ?대갚 ?ㅽ뻾 | %s", target.name)
            fallback_target = TargetConfig(
                name=target.name,
                mode="browser_url",
                url=target.fallback_url,
                browser=target.browser,
                match=target.match,
            )
            fallback_result = await collect_lowest_offer_via_browser(fallback_target, artifacts_dir)
            # ?대갚 ?뺣낫 湲곕줉 猷⑦떞 (status ?ㅼ뿼 湲덉?)
            fallback_result["fallback_used"] = 1
            fallback_result["status"] = "OK"  # ?대갚 ?깃났 ?쒖뿉???쒖닔 OK ?좎?
            return fallback_result
            
        return result

    elif target.mode == "browser_url":
        result = await collect_lowest_offer_via_browser(target, artifacts_dir)
        return result

    else:
        raise ValueError(f"吏?먰븯吏 ?딅뒗 ?섏쭛 紐⑤뱶: {target.mode}")


async def run_once(app_config, artifacts_dir: str, gsheet_id: str, summary_json: str | None = None) -> None:
    ok = 0
    fail = 0
    fallback_used_count = 0
    alerts_triggered_count = 0
    changed_items = []
    # ?곗씠??諛곗튂 ?섏쭛??由ъ뒪??    collected_payloads = []
    
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
    if not service_account_json:
        logger.error("GOOGLE_SERVICE_ACCOUNT_KEY ?섍꼍蹂?섍? ?ㅼ젙?섏? ?딆븯?듬땲??")
        return

    store = GoogleSheetStore(gsheet_id, service_account_json)
    client = NaverShoppingSearchClient(timeout_seconds=app_config.timeout_seconds)

    for target in app_config.targets:
        logger.info("?섏쭛 ?쒖옉 | %s | mode=%s", target.name, target.mode)
        try:
            # 吏곸쟾 ?깃났 湲곕줉 議고쉶 (媛寃?蹂??泥댄겕??
            prev_success = store.get_latest_success(target.name)
            prev_price = prev_success["price"] if prev_success else None

            result = await _collect_one(client, target, app_config, artifacts_dir)
            result["collected_at"] = utc_now_iso()
            result["config_mode"] = target.mode

            # 媛寃?蹂??諛??곹깭 怨꾩궛
            current_price = result.get("price")
            if current_price is not None:
                if prev_price is None:
                    result["price_change_status"] = "FIRST_SEEN"
                else:
                    delta, pct = calc_change_metrics(current_price, prev_price)
                    result["prev_price"] = prev_price
                    result["price_delta"] = delta
                    result["price_delta_pct"] = pct
                    
                    if delta is not None:
                        if delta < 0: result["price_change_status"] = "PRICE_DOWN"
                        elif delta > 0: result["price_change_status"] = "PRICE_UP"
                        else: result["price_change_status"] = "PRICE_SAME"
                    else:
                        result["price_change_status"] = "PRICE_SAME"
            else:
                result["price_change_status"] = None

            # ?꾩닔 ?꾨뱶 蹂댁옣
            result.setdefault("fallback_used", 0)
            result["alert_triggered"] = 0
            
            # ?뚮┝ 泥댄겕
            # ?뚮┝ 泥댄겕 (媛寃?蹂??湲곕컲)
            if result.get("success"):
                ok += 1
                status = result.get("price_change_status")

                # 媛寃⑹씠 蹂?숇맂 寃쎌슦 (?곸듅 or ?섎씫)
                if status in ["PRICE_DOWN", "PRICE_UP"]:
                    result["alert_triggered"] = 1
                    alerts_triggered_count += 1
                    changed_items.append(result)
                else:
                    result["alert_triggered"] = 0
                
                if result.get("fallback_used"):
                    fallback_used_count += 1
                
                logger.info("?섏쭛 ?꾨즺 | %s | %s", target.name, result.get("price_change_status"))
                collected_payloads.append(result)
            else:
                fail += 1
                logger.warning("?섏쭛 誘몄씪移?| %s | %s", target.name, result.get("status"))
                collected_payloads.append(result)

        except Exception as exc:
            fail += 1
            logger.exception("?섏쭛 ?ㅽ뙣 | %s", target.name)
            collected_payloads.append({
                "target_name": target.name,
                "config_mode": target.mode,
                "source_mode": target.mode,
                "fallback_used": 0,
                "collected_at": utc_now_iso(),
                "success": 0,
                "status": type(exc).__name__,
                "title": None,
                "price": None,
                "seller_name": None,
                "product_url": target.url,
                "error_message": str(exc),
                "price_change_status": None,
                "prev_price": None,
                "alert_triggered": 0
            })

    # 猷⑦봽 醫낅즺 ????踰덉뿉 ???(Batch Insert)
    if collected_payloads:
        try:
            store.insert_batch(collected_payloads)
        except Exception as e:
            logger.error(f"GSheet 諛곗튂 ???理쒖쥌 ?ㅽ뙣: {e}")

    # ---------- [???紐??몃옒而??섏쭛 猷⑦떞 - 理쒖쟻??踰꾩쟾] ----------
    if app_config.mall_targets:
        logger.info("???Mall) ?섏쭛 ?쒖옉 (%d媛??寃?", len(app_config.mall_targets))
        mall_collected_at = utc_now_iso()
        
        # 1. 荑쇰━蹂꾨줈 ?寃?洹몃９??        query_groups: dict[str, list] = {}
        for m_target in app_config.mall_targets:
            q = m_target.query
            if q not in query_groups:
                query_groups[q] = []
            query_groups[q].append(m_target)
        
        # 2. 荑쇰━ 洹몃９蹂꾨줈 API ?몄텧 諛??ㅼ쨷 ?꾪꽣留?        for query, targets in query_groups.items():
            try:
                # ?대떦 洹몃９??理쒕? ?섏씠吏 ???뺤씤
                max_pages = max(t.request.pages for t in targets)
                logger.info("荑쇰━ 洹몃９ ?섏쭛 以? '%s' (?寃???? %d媛? 理쒕? %d?섏씠吏)", 
                            query, len(targets), max_pages)
                
                # API ?몄텧 (1嫄댁쓽 荑쇰━濡?紐⑤뱺 ?寃??곗씠??寃??
                all_items = collect_mall_items(client, app_config, query, max_pages)
                
                # 媛??寃잙퀎濡??꾪꽣留?諛????                for m_target in targets:
                    target_mall = clean_text(m_target.mall_name)
                    candidates = [item for item in all_items if target_mall in clean_text(item.get("seller_name", ""))]
                    
                    if candidates:
                        for c in candidates:
                            c["collected_at"] = mall_collected_at
                        store.insert_mall_records(m_target.name, m_target.query, m_target.mall_name, m_target.category, candidates)
                        logger.info("  ??[%s] ?꾪꽣留??꾨즺: %d媛??곹뭹 ???, m_target.name, len(candidates))
                    else:
                        logger.warning("  ??[%s] ?꾪꽣留?寃곌낵 ?놁쓬", m_target.name)
                        
            except Exception as e:
                logger.error("荑쇰━ 洹몃９ ?섏쭛 ?ㅽ뙣 (%s): %s", query, e)

    # ---------- [??궧 ?섏쭛 理쒖쟻??猷⑦떞] ----------
    unique_rank_queries = {t.rank_query for t in app_config.targets if t.rank_query}
    expanded_queries = set(unique_rank_queries)

    logger.info("怨좎쑀 ??궧 ?ㅼ썙???섏쭛 ?쒖옉 (%d媛?", len(expanded_queries))
    
    rank_collected_at = utc_now_iso()
    
    for r_query in expanded_queries:
        try:
            logger.info(f"??궧 ?섏쭛 以?(API): {r_query}")
            # Naver API 寃??(sim=?ㅼ씠踰???궧??
            rank_payload = client.search(query=r_query, display=15, sort="sim")
            rank_items = rank_payload.get("items", [])
            
            rows_to_insert = []
            for rank, item in enumerate(rank_items, start=1):
                norm = _normalized_item(item)
                rows_to_insert.append({
                    "query": r_query,
                    "rank": rank,
                    "collected_at": rank_collected_at,
                    "title": norm.get("title"),
                    "price": norm.get("price"),
                    "seller_name": norm.get("seller_name"),
                    "product_id": norm.get("product_id"),
                    "product_type": norm.get("product_type"),
                    "product_url": norm.get("product_url"),
                    "image_url": norm.get("image_url"),
                    "is_ad": 0
                })
            
            if rows_to_insert:
                store.insert_ranking_batch(rows_to_insert)
                logger.info(f"??궧 ?섏쭛 ?꾨즺: {r_query} ({len(rows_to_insert)}媛?")
            else:
                logger.warning(f"??궧 ?섏쭛 寃곌낵 ?놁쓬: {r_query}")
        except Exception as e:
            logger.error(f"??궧 ?섏쭛 ?ㅽ뙣 ({r_query}): {e}")
    
    store.close()

    # ?대찓???뚮┝ (KST 湲곗? ?쇨컙 ?쒓컙? 21:00~08:00 ?쒖쇅)
    if changed_items:
        if not is_night_time_kst():
            send_price_alert(
                changed_items,
                app_config.email.email_from,
                app_config.email.email_password,
                app_config.email.email_to
            )
        else:
            logger.info("?쇨컙 ?쒓컙(21:00-08:00 KST)?대?濡??대찓???뚮┝??嫄대꼫?곷땲??")

    logger.info("理쒖쥌 寃곌낵 | OK: %d, FAIL: %d, Fallback: %d, Alert: %d", ok, fail, fallback_used_count, alerts_triggered_count)

    if summary_json:
        summary_data = {
            "ok": ok,
            "fail": fail,
            "fallback_used": fallback_used_count,
            "alerts": alerts_triggered_count,
            "collected_at": utc_now_iso()
        }
        Path(summary_json).write_text(dump_json(summary_data), encoding="utf-8")
        logger.info(f"?섏쭛 ?붿빟 ????꾨즺: {summary_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Naver Shopping Price Tracker")
    parser.add_argument("command", choices=["once", "monitor", "export-ui", "serve", "sync-from-gcs", "sync-to-gcs", "daily-report", "export-report", "export-mall-report"], help="?ㅽ뻾??而ㅻ㎤??)
    parser.add_argument("--config", default="targets.yaml", help="?ㅼ젙 ?뚯씪 寃쎈줈")
    parser.add_argument("--db", default="price_tracker.sqlite3", help="DB ?뚯씪 寃쎈줈")
    parser.add_argument("--interval", type=int, default=3600, help="紐⑤땲?곕쭅 二쇨린 (珥?")
    parser.add_argument("--summary-json", help="?섏쭛 寃곌낵 ?붿빟????ν븷 JSON 寃쎈줈")
    parser.add_argument("--output", help="?뚯씪 ???寃쎈줈 (export-report ?깆뿉???ъ슜)")
    parser.add_argument("--verbose", action="store_true", help="?곸꽭 濡쒓렇 異쒕젰")
    args = parser.parse_args()

    setup_logging(args.verbose)
    load_dotenv()

    try:
        app_config = load_config(args.config)
    except Exception as e:
        logger.error("?ㅼ젙 濡쒕뱶 ?ㅽ뙣: %s", e)
        return

    if args.command == "once":
        if not app_config.gsheet_id:
            logger.error("GSHEET_ID媛 ?ㅼ젙?섏? ?딆븯?듬땲??(YAML ?먮뒗 ?섍꼍蹂??.")
            return
        asyncio.run(run_once(app_config, "artifacts", app_config.gsheet_id, summary_json=args.summary_json))

    elif args.command == "monitor":
        if not app_config.gsheet_id:
            logger.error("GSHEET_ID媛 ?ㅼ젙?섏? ?딆븯?듬땲??")
            return
        logger.info("%d珥?媛꾧꺽?쇰줈 紐⑤땲?곕쭅???쒖옉?⑸땲??..", args.interval)
        while True:
            try:
                asyncio.run(run_once(app_config, "artifacts", app_config.gsheet_id, summary_json=args.summary_json))
            except Exception as e:
                logger.exception("紐⑤땲?곕쭅 猷⑦봽 以??ㅻ쪟 諛쒖깮")
            time.sleep(args.interval)

    elif args.command == "export-ui":
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        if not app_config.gsheet_id or not service_account_json:
            logger.error("GSHEET_ID ?먮뒗 GOOGLE_SERVICE_ACCOUNT_KEY ?섍꼍蹂?섍? ?ㅼ젙?섏? ?딆븯?듬땲??")
            return
            
        store = GoogleSheetStore(app_config.gsheet_id, service_account_json)
        try:
            dashboard_raw = store.get_dashboard_data(app_config.targets)
            
            # 怨좎쑀 ??궧 ?ㅼ썙?쒕퀎 理쒖떊 ?곗씠???섏쭛
            rankings = {}
            unique_rank_queries = {t.rank_query for t in app_config.targets if t.rank_query}
            
            for rq in unique_rank_queries:
                latest = store.get_latest_rankings(rq)
                if latest:
                    rankings[rq] = latest
            
            # ??щ퀎 ?쇳븨紐?由ы룷???곗씠???섏쭛
            mall_raw = store.get_mall_report_data()
            mall_reports = {"categories": mall_raw}
            
            data = {
                "products": dashboard_raw["products"],
                "rankings": rankings,
                "mall_reports": mall_reports,
                "gsheet_id": app_config.gsheet_id,
                "updated_at": dashboard_raw["generated_at"]
            }
            Path("dashboard_data.json").write_text(dump_json(data), encoding="utf-8")
            logger.info("UI ?곗씠???대낫?닿린 ?꾨즺: dashboard_data.json (Google Sheets 湲곕컲)")
        finally:
            store.close()

    elif args.command == "sync-from-gcs" or args.command == "sync-to-gcs":
        logger.warning("GCS ?곕룞 湲곕뒫? ??釉뚮옖移섏뿉?????댁긽 ?ъ슜?섏? ?딆뒿?덈떎 (Google Sheets Only).")

    elif args.command == "serve":
        # 媛꾨떒??HTTP ?쒕쾭 ?ㅽ뻾 (??쒕낫???뺤씤??
        import http.server
        import socketserver
        PORT = 8000
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            logger.info("http://localhost:%d ?먯꽌 ??쒕낫???쒕퉬?ㅻ? ?쒖옉?⑸땲??", PORT)
            httpd.serve_forever()

    elif args.command == "daily-report":
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        if not app_config.gsheet_id or not service_account_json:
            logger.error("GSHEET_ID ?먮뒗 GOOGLE_SERVICE_ACCOUNT_KEY ?섍꼍蹂?섍? ?ㅼ젙?섏? ?딆븯?듬땲??")
            return
            
        store = GoogleSheetStore(app_config.gsheet_id, service_account_json)
        try:
            send_daily_report(
                store,
                app_config.email.email_from,
                app_config.email.email_password,
                app_config.email.email_to,
                app_config.targets
            )
        finally:
            store.close()

    elif args.command == "export-report":
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        if not app_config.gsheet_id or not service_account_json:
            logger.error("?꾩슂???ㅼ젙???꾨씫?섏뿀?듬땲??")
            return
            
        from .report import generate_daily_report_html
        store = GoogleSheetStore(app_config.gsheet_id, service_account_json)
        try:
            html = generate_daily_report_html(store, app_config.targets)
            output_path = args.output or "report.html"
            Path(output_path).write_text(html, encoding="utf-8")
            logger.info(f"?곗씪由?由ы룷???앹꽦 ?꾨즺: {output_path}")
        finally:
            store.close()

    elif args.command == "export-mall-report":
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        if not app_config.gsheet_id or not service_account_json:
            logger.error("?꾩슂???ㅼ젙???꾨씫?섏뿀?듬땲??")
            return
            
        from .report import generate_mall_report_html
        store = GoogleSheetStore(app_config.gsheet_id, service_account_json)
        try:
            html = generate_mall_report_html(store)
            output_path = args.output or "mall_report.html"
            Path(output_path).write_text(html, encoding="utf-8")
            logger.info(f"?쇳븨紐?異붿쟻 由ы룷???앹꽦 ?꾨즺: {output_path}")
        finally:
            store.close()


if __name__ == "__main__":
    main()
