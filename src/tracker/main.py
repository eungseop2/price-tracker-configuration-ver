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
from .util import (
    calc_change_metrics, clean_text, dump_json, utc_now_iso, 
    is_night_time_kst, normalize_for_match
)

def _normalize_seller_name(name: str | None) -> str:
    """판매처 이름을 비교하기 좋게 소문자화 및 공백 제거합니다."""
    if not name: return ""
    return name.lower().replace(" ", "")

def _is_authorized_seller(seller_name: str | None, authorized_sellers: list[str]) -> bool:
    """해당 판매처가 공식(Authorized) 업체인지 확인합니다."""
    if not seller_name or not authorized_sellers:
        return False
    sn = _normalize_seller_name(seller_name)
    for auth in authorized_sellers:
        if _normalize_seller_name(auth) == sn:
            return True
    return False

def _extract_image_id(url: str | None) -> str | None:
    """이미지 URL에서 핵심 식별자(파일명의 상품 번호 등)를 추출합니다."""
    if not url: return None
    # 예: https://shopping-phinf.pstatic.net/main_5350770/53507707536.jpg?type=f160
    path = url.split("?")[0]
    filename = path.split("/")[-1]
    return filename.split(".")[0]

def _map_product_code(image_url: str | None, image_map: dict[str, str]) -> str | None:
    """이미지 URL을 기반으로 사전에 등록된 제품 코드를 반환합니다."""
    if not image_url or not image_map:
        return None
    
    # 1. 완전 일치 확인
    if image_url in image_map:
        return image_map[image_url]
    
    img_id = _extract_image_id(image_url)
    if not img_id: return None

    # 2. 부분 일치 확인 (이미지 ID 포함 여부)
    for map_url, code in image_map.items():
        if img_id in map_url or map_url in image_url:
            return code
            
    return None

logger = logging.getLogger("naver_price_tracker")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


async def _collect_one(client: NaverShoppingSearchClient, target: TargetConfig, app_config, artifacts_dir: str) -> tuple[dict, list[dict]]:
    """단일 타겟 수집 및 NO_MATCH 시 자동 폴백 로직"""
    result = None
    items = []
    
    if target.mode == "api_query":
        try:
            result, items = collect_lowest_offer_via_api(client, app_config, target)
        except Exception as e:
            raise e

        if result.get("status") == "NO_MATCH" and target.fallback_url:
            logger.info("API NO_MATCH -> Browser 폴백 실행 | %s", target.name)
            fallback_target = TargetConfig(
                name=target.name,
                mode="browser_url",
                url=target.fallback_url,
                browser=target.browser,
                match=target.match,
            )
            fallback_result, fallback_items = await collect_lowest_offer_via_browser(fallback_target, artifacts_dir)
            fallback_result["fallback_used"] = 1
            fallback_result["status"] = "OK"
            return fallback_result, fallback_items
            
        return result, items

    elif target.mode == "browser_url":
        result, items = await collect_lowest_offer_via_browser(target, artifacts_dir)
        return result, items

    else:
        raise ValueError(f"지원하지 않는 수집 모드: {target.mode}")


