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
        "fallback_used", "alert_triggered", "product_type", "product_code", "is_unauthorized"
    ],
    "mall_observations": [
        "target_name", "query", "mall_name", "category", "collected_at", 
        "title", "price", "product_id", "product_type", "product_url", "image_url", "search_rank", "product_code", "is_unauthorized"
    ],
    "ranking_history": [
        "query", "rank", "collected_at", "title", "price", "seller_name", 
        "product_id", "product_type", "product_url", "image_url", "is_ad", "product_code", "is_unauthorized"
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
            # 환경변수에서 온 JSON 문자열 정제
            raw_key = self.service_account_json.strip()
            
            # 만약 raw_key가 로컬 파일 경로이고 파일이 존재한다면 파일에서 직접 읽기 (쉘 이스케이프 문제 우회)
            import os
            if os.path.exists(raw_key):
                with open(raw_key, "rb") as f:
                    content = f.read().decode("utf-8", errors="replace").replace("\xa0", " ").strip()
                    raw_key = content
            elif raw_key.startswith('"') and raw_key.endswith('"'):
                # 만약 따옴표로 감싸져 있다면 제거
                raw_key = raw_key[1:-1]
            
            # JSON 파싱 시도
            try:
                # 1. 기본 파싱 시도
                info = json.loads(raw_key)
            except json.JSONDecodeError:
                try:
                    # 2. 쉘 환경(PowerShell 등)에서 오염된 이스케이프 및 중첩 백슬래시 정제
                    # - 유효하지 않은 백슬래시는 제거하고, 이스케이프된 \n 등은 정상화
                    import re
                    # \\n 등을 실제 줄바꿈으로 변경하기 전, JSON에 부적합한 백슬래시 조합 제거
                    # (예: \> -> >, \m -> m 등)
                    cleaned_key = re.sub(r'\\([^nrt"\\/u])', r'\1', raw_key)
                    # 여전히 남아있는 \\n (리터럴 백슬래시+n) 처리
                    cleaned_key = cleaned_key.replace('\\n', '\n')
                    info = json.loads(cleaned_key, strict=False)
                except json.JSONDecodeError as e:
                    logger.error(f"구글 서비스 계정 키 JSON 파싱 최종 실패: {e}")
                    raise e

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            credentials = Credentials.from_service_account_info(info, scopes=scopes)
            self._gc = gspread.authorize(credentials)
            self._sh = self._gc.open_by_key(self.spreadsheet_id)
            logger.info(f"구글 스프레드시트 연결 성공: {self._sh.title}")
        except json.JSONDecodeError as e:
            logger.error(f"구글 서비스 계정 키 JSON 파싱 실패: {e}. 키의 형식을 확인하세요.")
            raise
        except Exception as e:
            logger.error(f"구글 스프레드시트 연결 중 최종 실패: {e}")
            raise

    def _get_worksheet(self, name: str):
        self._connect()
        if name in self._worksheets:
            return self._worksheets[name]
        
        try:
            ws = self._sh.worksheet(name)
            # 마이그레이션: 기존 시트의 헤더가 로컬의 HEADERS와 일치하는지 확인
            expected_headers = HEADERS.get(name)
            current_headers = ws.row_values(1)
            
            if expected_headers:
                # 컬럼 수가 부족하거나 헤더가 비어 있으면 최신화
                if len(current_headers) < len(expected_headers):
                    try:
                        # 첫 번째 행을 전체 HEADERS로 업데이트 (A1 섹션)
                        ws.update('A1', [expected_headers])
                        logger.info(f"시트 '{name}'의 헤더를 최신 버전으로 업데이트했습니다.")
                        current_headers = expected_headers
                    except Exception as e:
                        logger.warning(f"시트 '{name}' 헤더 자동 업데이트 중 경고: {e}")
            
            self._worksheets[name] = ws
            # 헤더 정보 캐싱 (성능 최적화)
            if not hasattr(self, '_headers_cache'):
                self._headers_cache = {}
            self._headers_cache[name] = current_headers
            
        except gspread.exceptions.WorksheetNotFound:
            cols = HEADERS.get(name, ["data"])
            ws = self._sh.add_worksheet(title=name, rows=1000, cols=len(cols))
            ws.append_row(cols)
            logger.info(f"새 시트 생성됨: {name}")
            self._worksheets[name] = ws
            if not hasattr(self, '_headers_cache'):
                self._headers_cache = {}
            self._headers_cache[name] = cols
            
        return ws

    def _get_cached_headers(self, name: str):
        """시트의 헤더 정보를 가져오거나 캐시에서 반환"""
        if hasattr(self, '_headers_cache') and name in self._headers_cache:
            return self._headers_cache[name]
        
        ws = self._get_worksheet(name)
        # _get_worksheet에서 이미 캐싱을 시도하지만, 안전을 위해 보장
        return getattr(self, '_headers_cache', {}).get(name, ws.row_values(1))

    def _get_all_records_safe(self, ws):
        """gspread의 get_all_records()가 빈 헤더 중복 시 에러를 내는 문제를 해결한 안전한 버전"""
        all_values = ws.get_all_values()
        if not all_values:
            return []
        
        headers = all_values[0]
        
        records = []
        for row in all_values[1:]:
            record = {}
            for i, h in enumerate(headers):
                if h: # 헤더가 비어있지 않은 컬럼만 데이터로 포함
                    record[h] = row[i] if i < len(row) else ""
            records.append(record)
        return records

    def insert(self, payload: dict[str, Any]):
        """단일 상품 수집 기록 저장 (내부적으로 insert_batch 활용)"""
        self.insert_batch([payload])

    def insert_batch(self, payloads: list[dict[str, Any]]):
        """여러 상품 수집 기록을 한 번에 저장 (컬럼 순서에 독립적으로 실제 헤더에 맞춰 매핑)"""
        if not payloads:
            return

        ws = self._get_worksheet("observations")
        # 캐싱된 헤더 순서를 읽어와서 매핑 기준으로 삼음 (열 밀림 방지 + 성능 향상)
        current_headers = self._get_cached_headers("observations")
        
        rows = []
        for p in payloads:
            row = []
            for col in current_headers:
                if not col:
                    row.append("")
                    continue
                val = p.get(col)
                row.append("" if val is None else val)
            rows.append(row)
            
        try:
            ws.append_rows(rows, value_input_option='RAW')
            logger.info(f"데이터 배치 저장 완료 (observations): {len(rows)}건")
        except Exception as e:
            logger.error(f"데이터 배치 저장 실패 (observations): {e}")

    def insert_mall_records(self, target_name: str, query: str, mall_name: str, category: str, items: list[dict[str, Any]]):
        """특정 쇼핑몰 수집 기록 저장 (컬럼 순서 독립형)"""
        if not items:
            return
        
        ws = self._get_worksheet("mall_observations")
        current_headers = self._get_cached_headers("mall_observations")

        rows = []
        for itm in items:
            p = itm.copy()
            p["target_name"] = target_name
            p["query"] = query
            p["mall_name"] = mall_name
            p["category"] = category
            
            row = []
            for col in current_headers:
                if not col:
                    row.append("")
                    continue
                val = p.get(col)
                row.append("" if val is None else val)
            rows.append(row)
        
        try:
            ws.append_rows(rows, value_input_option='RAW')
            logger.info(f"쇼핑몰 데이터 저장 성공: {target_name} ({len(rows)}건)")
        except Exception as e:
            logger.error(f"쇼핑몰 데이터 저장 실패 (mall_observations): {e}")

    def insert_ranking_batch(self, rows_to_insert: list[dict[str, Any]]):
        """랭킹 히스토리 저장"""
        if not rows_to_insert:
            return
            
        ws = self._get_worksheet("ranking_history")
        current_headers = self._get_cached_headers("ranking_history")

        rows = []
        for data in rows_to_insert:
            row = []
            for col in current_headers:
                if not col:
                    row.append("")
                    continue
                val = data.get(col)
                row.append("" if val is None else val)
            rows.append(row)
        
        try:
            ws.append_rows(rows, value_input_option='RAW')
            logger.info(f"랭킹 히스토리 저장 완료: {len(rows)}건")
        except Exception as e:
            logger.error(f"랭킹 히스토리 저장 실패 (ranking_history): {e}")

    def get_latest_rankings(self, query: str) -> list[dict[str, Any]]:
        """특정 쿼리의 가장 최근 랭킹 데이터를 가져옵니다."""
        ws = self._get_worksheet("ranking_history")
        all_records = self._get_all_records_safe(ws)
        
        matches = [r for r in all_records if r.get("query") == query]
        if not matches:
            return []
            
        latest_time = max(m["collected_at"] for m in matches)
        return [m for m in matches if m["collected_at"] == latest_time]

    def get_mall_report_data(self, monitored_sellers: list[str] | None = None) -> dict[str, Any]:
        """쇼핑몰 리포트용 계층 데이터 구성 (대시보드 노출)"""
        ws = self._get_worksheet("mall_observations")
        records = self._get_all_records_safe(ws)
        
        if not records:
            return {}
            
        # Target별 최신 수집 시점 찾기
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
        
        # 카테고리/몰별 그룹화 및 필터링
        report = {}
        from .util import format_price, normalize_for_match
        
        # 필터링 및 정규화용 셋 준비
        m_sellers_norm = {normalize_for_match(s) for s in (monitored_sellers or [])}
        
        for r in latest_records:
            raw_mall = r.get("mall_name", "")
            if not raw_mall: continue
            
            # 몰 이름 정규화 (필터링 및 그룹화 목적)
            norm_mall = normalize_for_match(raw_mall)
            if norm_mall == "디엠에이씨": 
                norm_mall = "dmac"
            
            # 필터링 로직 (monitored_sellers가 지정된 경우)
            if monitored_sellers:
                if norm_mall not in m_sellers_norm:
                    # 원본 이름에 포함되는지 한 번 더 확인 (예: "dmac 네이버 스마트스토어" 등 대응)
                    is_contained = any(s in norm_mall for s in m_sellers_norm)
                    if not is_contained:
                        continue

            cat = r.get("category") or "기타"
            # 대시보드 표시용 이름 (최초 발견 시의 정규화된 이름을 키로 사용하되, 
            # dmac/디엠에이씨는 'dmac'으로 통일)
            display_mall = norm_mall
            
            if cat not in report: report[cat] = {}
            if display_mall not in report[cat]: 
                report[cat][display_mall] = {
                    "total_products": 0,
                    "price_decreased_count": 0,
                    "products": []
                }
            
            # 이하 데이터 구성 시 mall 대신 display_mall 사용
            mall = display_mall
            
            # 이전 가격 찾기 (같은 몰의 같은 상품 ID 중 직전 수집 시점)
            title = r.get("title", "")
            p_id = str(r.get("product_id") or "")
            
            try:
                curr_price = int(r.get("price") or 0)
            except (ValueError, TypeError):
                curr_price = 0
                
            prev_price = 0
            
            # 같은 몰의 같은 ID(없으면 이름)를 가진 이전 기록들 필터링 (동의어 및 대소문자 무시 매칭 적용)
            def is_same_mall(m1, m2):
                if not m1 or not m2: return False
                n1 = normalize_for_match(m1)
                n2 = normalize_for_match(m2)
                if n1 == "디엠에이씨": n1 = "dmac"
                if n2 == "디엠에이씨": n2 = "dmac"
                return n1 == n2
            
            if p_id:
                history = [h for h in records if is_same_mall(h.get("mall_name"), mall) and str(h.get("product_id")) == p_id and h["collected_at"] < r["collected_at"]]
            else:
                history = [h for h in records if is_same_mall(h.get("mall_name"), mall) and h.get("title") == title and h["collected_at"] < r["collected_at"]]
                
            if history:
                latest_h = sorted(history, key=lambda x: str(x["collected_at"]), reverse=True)[0]
                try:
                    prev_price = int(latest_h.get("price") or 0)
                except (ValueError, TypeError):
                    prev_price = 0
            
            delta = curr_price - prev_price if prev_price > 0 else 0
            delta_str = "0"
            if delta < 0:
                delta_str = f"-{format_price(abs(delta))}"
                report[cat][mall]["price_decreased_count"] += 1
            elif delta > 0:
                delta_str = f"+{format_price(delta)}"
            
            # 히스토리 데이터 구성 (그래프용 최근 50개 포인트)
            all_history = sorted(history + [r], key=lambda x: str(x["collected_at"]))
            chart_history = []
            for h in all_history[-50:]:
                try:
                    h_price = int(h.get("price") or 0)
                except (ValueError, TypeError):
                    h_price = 0
                chart_history.append({
                    "t": h["collected_at"],
                    "p": h_price
                })
            
            report[cat][mall]["total_products"] += 1
            report[cat][mall]["products"].append({
                "title": title,
                "collected_at": r.get("collected_at", "")[:16],
                "price": curr_price,
                "curr_price_fmt": format_price(curr_price),
                "prev_price_fmt": format_price(prev_price) if prev_price > 0 else "-",
                "delta": delta,
                "delta_str": delta_str,
                "url": r.get("product_url", ""),
                "history": chart_history
            })
            
        return report

    def get_dashboard_data(self, targets: Any) -> dict[str, Any]:
        """대시보드 UI용 데이터 생성"""
        ws = self._get_worksheet("observations")
        records = self._get_all_records_safe(ws)
        
        # 과거 '네이버' 판매처 소급 매칭을 위해 mall_observations 데이터 로드 및 인덱싱
        mws = self._get_worksheet("mall_observations")
        mall_records = self._get_all_records_safe(mws)
        from .util import parse_int
        m_idx = {}
        for mr in mall_records:
            t_name = mr.get("target_name")
            # 시간 동기화 오차 대응: 분 단위까지 인덱싱하되, 전후 1분 정도의 오차를 허용하기 위해 복수 키 등록 (선택적)
            t_at = str(mr.get("collected_at") or "")[:16] 
            price = str(parse_int(mr.get("price")))
            if t_name and t_at and price:
                key = f"{t_name}|{t_at}|{price}"
                # 같은 시간에 여러 몰이 있을 수 있으나, 보통 최저가 하나이므로 덮어씀
                m_idx[key] = mr.get("mall_name")

        target_map = {t.name: t for t in targets}
        from .util import utc_now_iso
        from datetime import datetime, timedelta, timezone
        
        data = {
            "generated_at": utc_now_iso(),
            "products": []
        }

        now = datetime.now(timezone.utc)

        for name, t_config in target_map.items():
            p_history = [r for r in records if r.get("target_name") == name and str(r.get("success")) == "1"]
            if not p_history:
                continue
            
            # 시간순 정렬 (ISO 날짜 문자열 정렬)
            p_history_sorted = sorted(p_history, key=lambda x: str(x.get("collected_at", "")))
            latest = p_history_sorted[-1]
            
            prices = []
            for r in p_history_sorted:
                try:
                    p = int(r.get("price") or 0)
                    if p > 0: prices.append(p)
                except (ValueError, TypeError):
                    continue
            
            # 통계 계산
            all_time_low = min(prices) if prices else None
            all_time_high = max(prices) if prices else None
            
            # 7일/30일 평균 계산
            avg_7d = None
            avg_30d = None
            if prices:
                try:
                    prices_7d = []
                    prices_30d = []
                    for r in p_history_sorted:
                        if not r.get("price") or not r.get("collected_at"):
                            continue
                        try:
                            # ISO 형식 파싱 (타임존 포함/미포함 모두 대응)
                            ts_str = str(r["collected_at"])
                            if "+" in ts_str or ts_str.endswith("Z"):
                                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            else:
                                ts = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
                            
                            age_days = (now - ts).total_seconds() / 86400
                            p = int(r["price"])
                            if age_days <= 7:
                                prices_7d.append(p)
                            if age_days <= 30:
                                prices_30d.append(p)
                        except (ValueError, TypeError):
                            continue
                    
                    if prices_7d:
                        avg_7d = round(sum(prices_7d) / len(prices_7d))
                    if prices_30d:
                        avg_30d = round(sum(prices_30d) / len(prices_30d))
                except Exception:
                    pass
            
            # 이력 포인트 구성 (판매처 정보 포함 및 소급 매칭 적용)
            history_points = []
            for r in p_history_sorted[-1000:]:
                s_name = r.get("seller_name")
                if not s_name or s_name == "네이버":
                    t_at = str(r.get("collected_at") or "")[:16]
                    price = str(parse_int(r.get("price")))
                    key = f"{name}|{t_at}|{price}"
                    # 매칭 안될 시 전후 1분 오차 대응을 위해 추가 시도 (분 단위 반올림 등은 복잡하므로 단순[:16] 유지하되 util.parse_int 적용)
                    s_name = m_idx.get(key) or "네이버"
                
                history_points.append({
                    "t": r["collected_at"],
                    "p": int(r.get("price") or 0),
                    "s": s_name
                })

            # 최신 기록의 판매처명도 '네이버'인 경우 소급 매칭 시도
            latest_seller = latest.get("seller_name")
            if not latest_seller or latest_seller == "네이버":
                t_at_latest = str(latest.get("collected_at") or "")[:16]
                p_latest = str(parse_int(latest.get("price")))
                latest_seller = m_idx.get(f"{name}|{t_at_latest}|{p_latest}") or "네이버"

            product_data = {
                "name": name,
                "category": t_config.category,
                "current_price": int(latest.get("price") or 0),
                "seller": latest_seller,
                "status": latest.get("price_change_status"),
                "change_pct": float(latest.get("price_delta_pct") or 0.0),
                "product_id": latest.get("product_id"),
                "product_type": latest.get("product_type"),
                "product_url": latest.get("product_url"),
                "image_url": latest.get("image_url"),
                "search_rank": int(latest.get("search_rank") or 0) if latest.get("search_rank") else None,
                "product_code": latest.get("product_code"),
                "is_unauthorized": int(latest.get("is_unauthorized") or 0),
                "rank_query": getattr(t_config, "rank_query", None) or name,
                "all_time_low": all_time_low,
                "all_time_high": all_time_high,
                "avg_7d": avg_7d,
                "avg_30d": avg_30d,
                "history": history_points
            }
            data["products"].append(product_data)
            
        return data

    def get_latest_success(self, target_name: str) -> dict[str, Any] | None:
        """특정 상품의 가장 최근 성공 수집 기록 반환"""
        ws = self._get_worksheet("observations")
        records = self._get_all_records_safe(ws)
        matches = [r for r in records if r.get("target_name") == target_name and str(r.get("success")) == "1"]
        if not matches:
            return None
        latest = sorted(matches, key=lambda x: x["collected_at"], reverse=True)[0]
        # 가격 데이터 정수형 변환 보장
        if "price" in latest:
            try:
                latest["price"] = int(latest["price"] or 0)
            except (ValueError, TypeError):
                latest["price"] = 0
        return latest

    def close(self):
        pass
