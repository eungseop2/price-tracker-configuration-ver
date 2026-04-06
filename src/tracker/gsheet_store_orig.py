import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger("tracker.gsheet_store")

# ?쒗듃蹂??ㅻ뜑 ?뺤쓽 (SQLite ?ㅽ궎留덉? ?숈씪?섍쾶 ?좎?)
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
            logger.info(f"援ш? ?ㅽ봽?덈뱶?쒗듃 ?곌껐 ?깃났: {self._sh.title}")
        except Exception as e:
            logger.error(f"援ш? ?ㅽ봽?덈뱶?쒗듃 ?곌껐 ?ㅽ뙣: {e}")
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
            logger.info(f"???쒗듃 ?앹꽦?? {name}")
            
        self._worksheets[name] = ws
        return ws

    def insert(self, payload: dict[str, Any]):
        """?⑥씪 ?곹뭹 ?섏쭛 湲곕줉 ???(?대??곸쑝濡?insert_batch ?쒖슜)"""
        self.insert_batch([payload])

    def insert_batch(self, payloads: list[dict[str, Any]]):
        """?щ윭 ?곹뭹 ?섏쭛 湲곕줉????踰덉뿉 ???(?깅뒫 諛??좊ː??理쒖쟻??"""
        if not payloads:
            return

        ws = self._get_worksheet("observations")
        cols = HEADERS["observations"]
        
        rows = []
        for p in payloads:
            row = []
            for col in cols:
                val = p.get(col)
                # GSheet 湲곕줉 ??None? 鍮?臾몄옄?대줈 蹂?섑븯???먮윭 諛⑹?
                if val is None:
                    row.append("")
                else:
                    row.append(val)
            rows.append(row)
            
        try:
            ws.append_rows(rows)
            logger.info(f"?곗씠??諛곗튂 ????꾨즺 (observations): {len(rows)}嫄?)
        except Exception as e:
            logger.error(f"?곗씠??諛곗튂 ????ㅽ뙣 (observations): {e}")

    def insert_mall_records(self, target_name: str, query: str, mall_name: str, category: str, items: list[dict[str, Any]]):
        """???紐??섏쭛 湲곕줉 ???""
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
            logger.error(f"?곗씠??????ㅽ뙣 (mall_observations): {e}")

    def insert_ranking_batch(self, rows_to_insert: list[dict[str, Any]]):
        """??궧 ?덉뒪?좊━ ???""
        if not rows_to_insert:
            return
            
        ws = self._get_worksheet("ranking_history")
        cols = HEADERS["ranking_history"]
        rows = [[data.get(col) for col in cols] for data in rows_to_insert]
        
        try:
            ws.append_rows(rows)
        except Exception as e:
            logger.error(f"?곗씠??????ㅽ뙣 (ranking_history): {e}")

    def get_latest_rankings(self, query: str) -> list[dict[str, Any]]:
        """?뱀젙 荑쇰━??媛??理쒓렐 ??궧 ?곗씠?곕? 媛?몄샃?덈떎."""
        ws = self._get_worksheet("ranking_history")
        all_records = ws.get_all_records() # ?깅뒫 二쇱쓽: ?곗씠?곌? 留롮쑝硫??꾪꽣留?濡쒖쭅 媛쒖꽑 ?꾩슂
        
        # ?뱀젙 荑쇰━??理쒖떊 ?쒓컙? ?곗씠???꾪꽣留?        matches = [r for r in all_records if r.get("query") == query]
        if not matches:
            return []
            
        latest_time = max(m["collected_at"] for m in matches)
        return [m for m in matches if m["collected_at"] == latest_time]

    def get_mall_report_data(self) -> dict[str, Any]:
        """?쇳븨紐?由ы룷?몄슜 怨꾩링 ?곗씠??援ъ꽦 (??쒕낫???명솚??"""
        ws = self._get_worksheet("mall_observations")
        records = ws.get_all_records()
        
        # ???`target_name`)蹂꾨줈 洹몃９?뷀븯??媛곴컖??理쒖떊 ?섏쭛 ?쒖젏 ?곗씠?곕? 痍⑦빀?⑸땲??
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
        
        # 移댄뀒怨좊━/紐곕퀎 洹몃９??        report = {}
        for r in latest_records:
            cat = r.get("category") or "湲고?"
            mall = r.get("mall_name")
            
            if cat not in report: report[cat] = {}
            if mall not in report[cat]: 
                report[cat][mall] = {
                    "total_products": 0,
                    "price_decreased_count": 0,
                    "products": []
                }
            
            # ?댁쟾 湲곕줉 李얘린 (蹂?숈븸 怨꾩궛??
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
                "curr_price_fmt": f"{int(r['price']):,}?? if r.get("price") else "-",
                "prev_price_fmt": f"{int(prev_price):,}?? if prev_price else "-",
                "delta_str": f"{delta:+,}?? if delta != 0 else "0??,
                "price": r["price"],
                "url": r["product_url"],
                "history": [] # 李⑦듃???덉뒪?좊━ (?꾩슂 ??蹂닿컯)
            })
            
        return report

    def get_dashboard_data(self, targets: Any) -> dict[str, Any]:
        """??쒕낫???쒓컖?붿슜 ?듯빀 ?곗씠???앹꽦 (GSheet 踰꾩쟾)"""
        ws = self._get_worksheet("observations")
        records = ws.get_all_records()
        
        target_map = {t.name: t for t in targets}
        # KST ?곸슜
        from .util import now_iso
        data = {
            "generated_at": now_iso(),
            "products": []
        }

        for name, t_config in target_map.items():
            # ?뱀젙 ?곹뭹???섏쭛 湲곕줉 ?꾪꽣留?(?깃났??寃껊쭔)
            p_history = [r for r in records if r.get("target_name") == name and r.get("success") == 1]
            if not p_history:
                continue
            
            # 理쒖떊 湲곕줉
            latest = sorted(p_history, key=lambda x: x["collected_at"], reverse=True)[0]
            
            # ?듦퀎 怨꾩궛
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
                "seller": latest.get("seller_name") or "?ㅼ씠踰?,
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
                    {"t": r["collected_at"], "p": r["price"]} for r in p_history[-200:] # 理쒓렐 200媛쒕줈 ?쒗븳
                ]
            }
            data["products"].append(product_data)
            
        return data

    def get_latest_success(self, target_name: str) -> dict[str, Any] | None:
        """?뱀젙 ?곹뭹??媛??理쒓렐 ?깃났 ?섏쭛 湲곕줉??諛섑솚?⑸땲??"""
        ws = self._get_worksheet("observations")
        records = ws.get_all_records()
        matches = [r for r in records if r.get("target_name") == target_name and r.get("success") == 1]
        if not matches:
            return None
        return sorted(matches, key=lambda x: x["collected_at"], reverse=True)[0]

    def close(self):
        # gspread???몄뀡???먮룞?쇰줈 愿由ы븯誘濡?紐낆떆??醫낅즺媛 ?꾩슂 ?놁쑝???명꽣?섏씠???좎?
        pass
