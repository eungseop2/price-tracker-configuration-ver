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
    "mall_observations": [
        "target_name", "query", "mall_name", "category", "collected_at", 
        "title", "price", "product_id", "product_type", "product_url", "image_url", "search_rank"
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
            cols = HEADERS.get(name, ["data"])
            ws = self._sh.add_worksheet(title=name, rows="1000", cols=str(len(cols)))
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

    def insert_mall_records(self, target_name: str, query: str, mall_name: str, category: str, items: list[dict[str, Any]]):
        """셀러 몰 수집 기록 저장"""
        if not items:
            return
        
        ws = self._get_worksheet("mall_observations")
        cols = HEADERS["mall_observations"]
        rows = []
        for itm in items:
            row_data = {
                "target_name": target_name,
                "query": query,
                "mall_name": mall_name,
                "category": category,
                **itm
            }
            rows.append([row_data.get(col) for col in cols])
        
        try:
            ws.append_rows(rows)
        except Exception as e:
            logger.error(f"데이터 저장 실패 (mall_observations): {e}")

    def insert_ranking_batch(self, rows_to_insert: list[dict[str, Any]]):
        """랭킹 히스토리 저장"""
        if not rows_to_insert:
            return
            
        ws = self._get_worksheet("ranking_history")
        cols = HEADERS["ranking_history"]
        rows = [[data.get(col) for col in cols] for data in rows_to_insert]
        
        try:
            ws.append_rows(rows)
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

    def get_mall_report_data(self) -> dict[str, Any]:
        """쇼핑몰 리포트용 계층 데이터 구성 (대시보드 호환용)"""
        ws = self._get_worksheet("mall_observations")
        records = ws.get_all_records()
        
        # 셀러(`target_name`)별로 그룹화하여 각각의 최신 수집 시점 데이터를 취합합니다.
        if not records:
            return {}
            
        by_target = {}
        for r in records:
            tn = r.get("target_name")
            if not tn: continue
            if tn not in by_target: by_target[tn] = []
            by_target[tn].append(r)
            
        latest_records = []
        for tn, group in by_target.items():
            max_t = max(g["collected_at"] for g in group)
            latest_records.extend([g for g in group if g["collected_at"] == max_t])
        
        # 카테고리/몰별 그룹화
        report = {}
        for r in latest_records:
            cat = r.get("category") or "기타"
            mall = r.get("mall_name")
            
            if cat not in report: report[cat] = {}
            if mall not in report[cat]: 
                report[cat][mall] = {
                    "total_products": 0,
                    "price_decreased_count": 0,
                    "products": []
                }
            
            # 이전 기록 찾기 (변동액 계산용)
            prev_records = [rec for rec in records if rec.get("product_id") == r.get("product_id") and rec["collected_at"] < latest_time]
            prev_price = None
            delta = 0
            if prev_records:
                prev_latest = sorted(prev_records, key=lambda x: x["collected_at"], reverse=True)[0]
                prev_price = prev_latest.get("price")
                if prev_price and r.get("price"):
                    delta = int(r["price"]) - int(prev_price)

            report[cat][mall]["total_products"] += 1
            if delta < 0:
                report[cat][mall]["price_decreased_count"] += 1

            report[cat][mall]["products"].append({
                "title": r["title"],
                "collected_at": r["collected_at"][:16], # YYYY-MM-DD HH:mm
                "curr_price_fmt": f"{int(r['price']):,}원" if r.get("price") else "-",
                "prev_price_fmt": f"{int(prev_price):,}원" if prev_price else "-",
                "delta_str": f"{delta:+,}원" if delta != 0 else "0원",
                "price": r["price"],
                "url": r["product_url"],
                "history": [] # 차트용 히스토리 (필요 시 보강)
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
