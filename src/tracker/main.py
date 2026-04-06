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
from .db import ObservationStore, RankingStore
from .gcs_sync import download_db, upload_db
from .naver_api import (
    NaverShoppingSearchClient,
    collect_lowest_offer_via_api,
    _normalized_item,
)
from .notifier import send_price_alert
from .report import send_daily_report
from .util import calc_change_metrics, dump_json, utc_now_iso, is_night_time_kst

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


async def run_once(app_config, artifacts_dir: str, db_path: str, summary_json: str | None = None) -> None:
    ok = 0
    fail = 0
    fallback_used_count = 0
    alerts_triggered_count = 0
    changed_items = []
    
    store = ObservationStore(db_path)
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
                store.insert(result)
            else:
                fail += 1
                logger.warning("?섏쭛 誘몄씪移?| %s | %s", target.name, result.get("status"))
                store.insert(result)

        except Exception as exc:
            fail += 1
            logger.exception("?섏쭛 ?ㅽ뙣 | %s", target.name)
            store.insert({
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

    # ---------- [??궧 ?섏쭛 理쒖쟻??猷⑦떞] ----------
    unique_rank_queries = {t.rank_query for t in app_config.targets if t.rank_query}
    # "媛ㅻ윮??媛 ?ы븿??寃쎌슦 ?쒖쇅??踰꾩쟾???섏쭛 紐⑸줉??異붽?
    expanded_queries = set()
    for q in unique_rank_queries:
        expanded_queries.add(q)
        if "媛ㅻ윮?? in q:
            short_q = q.replace("媛ㅻ윮??, "").strip()
            if short_q:
                expanded_queries.add(short_q)
    
    logger.info("怨좎쑀 ??궧 ?ㅼ썙???섏쭛 ?쒖옉 (%d媛?-> ?뺤옣 %d媛?", len(unique_rank_queries), len(expanded_queries))
    
    r_store = RankingStore(db_path)
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
                r_store.insert_ranking_batch(rows_to_insert)
                logger.info(f"??궧 ?섏쭛 ?꾨즺: {r_query} ({len(rows_to_insert)}媛?")
            else:
                logger.warning(f"??궧 ?섏쭛 寃곌낵 ?놁쓬: {r_query}")
        except Exception as e:
            logger.error(f"??궧 ?섏쭛 ?ㅽ뙣 ({r_query}): {e}")
    
    r_store.close()
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
    parser.add_argument("command", choices=["once", "monitor", "export-ui", "serve", "sync-from-gcs", "sync-to-gcs", "daily-report", "export-report"], help="?ㅽ뻾??而ㅻ㎤??)
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
        asyncio.run(run_once(app_config, "artifacts", args.db, summary_json=args.summary_json))

    elif args.command == "monitor":
        logger.info("%d珥?媛꾧꺽?쇰줈 紐⑤땲?곕쭅???쒖옉?⑸땲??..", args.interval)
        while True:
            try:
                asyncio.run(run_once(app_config, "artifacts", args.db, summary_json=args.summary_json))
            except Exception as e:
                logger.exception("紐⑤땲?곕쭅 猷⑦봽 以??ㅻ쪟 諛쒖깮")
            time.sleep(args.interval)

    elif args.command == "export-ui":
        store = ObservationStore(args.db)
        r_store = RankingStore(args.db)
        try:
            dashboard_raw = store.get_dashboard_data(app_config.targets)
            
            # 怨좎쑀 ??궧 ?ㅼ썙?쒕퀎 理쒖떊 ?곗씠???섏쭛 (?뺤옣 踰꾩쟾 ?ы븿)
            rankings = {}
            unique_rank_queries = {t.rank_query for t in app_config.targets if t.rank_query}
            
            expanded_queries = set()
            for q in unique_rank_queries:
                expanded_queries.add(q)
                if "媛ㅻ윮?? in q:
                    short_q = q.replace("媛ㅻ윮??, "").strip()
                    if short_q:
                        expanded_queries.add(short_q)

            for rq in expanded_queries:
                latest = r_store.get_latest_rankings(rq)
                if latest:
                    rankings[rq] = latest
            
            data = {
                "products": dashboard_raw["products"],
                "rankings": rankings,
                "updated_at": dashboard_raw["generated_at"]
            }
            Path("dashboard_data.json").write_text(dump_json(data), encoding="utf-8")
            logger.info("UI ?곗씠???대낫?닿린 ?꾨즺: dashboard_data.json")
        finally:
            store.close()
            r_store.close()

    elif args.command == "sync-from-gcs":
        bucket = os.getenv("GCS_BUCKET")
        if not bucket:
            logger.error("GCS_BUCKET ?섍꼍蹂?섍? ?ㅼ젙?섏? ?딆븯?듬땲??")
            return
        download_db(bucket, args.db)

    elif args.command == "sync-to-gcs":
        bucket = os.getenv("GCS_BUCKET")
        if not bucket:
            logger.error("GCS_BUCKET ?섍꼍蹂?섍? ?ㅼ젙?섏? ?딆븯?듬땲??")
            return
        upload_db(bucket, args.db)

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
        send_daily_report(args.db, app_config.email.email_from, app_config.email.email_password, app_config.email.email_to, app_config.targets)

    elif args.command == "export-report":
        from .report import generate_daily_report_html
        html = generate_daily_report_html(args.db, app_config.targets)
        out_path = args.output or "daily_report.html"
        Path(out_path).write_text(html, encoding="utf-8")
        logger.info(f"蹂닿퀬??????꾨즺: {out_path}")


if __name__ == "__main__":
    main()

