from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from .alert import check_and_alert
from .browser_scraper import (
    BrowserScrapeError,
    collect_lowest_offer_via_browser,
    collect_current_offer_via_browser
)
from .config import StoreType, TargetConfig, load_config
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
    """단일 타겟 수집 및 NO_MATCH 시 자동 폴백 로직"""
    result = None
    
    if target.mode == "api_query":
        try:
            result = collect_lowest_offer_via_api(client, app_config, target)
        except Exception as e:
            # 401, 429, 네트워크 오류 등은 폴백하지 않고 예외 발생 (main 루프에서 처리)
            raise e

        # API 결과가 NO_MATCH이고 fallback_url이 있는 경우에만 브라우저 폴백
        if result.get("status") == "NO_MATCH" and target.fallback_url:
            logger.info("API NO_MATCH -> Browser 폴백 실행 | %s", target.name)
            fallback_target = TargetConfig(
                name=target.name,
                mode="browser_url",
                url=target.fallback_url,
                browser=target.browser,
                match=target.match,
            )
            fallback_result = await collect_lowest_offer_via_browser(fallback_target, artifacts_dir)
            # 폴백 정보 기록 루틴 (status 오염 금지)
            fallback_result["fallback_used"] = 1
            fallback_result["status"] = "OK"  # 폴백 성공 시에도 순수 OK 유지
            return fallback_result
            
        return result

    elif target.mode == "browser_url":
        result = await collect_lowest_offer_via_browser(target, artifacts_dir)
        return result

    else:
        raise ValueError(f"지원하지 않는 수집 모드: {target.mode}")