async def run_once(app_config, artifacts_dir: str, gsheet_id: str, summary_json: str | None = None) -> None:
    ok = 0
    fail = 0
    fallback_used_count = 0
    alerts_triggered_count = 0
    changed_items = []
    collected_payloads = []
    
    # 최저가 수집 데이터를 재활용하기 위한 전체 상품 저장소
    all_peeked_items = []
    
    service_account_json = os.getenv("GCP_SA_KEY") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
    if not service_account_json:
        logger.error("구글 서비스 계정 키 환경변수(GCP_SA_KEY 또는 GOOGLE_SERVICE_ACCOUNT_KEY)가 설정되지 않았습니다.")
        return

    store = GoogleSheetStore(gsheet_id, service_account_json)
    client = NaverShoppingSearchClient(timeout_seconds=app_config.timeout_seconds)

    for target in app_config.targets:
        logger.info("수집 시작 | %s | mode=%s", target.name, target.mode)
        try:
            prev_success = store.get_latest_success(target.name)
            prev_price = prev_success["price"] if prev_success else None

            result, items = await _collect_one(client, target, app_config, artifacts_dir)
            
            # 수집된 모든 상품을 통합 분석 풀에 저장 (몰 리포트용)
            if items:
                for itm in items:
                    # itm은 이제 naver_api.py에서 반환된 정규화된 전체 데이터 리스트임
                    itm["category"] = target.category
                    # 낱개 상품들에 대해서도 이미지 매핑 수행
                    itm["product_code"] = _map_product_code(itm.get("image_url"), app_config.image_map)
                    all_peeked_items.append(itm)
                
            result["collected_at"] = utc_now_iso()
            result["config_mode"] = target.mode
            # 최종 선정된 최저가 상품에 대해서도 이미지 매핑 수행
            result["product_code"] = _map_product_code(result.get("image_url"), app_config.image_map)

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

            result.setdefault("fallback_used", 0)
            result["alert_triggered"] = 0
            
            if result.get("success"):
                ok += 1
                status = result.get("price_change_status")
                if status in ["PRICE_DOWN", "PRICE_UP"]:
                    result["alert_triggered"] = 1
                    alerts_triggered_count += 1
                    changed_items.append(result)
                
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

    # ---------- [도용 감시 로직 추가] ----------
    # 1. 이번 회차 수집된 모든 상품 중 공식 판매처가 사용한 이미지 ID들 추출
    official_image_ids = set()
    for itm in all_peeked_items:
        if _is_authorized_seller(itm.get("seller_name"), app_config.authorized_sellers):
            img_id = _extract_image_id(itm.get("image_url"))
            if img_id:
                official_image_ids.add(img_id)
    
    # 2. 모든 수집 상품에 대해 도용 여부 판단
    for itm in all_peeked_items:
        img_id = _extract_image_id(itm.get("image_url"))
        if img_id in official_image_ids:
            if not _is_authorized_seller(itm.get("seller_name"), app_config.authorized_sellers):
                itm["is_unauthorized"] = 1
                itm["product_code"] = itm.get("product_code") or "IMAGE_MISUSE_DETECTED"
            else:
                itm["is_unauthorized"] = 0
        else:
            itm["is_unauthorized"] = 0

    # 3. 최저가 수집 결과(collected_payloads)들도 동일하게 도용 여부 플래그 업데이트
    for payload in collected_payloads:
        if payload.get("success"):
            img_id = _extract_image_id(payload.get("image_url"))
            if img_id in official_image_ids:
                if not _is_authorized_seller(payload.get("seller_name"), app_config.authorized_sellers):
                    payload["is_unauthorized"] = 1
                    payload["product_code"] = payload.get("product_code") or "IMAGE_MISUSE_DETECTED"
                else:
                    payload["is_unauthorized"] = 0
            else:
                payload["is_unauthorized"] = 0

    # 4. [사용자 요청] 카탈로그 판매처('네이버')를 실판매처로 매칭 (수집 시점 확정)
    for payload in collected_payloads:
        if payload.get("success") and payload.get("seller_name") in ["네이버", "Naver", None]:
            price = payload.get("price")
            if not price: continue
            
            found_mall = None
            # 같은 회차에 수집된 모든 상품 중 가격이 일치하는 가장 적절한 판매처 검색
            for itm in all_peeked_items:
                try:
                    m_price = int(itm.get("price") or 0)
                    if m_price == int(price) and m_price > 0:
                        m_seller = itm.get("seller_name")
                        if m_seller and m_seller not in ["네이버", "Naver"]:
                            found_mall = m_seller
                            break
                except (ValueError, TypeError):
                    continue
            
            if found_mall:
                logger.info(f"  [MARKET MATCH] {payload['target_name']} -> {found_mall} (Price: {price})")
                payload["seller_name"] = found_mall

    # 루프 종료 후 한 번에 저장 (Batch Insert)
    if collected_payloads:
        try:
            store.insert_batch(collected_payloads)
        except Exception as e:
            logger.error(f"GSheet 배치 저장 최종 실패: {e}")

    # ---------- [셀러 트래킹: 최저가 데이터 재활용] ----------
    if app_config.mall_targets:
        logger.info("최저가 수집 데이터를 활용한 셀러 필터링 시작 (%d개 몰 타겟, %d개 수집 상품 분석)", 
                    len(app_config.mall_targets), len(all_peeked_items))
        
        combined_collected_at = utc_now_iso()
        
        for m_target in app_config.mall_targets:
            target_mall_search_term = normalize_for_match(m_target.mall_name)
            candidates = []
            seen_urls = set()
            
            for itm in all_peeked_items:
                # 카테고리가 일치하거나 쿼리 키워드가 포함된 경우 필터링
                if itm.get("category") == m_target.category or m_target.query in itm.get("title", ""):
                    if target_mall_search_term in normalize_for_match(itm.get("seller_name", "")):
                        url = itm.get("product_url")
                        if url not in seen_urls:
                            itm["collected_at"] = combined_collected_at
                            candidates.append(itm)
                            seen_urls.add(url)
            
            if candidates:
                store.insert_mall_records(m_target.name, m_target.query, m_target.mall_name, m_target.category, candidates)
                logger.info(f"  └─ [{m_target.name}] 필터링 완료: {len(candidates)}개 상품 저장 (재활용)")
            else:
                logger.warning(f"  └─ [{m_target.name}] 해당 셀러 상품을 찾을 수 없음 (카탈로그 결과 내)")

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
            
            # [카탈로그 매칭 안내] 카탈로그 판매처는 이제 수집 시점(run_once)에 확정되어 저장됩니다.

            data = {



                "products": dashboard_raw["products"],
                "rankings": rankings,
                "mall_reports": mall_reports,
                "gsheet_id": app_config.gsheet_id,
                "updated_at": dashboard_raw["generated_at"]
            }
            Path("dashboard_data.json").write_text(dump_json(data), encoding="utf-8")
            logger.info("UI 데이터 내보내기 완료: dashboard_data.json (Google Sheets 기반 + 매칭 로직 적용)")
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
