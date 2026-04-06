import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger("tracker.gsheet_store")

# 시트별 헤더 정의 (SQLite 스키마와 동일하게 유지)
HEADERS = {
    "observations": [
        "target_name", "source_mode", "collected_at", "success", "status", 
        "price", "prev_price", "price_delta", "price_delta_pct", "price_change_status",
        "title", "seller_name", "product_id", "product_url", "image_url", "search_rank",
        "fallback_used", "alert_triggered"
    ],
    "ranking_history": [
        "query", "rank", "collected_at", "title", "price", "seller_name", 
        "product_id", "product_type", "product_url", "image_url", "is_ad"
    ]
}

class GoogleSheetStore:
    def __init__(self, spreadsheet_id: str, service_account_json: str):
        self.spreadsheet_id = spreadsheet_id
        self.service_account_json = service_account_json
        self._gc = None
        self._sh = None
        self._worksheets = {}

    def _connect(self):
        if self._sh:
            return
        
        try:
            info = json.loads(self.service_account_json)
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            credentials = Credentials.from_service_account_info(info, scopes=scopes)
            self._gc = gspread.authorize(credentials)
            self._sh = self._gc.open_by_key(self.spreadsheet_id)
            logger.info(f"구글 스프레드시트 연결 성공: {self._sh.title}")
        except Exception as e:
            logger.error(f"구글 스프레드시트 연결 실패: {e}")
            raise

    def _get_worksheet(self, name: str):
        self._connect()
        if name in self._worksheets:
            return self._worksheets[name]
        
        try:
            ws = self._sh.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            ws = self._sh.add_worksheet(title=name, rows=1000, cols=len(cols))
            ws.append_row(cols)
            logger.info(f"새 시트 생성됨: {name}")
            
        self._worksheets[name] = ws
        return ws

    def insert(self, payload: dict[str, Any]):
        """단일 상품 수집 기록 저장 (내부적으로 insert_batch 활용)"""
        self.insert_batch([payload])

    def insert_batch(self, payloads: list[dict[str, Any]]):
        """여러 상품 수집 기록을 한 번에 저장 (성능 및 신뢰성 최적화)"""
        if not payloads:
            return

        ws = self._get_worksheet("observations")
        cols = HEADERS["observations"]
        
        rows = []
        for p in payloads:
            row = []
            for col in cols:
                val = p.get(col)
                # GSheet 기록 시 None은 빈 문자열로 변환하여 에러 방지
                if val is None:
                    row.append("")
                else:
                    row.append(val)
            rows.append(row)
            
        try:
            ws.append_rows(rows)
            logger.info(f"데이터 배치 저장 완료 (observations): {len(rows)}건")
        except Exception as e:
            logger.error(f"데이터 배치 저장 실패 (observations): {e}")


    def insert_ranking_batch(self, rows_to_insert: list[dict[str, Any]]):
        """랭킹 히스토리 저장"""
        if not rows_to_insert:
            return
            
        ws = self._get_worksheet("ranking_history")
        rows = []
        for data in rows_to_insert:
            row = []
            for col in cols:
                val = data.get(col)
                row.append(val if val is not None else "")
            rows.append(row)
            
        try:
            ws.append_rows(rows)
            logger.info(f"데이터 배치 저장 완료 (ranking_history): {len(rows)}건")
        except Exception as e:
            logger.error(f"데이터 저장 실패 (ranking_history): {e}")

    def get_latest_rankings(self, query: str) -> list[dict[str, Any]]:
        """특정 쿼리의 가장 최근 랭킹 데이터를 가져옵니다."""
        ws = self._get_worksheet("ranking_history")
        all_records = ws.get_all_records() # 성능 주의: 데이터가 많으면 필터링 로직 개선 필요
        
        # 특정 쿼리의 최신 시간대 데이터 필터링
        matches = [r for r in all_records if r.get("query") == query]
        if not matches:
            return []
            
        latest_time = max(m["collected_at"] for m in matches)
        return [m for m in matches if m["collected_at"] == latest_time]

    def get_mall_report_data(self, monitored_sellers: list[str] | None = None) -> dict[str, Any]:
        """쇼핑몰 리포트용 계층 데이터 구성 (Ranking 기반 통합 버전)"""
        monitored_sellers = monitored_sellers or []
        ws_rank = self._get_worksheet("ranking_history")
        all_ranks = ws_rank.get_all_records()
        
        if not all_ranks:
            return {}
            
        # 1. 쿼리별 최신 수집 시점 조회
        query_latest = {}
        for r in all_ranks:
            q = r.get("query")
            t = r.get("collected_at")
            if q not in query_latest or t > query_latest[q]:
                query_latest[q] = t
                
        # 2. 최신 랭킹 데이터만 필터링 및 리포트 구성
        report = {}
        for r in all_ranks:
            # 해당 쿼리의 최신 데이터가 아니면 스킵
            if r.get("collected_at") != query_latest.get(r.get("query")):
                continue
                
            mall = r.get("seller_name")
            if not mall: continue
            
            # 모니터링 대상 셀러인지 확인 (부분 일치 포함)
            is_monitored = False
            for m in monitored_sellers:
                if m in mall:
                    is_monitored = True
                    break
            
            if monitored_sellers and not is_monitored:
                continue

            # 카테고리 분류 (랭킹 데이터에 카테고리가 없으므로 쿼리나 고정값으로 추정)
            # 여기서는 편의상 "전체" 또는 쿼리 앞부분 사용
            cat = "전체"
            if cat not in report: report[cat] = {}
            if mall not in report[cat]: 
                report[cat][mall] = {
                    "total_products": 0,
                    "price_decreased_count": 0,
                    "products": []
                }
            
            # 가격 변동액 계산 (GSheet 특성상 단순화)
            # ranking_history에서 이전 가격 정보를 찾기는 비용이 크므로 0으로 우선 처리
            # (필요 시 observations 시트를 크로스 체크할 수도 있으나 구조 단순화 우선)
            delta = 0

            report[cat][mall]["total_products"] += 1
            report[cat][mall]["products"].append({
                "title": r.get("title", ""),
                "collected_at": r.get("collected_at", "")[:16],
                "curr_price_fmt": f"{int(r['price']):,}원" if r.get("price") else "-",
                "prev_price_fmt": "-",
                "delta_str": "0원",
                "price": r.get("price"),
                "url": r.get("product_url"),
                "history": []
            })
            
        return report

    def get_dashboard_data(self, targets: Any) -> dict[str, Any]:
        """대시보드 시각화용 통합 데이터 생성 (GSheet 버전)"""
        ws = self._get_worksheet("observations")
        records = ws.get_all_records()
        
        target_map = {t.name: t for t in targets}
        # KST 적용
        from .util import now_iso
        data = {
            "generated_at": now_iso(),
            "products": []
        }

        for name, t_config in target_map.items():
            # 특정 상품의 수집 기록 필터링 (성공한 것만)
            p_history = [r for r in records if r.get("target_name") == name and r.get("success") == 1]
            if not p_history:
                continue
            
            # 최신 기록
            latest = sorted(p_history, key=lambda x: x["collected_at"], reverse=True)[0]
            
            # 통계 계산
            prices = [int(r["price"]) for r in p_history if r.get("price")]
            all_time_low = min(prices) if prices else None
            all_time_high = max(prices) if prices else None
            
            def calc_avg(days):
                cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                recent_prices = [int(r["price"]) for r in p_history if r["collected_at"] >= cutoff and r.get("price")]
                return round(sum(recent_prices) / len(recent_prices)) if recent_prices else None

            product_data = {
                "name": name,
                "category": t_config.category,
                "rank_query": t_config.rank_query,
                "current_price": latest["price"],
                "seller": latest.get("seller_name") or "네이버",
                "status": latest.get("price_change_status"),
                "change_pct": latest.get("price_delta_pct"),
                "product_id": latest.get("product_id"),
                "avg_7d": calc_avg(7),
                "avg_30d": calc_avg(30),
                "avg_90d": calc_avg(90),
                "all_time_low": all_time_low,
                "all_time_high": all_time_high,
                "image_url": latest.get("image_url"),
                "search_rank": latest.get("search_rank"),
                "history": [
                    {"t": r["collected_at"], "p": r["price"]} for r in p_history[-200:] # 최근 200개로 제한
                ]
            }
            data["products"].append(product_data)
            
        return data

    def get_latest_success(self, target_name: str) -> dict[str, Any] | None:
        """특정 상품의 가장 최근 성공 수집 기록을 반환합니다."""
        ws = self._get_worksheet("observations")
        records = ws.get_all_records()
        matches = [r for r in records if r.get("target_name") == target_name and r.get("success") == 1]
        if not matches:
            return None
        return sorted(matches, key=lambda x: x["collected_at"], reverse=True)[0]

    def close(self):
        # gspread는 세션을 자동으로 관리하므로 명시적 종료가 필요 없으나 인터페이스 유지
        pass