async def run_once(app_config, artifacts_dir: str, gsheet_id: str, summary_json: str | None = None) -> None:
    ok = 0
    fail = 0
    fallback_used_count = 0
    alerts_triggered_count = 0
    changed_items = []
    # 데이터 배치 수집용 리스트
    collected_payloads = []
    
    service_account_json = os.getenv("GCP_SA_KEY") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
    if not service_account_json:
        logger.error("구글 서비스 계정 키 환경변수(GCP_SA_KEY 또는 GOOGLE_SERVICE_ACCOUNT_KEY)가 설정되지 않았습니다.")
        return

    store = GoogleSheetStore(gsheet_id, service_account_json)
    client = NaverShoppingSearchClient(timeout_seconds=app_config.timeout_seconds)

    for target in app_config.targets:
        logger.info("수집 시작 | %s | mode=%s", target.name, target.mode)
        try:
            # 직전 성공 기록 조회 (가격 변동 체크용)
            prev_success = store.get_latest_success(target.name)
            prev_price = prev_success["price"] if prev_success else None

            result = await _collect_one(client, target, app_config, artifacts_dir)
            result["collected_at"] = utc_now_iso()
            result["config_mode"] = target.mode

            # 가격 변동 및 상태 계산
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

            # 필수 필드 보장
            result.setdefault("fallback_used", 0)
            result["alert_triggered"] = 0
            
            # 알림 체크
            # 알림 체크 (가격 변동 기반)
            if result.get("success"):
                ok += 1
                status = result.get("price_change_status")

                # 가격이 변동된 경우 (상승 or 하락)
                if status in ["PRICE_DOWN", "PRICE_UP"]:
                    result["alert_triggered"] = 1
                    alerts_triggered_count += 1
                    changed_items.append(result)
                else:
                    result["alert_triggered"] = 0
                
                if result.get("fallback_used"):
                    fallback_used_count += 1
                
                logger.info("수집 완료 | %s | %s", target.name, result.get("price_change_status"))
                collected_payloads.append(result)
            else:
                fail += 1
                logger.warning("수집 미일치 | %s | %s", target.name, result.get("status"))
                collected_payloads.append(result)

        except Exception as exc:
            fail += 1
            logger.exception("수집 실패 | %s", target.name)
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

    # 루프 종료 후 한 번에 저장 (Batch Insert)
    if collected_payloads:
        try:
            store.insert_batch(collected_payloads)
        except Exception as e:
            logger.error(f"GSheet 배치 저장 최종 실패: {e}")

    # ---------- [셀러 트래킹 + 랭킹 통합 수집 루틴] ----------
    # 2번(랭킹)과 3번(셀러 트래킹)이 같은 쿼리를 쓸 경우 API 호출을 공유하여 리소스 절약
    
    # 1. 필요한 쿼리 전체 목록 수집
    unique_rank_queries = {t.rank_query for t in app_config.targets if t.rank_query}
    mall_query_groups: dict[str, list] = {}
    if app_config.mall_targets:
        for m_target in app_config.mall_targets:
            q = m_target.query
            if q not in mall_query_groups:
                mall_query_groups[q] = []
            mall_query_groups[q].append(m_target)
    
    # 2. 전체 고유 쿼리 합산 (셀러+랭킹 통합)
    all_queries = set(unique_rank_queries) | set(mall_query_groups.keys())
    # API 결과 캐시: {쿼리: [normalized_item, ...]}
    api_result_cache: dict[str, list] = {}
    
    combined_collected_at = utc_now_iso()
    
    logger.info("셀러+랭킹 통합 수집 시작 (%d개 고유 쿼리)", len(all_queries))
    
    for query in all_queries:
        try:
            # 필요한 최대 페이지 수 결정 (셀러 트래킹이 더 넓은 범위)
            mall_pages = max((t.request.pages for t in mall_query_groups.get(query, [])), default=0)
            ranking_limit = getattr(app_config, "ranking_limit", 50)
            # 랭킹용 필요 페이지 수 (display=50 기준)
            rank_pages = (ranking_limit + app_config.display - 1) // app_config.display if query in unique_rank_queries else 0
            
            max_pages = max(mall_pages, rank_pages, 1)
            logger.info(f"통합 수집: '{query}' (셀러={mall_pages}p, 랭킹={rank_pages}p → 최대 {max_pages}p)")
            
            # API 호출 1회 (가장 넓은 범위로)
            all_items = collect_mall_items(client, app_config, query, max_pages)
            api_result_cache[query] = all_items
            
        except Exception as e:
            logger.error(f"통합 수집 실패 ({query}): {e}")
            api_result_cache[query] = []
    
    # 3. 셀러 트래킹 데이터 처리 (캐시된 결과 활용)
    if app_config.mall_targets:
        logger.info("대상 쇼핑몰(Mall) 필터링 시작 (%d개 타겟)", len(app_config.mall_targets))
        for query, targets in mall_query_groups.items():
            all_items = api_result_cache.get(query, [])
            for m_target in targets:
                target_mall = clean_text(m_target.mall_name)
                candidates = [item for item in all_items if target_mall in clean_text(item.get("seller_name", ""))]
                
                if candidates:
                    for c in candidates:
                        c["collected_at"] = combined_collected_at
                    store.insert_mall_records(m_target.name, m_target.query, m_target.mall_name, m_target.category, candidates)
                    logger.info(f"  └─ [{m_target.name}] 필터링 완료: {len(candidates)}개 상품 저장")
                else:
                    logger.warning(f"  └─ [{m_target.name}] 해당 쇼핑몰 상품을 찾을 수 없음")

    # 4. 랭킹 데이터 처리 (캐시된 결과 활용)
    logger.info("랭킹 데이터 추출 시작 (%d개 키워드)", len(unique_rank_queries))
    
    for r_query in unique_rank_queries:
        try:
            cached_items = api_result_cache.get(r_query, [])
            limit = getattr(app_config, "ranking_limit", 50)
            rank_items = cached_items[:limit]  # 이미 sim 정렬된 결과에서 상위 N개 추출
            
            rows_to_insert = []
            for rank, norm in enumerate(rank_items, start=1):
                rows_to_insert.append({
                    "query": r_query,
                    "rank": rank,
                    "collected_at": combined_collected_at,
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
                logger.info(f"랭킹 추출 완료: {r_query} ({len(rows_to_insert)}개, 캐시 활용)")
            else:
                logger.warning(f"랭킹 추출 결과 없음: {r_query}")
        except Exception as e:
            logger.error(f"랭킹 추출 실패 ({r_query}): {e}")
    
    store.close()

    # 이메일 알림 (KST 기준 야간 시간대 21:00~08:00 제외)
    if changed_items:
        if not is_night_time_kst():
            send_price_alert(
                changed_items,
                app_config.email.email_from,
                app_config.email.email_password,
                app_config.email.email_to
            )
        else:
            logger.info("야간 시간(21:00-08:00 KST)이므로 이메일 알림을 건너뜁니다.")

    logger.info("최종 결과 | OK: %d, FAIL: %d, Fallback: %d, Alert: %d", ok, fail, fallback_used_count, alerts_triggered_count)

    if summary_json:
        summary_data = {
            "ok": ok,
            "fail": fail,
            "fallback_used": fallback_used_count,
            "alerts": alerts_triggered_count,
            "collected_at": utc_now_iso()
        }
        Path(summary_json).write_text(dump_json(summary_data), encoding="utf-8")
        logger.info(f"수집 요약 저장 완료: {summary_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Naver Shopping Price Tracker")
    parser.add_argument("command", choices=["once", "monitor", "export-ui", "serve", "sync-from-gcs", "sync-to-gcs", "daily-report", "export-report", "export-mall-report"], help="실행할 커맨드")
    parser.add_argument("--config", default="targets.yaml", help="설정 파일 경로")
    parser.add_argument("--db", default="price_tracker.sqlite3", help="DB 파일 경로")
    parser.add_argument("--interval", type=int, default=3600, help="모니터링 주기 (초)")
    parser.add_argument("--summary-json", help="수집 결과 요약을 저장할 JSON 경로")
    parser.add_argument("--output", help="파일 저장 경로 (export-report 등에서 사용)")
    parser.add_argument("--verbose", action="store_true", help="상세 로그 출력")
    args = parser.parse_args()

    setup_logging(args.verbose)
    load_dotenv()

    try:
        app_config = load_config(args.config)
    except Exception as e:
        logger.error("설정 로드 실패: %s", e)
        return

    if args.command == "once":
        if not app_config.gsheet_id:
            logger.error("GSHEET_ID가 설정되지 않았습니다 (YAML 또는 환경변수).")
            return
        asyncio.run(run_once(app_config, "artifacts", app_config.gsheet_id, summary_json=args.summary_json))

    elif args.command == "monitor":
        if not app_config.gsheet_id:
            logger.error("GSHEET_ID가 설정되지 않았습니다.")
            return
        logger.info("%d초 간격으로 모니터링을 시작합니다...", args.interval)
        while True:
            try:
                asyncio.run(run_once(app_config, "artifacts", app_config.gsheet_id, summary_json=args.summary_json))
            except Exception as e:
                logger.exception("모니터링 루프 중 오류 발생")
            time.sleep(args.interval)

    elif args.command == "export-ui":
        service_account_json = os.getenv("GCP_SA_KEY") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        if not app_config.gsheet_id or not service_account_json:
            logger.error("GSHEET_ID 또는 구글 서비스 계정 키 환경변수(GCP_SA_KEY/GOOGLE_SERVICE_ACCOUNT_KEY)가 설정되지 않았습니다.")
            return
            
        store = GoogleSheetStore(app_config.gsheet_id, service_account_json)
        try:
            dashboard_raw = store.get_dashboard_data(app_config.targets)
            
            # 고유 랭킹 키워드별 최신 데이터 수집
            rankings = {}
            unique_rank_queries = {t.rank_query for t in app_config.targets if t.rank_query}
            
            for rq in unique_rank_queries:
                latest = store.get_latest_rankings(rq)
                if latest:
                    rankings[rq] = latest
            
            # 셀러별 쇼핑몰 리포트 데이터 수집
            mall_raw = store.get_mall_report_data(monitored_sellers=app_config.monitored_sellers)
            mall_reports = {"categories": mall_raw}
            
            data = {
                "products": dashboard_raw["products"],
                "rankings": rankings,
                "mall_reports": mall_reports,
                "gsheet_id": app_config.gsheet_id,
                "updated_at": dashboard_raw["generated_at"]
            }
            Path("dashboard_data.json").write_text(dump_json(data), encoding="utf-8")
            logger.info("UI 데이터 내보내기 완료: dashboard_data.json (Google Sheets 기반)")
        finally:
            store.close()

    elif args.command == "sync-from-gcs" or args.command == "sync-to-gcs":
        logger.warning("GCS 연동 기능은 이 브랜치에서 더 이상 사용되지 않습니다 (Google Sheets Only).")

    elif args.command == "serve":
        # 간단한 HTTP 서버 실행 (대시보드 확인용)
        import http.server
        import socketserver
        PORT = 8000
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            logger.info("http://localhost:%d 에서 대시보드 서비스를 시작합니다.", PORT)
            httpd.serve_forever()

    elif args.command == "daily-report":
        service_account_json = os.getenv("GCP_SA_KEY") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        if not app_config.gsheet_id or not service_account_json:
            logger.error("GSHEET_ID 또는 구글 서비스 계정 키 환경변수(GCP_SA_KEY/GOOGLE_SERVICE_ACCOUNT_KEY)가 설정되지 않았습니다.")
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
        service_account_json = os.getenv("GCP_SA_KEY") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        if not app_config.gsheet_id or not service_account_json:
            logger.error("필요한 설정(GSHEET_ID 또는 구글 서비스 계정 키)이 누락되었습니다.")
            return
            
        from .report import generate_daily_report_html
        store = GoogleSheetStore(app_config.gsheet_id, service_account_json)
        try:
            html = generate_daily_report_html(store, app_config.targets)
            output_path = args.output or "report.html"
            Path(output_path).write_text(html, encoding="utf-8")
            logger.info(f"데일리 리포트 생성 완료: {output_path}")
        finally:
            store.close()

    elif args.command == "export-mall-report":
        # 2. 저장소 결정 (GSheet vs SQLite)
        store = None
        if app_config.store_type == StoreType.GSHEET:
            credential_json = os.getenv("GCP_SA_KEY") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
            if not credential_json:
                logger.error("GSHEET 모드이나 GCP_SA_KEY (또는 GOOGLE_SERVICE_ACCOUNT_KEY) 환경변수가 설정되지 않았습니다.")
                sys.exit(1)
            store = GoogleSheetStore(app_config.gsheet_id, credential_json)
            logger.info(f"Google Sheets 저장소 사용 준비 완료 (ID: {app_config.gsheet_id})")
        else:
            db_path = os.getenv("DB_PATH", "data/tracker.db")
            store = ObservationStore(db_path)
            logger.info(f"SQLite 저장소 사용 준비 완료 (Path: {db_path})")
            
        from .report import generate_mall_report_html
        try:
            html = generate_mall_report_html(store)
            output_path = args.output or "mall_report.html"
            Path(output_path).write_text(html, encoding="utf-8")
            logger.info(f"쇼핑몰 추적 리포트 생성 완료: {output_path}")
        finally:
            store.close()


if __name__ == "__main__":
    main()
