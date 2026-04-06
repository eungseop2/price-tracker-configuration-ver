from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .util import dump_json, ensure_dir, format_price

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_name TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    success INTEGER NOT NULL,
    status TEXT NOT NULL,
    config_mode TEXT,
    fallback_used INTEGER DEFAULT 0,
    title TEXT,
    price INTEGER,
    seller_name TEXT,
    product_id TEXT,
    product_type INTEGER,
    product_url TEXT,
    raw_payload TEXT,
    error_message TEXT,
    price_change_status TEXT,
    prev_price INTEGER,
    price_delta INTEGER,
    price_delta_pct REAL,
    alert_triggered INTEGER DEFAULT 0,
    image_url TEXT,
    search_rank INTEGER
);

CREATE INDEX IF NOT EXISTS idx_observations_target_time
ON observations(target_name, collected_at DESC);

CREATE TABLE IF NOT EXISTS ranking_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    rank INTEGER NOT NULL,
    collected_at TEXT NOT NULL,
    title TEXT,
    price INTEGER,
    seller_name TEXT,
    product_id TEXT,
    product_type INTEGER,
    product_url TEXT,
    image_url TEXT,
    is_ad INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_ranking_query_time
ON ranking_history(query, collected_at DESC);
"""

# ?몄쬆??愿??而щ읆?ㅼ? ?ㅽ궎留??뺤쓽?먯꽌 ?쒓굅?섏?留? 
# 留덉씠洹몃젅?댁뀡 濡쒖쭅?먯꽌??DB ?명솚?깆쓣 ?꾪빐 ?④꺼?먭굅???꾩슂??寃껊쭔 ?좎??⑸땲??
_MIGRATION_COLUMNS = [
    ("config_mode", "TEXT"),
    ("fallback_used", "INTEGER DEFAULT 0"),
    ("price_change_status", "TEXT"),
    ("prev_price", "INTEGER"),
    ("price_delta", "INTEGER"),
    ("price_delta_pct", "REAL"),
    ("alert_triggered", "INTEGER DEFAULT 0"),
    ("product_id", "TEXT"),
    ("image_url", "TEXT"),
    ("search_rank", "INTEGER"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    """湲곗〈 DB???좉퇋 而щ읆???놁쑝硫?ALTER TABLE濡?異붽??⑸땲??"""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(observations)").fetchall()}
    for col_name, col_type in _MIGRATION_COLUMNS:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE observations ADD COLUMN {col_name} {col_type}")
    conn.commit()


class ObservationStore:
    def __init__(self, db_path: str) -> None:
        db_path = str(Path(db_path).resolve())
        ensure_dir(Path(db_path).parent)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()
        _migrate(self.conn)

    def insert(self, row: dict[str, Any]) -> None:
        payload = dict(row)
        if "raw_payload" in payload and not isinstance(payload["raw_payload"], str):
            payload["raw_payload"] = dump_json(payload["raw_payload"])

        columns = [
            "target_name",
            "source_mode",
            "collected_at",
            "success",
            "status",
            "config_mode",
            "fallback_used",
            "title",
            "price",
            "seller_name",
            "product_id",
            "product_type",
            "product_url",
            "raw_payload",
            "error_message",
            "price_change_status",
            "prev_price",
            "price_delta",
            "price_delta_pct",
            "alert_triggered",
            "image_url",
            "search_rank",
        ]
        values = [payload.get(col) for col in columns]
        self.conn.execute(
            f"INSERT INTO observations ({','.join(columns)}) VALUES ({','.join(['?']*len(columns))})",
            values,
        )
        self.conn.commit()

    def get_latest_success(self, target_name: str) -> dict[str, Any] | None:
        """?뱀젙 ?곹뭹??媛??理쒓렐 ?깃났 ?섏쭛 湲곕줉(success=1)??諛섑솚?⑸땲??"""
        row = self.conn.execute(
            """
            SELECT * FROM observations
            WHERE target_name = ? AND success = 1 AND price IS NOT NULL
            ORDER BY collected_at DESC, id DESC
            LIMIT 1
            """,
            (target_name,),
        ).fetchone()
        return dict(row) if row else None

    def get_price_history(self, target_name: str, limit: int = 20) -> list[dict[str, Any]]:
        """?뱀젙 ?곹뭹??理쒓렐 ?섏쭛 ?대젰??諛섑솚?⑸땲??"""
        rows = self.conn.execute(
            """
            SELECT * FROM observations
            WHERE target_name = ?
            ORDER BY collected_at DESC, id DESC
            LIMIT ?
            """,
            (target_name, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_dashboard_data(self, targets: list[TargetConfig]) -> dict[str, Any]:
        """??쒕낫???쒓컖?붿슜 ?듯빀 ?곗씠?곕? 諛섑솚?⑸땲??(7??30??90??遺꾩꽍 ?ы븿)."""
        target_map = {t.name: t for t in targets}
        target_names = list(target_map.keys())

        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "products": []
        }

        for name in target_names:
            t_config = target_map[name]

            # 1. 理쒖떊 ?뺣낫 媛?몄삤湲?
            latest = self.get_latest_success(name)
            if not latest:
                continue

            # 2. 遺꾩꽍???곗씠??異붿텧 (?꾩껜 ?덉뒪?좊━ 遺꾩꽍 媛?ν븯?꾨줉 ?꾪꽣 ?쒓굅)
            hist_all = self.conn.execute(
                """
                SELECT collected_at, price 
                FROM observations 
                WHERE target_name = ? AND success = 1 AND price IS NOT NULL
                ORDER BY collected_at ASC
                """, (name,)
            ).fetchall()

            # 3. ??? 理쒖?/理쒓퀬媛 怨꾩궛 (?꾩껜 ?덉뒪?좊━ ???
            stats_all = self.conn.execute(
                """
                SELECT MIN(price) as min_p, MAX(price) as max_p
                FROM observations
                WHERE target_name = ? AND success = 1 AND price IS NOT NULL
                """, (name,)
            ).fetchone()
            all_time_low = stats_all["min_p"]
            all_time_high = stats_all["max_p"]

            if not hist_all:
                continue
            
            # 湲곌컙蹂??됯퇏 怨꾩궛 ?⑥닔 (?곗씠?곌? 遺議깊븯硫?None 諛섑솚)
            def calc_avg(days):
                cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                prices = [r["price"] for r in hist_all if datetime.fromisoformat(r["collected_at"].replace('Z', '+00:00')) >= cutoff]
                return round(sum(prices) / len(prices)) if prices else None

            product_data = {
                "name": name,
                "category": t_config.category,
                "rank_query": t_config.rank_query,
                "current_price": latest["price"],
                "seller": latest["seller_name"] or "?ㅼ씠踰?,
                "status": latest["price_change_status"],
                "change_pct": latest["price_delta_pct"],
                "product_id": latest["product_id"],
                "avg_7d": calc_avg(7),
                "avg_30d": calc_avg(30),
                "avg_90d": calc_avg(90),
                "all_time_low": all_time_low,
                "all_time_high": all_time_high,
                "image_url": latest["image_url"],
                "search_rank": latest.get("search_rank"),
                "history": [
                    {"t": r["collected_at"], "p": r["price"]} for r in hist_all[-500:] # 理쒓렐 500媛??곗씠???ъ씤?몃줈 ?뺤옣
                ]
            }
            data["products"].append(product_data)

        return data

    def export_dashboard_json(self, out_path: str, categories: dict[str, str] | None = None) -> str:
        """??쒕낫???곗씠?곕? JSON ?뚯씪濡???ν빀?덈떎."""
        data = self.get_dashboard_data(categories=categories)
        out = Path(out_path).resolve()
        ensure_dir(out.parent)
        out.write_text(dump_json(data), encoding="utf-8")
        return str(out)

    def export_latest_csv(self, out_path: str) -> str:
        query = """
        WITH ranked AS (
          SELECT
            *,
            ROW_NUMBER() OVER (
              PARTITION BY target_name
              ORDER BY collected_at DESC, id DESC
            ) AS rn
          FROM observations
        )
        SELECT *
        FROM ranked
        WHERE rn = 1
        ORDER BY target_name;
        """
        rows = self.conn.execute(query).fetchall()
        out = Path(out_path).resolve()
        ensure_dir(out.parent)
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "target_name", "collected_at", "config_mode", "source_mode", "fallback_used", "success", "status",
                "title", "price", "seller_name", "price_change_status", "prev_price",
                "price_delta", "price_delta_pct", "product_url", "error_message", "image_url", "search_rank"
            ])
            for r_raw in rows:
                r = dict(r_raw)
                writer.writerow([
                    r["target_name"], r["collected_at"], r.get("config_mode"), r["source_mode"], r.get("fallback_used", 0), r["success"], r["status"],
                    r["title"], r["price"], r["seller_name"], r["price_change_status"], r["prev_price"],
                    r["price_delta"], r["price_delta_pct"], r["product_url"], r["error_message"],
                    r.get("image_url"), r.get("search_rank")
                ])
        return str(out)

    def export_html_report(self, out_path: str, limit: int = 20) -> str:
        """HTML 由ы룷???앹꽦 (?댁뒪耳?댄봽 諛??대갚 ?뺣낫 異붽?)"""
        import html as py_html
        target_names = [
            r[0] for r in self.conn.execute(
                "SELECT DISTINCT target_name FROM observations ORDER BY target_name"
            ).fetchall()
        ]

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sections = []
        for name in target_names:
            history = self.get_price_history(name, limit=limit)
            rows_html = []
            for rec in history:
                status_cls = rec.get("price_change_status") or "UNKNOWN"
                status_color = "#94a3b8"  # 湲곕낯 ?뚯깋
                if status_cls == "PRICE_DOWN": status_color = "#22c55e"  # 珥덈줉
                elif status_cls == "PRICE_UP": status_color = "#ef4444"  # 鍮④컯
                elif status_cls == "PRICE_SAME": status_color = "#6b7280" # 以묐┰ ?뚯깋
                
                row_style = ""
                if not rec.get("success"):
                    row_style = 'style="background: #2d0a0a"'  # ???대몢??鍮④컯 諛곌꼍 (success=0)

                delta_pct = rec.get("price_delta_pct")
                pct_str = f"{delta_pct:+.1f}%" if delta_pct is not None else "-"
                delta_str = f"{rec.get('price_delta'):+,}" if rec.get("price_delta") is not None else "-"

                cfg_m = py_html.escape(str(rec.get("config_mode") or "-"))
                src_m = py_html.escape(str(rec.get("source_mode") or "-"))
                route_html = f"{cfg_m} &rarr; {src_m}"
                if rec.get("fallback_used"):
                    route_html += ' <span style="background:#f59e0b; color:#fff; font-size:10px; padding:1px 4px; border-radius:4px; font-weight:700">FALLBACK</span>'
                
                rows_html.append(f"""
        <tr {row_style}>
          <td style="font-size:11px">{py_html.escape((rec.get('collected_at') or '')[:19].replace('T', ' '))}</td>
          <td style="font-size:12px; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap" title="{py_html.escape(rec.get('title') or '')}">{py_html.escape(rec.get('title') or '-')}</td>
          <td>{py_html.escape(rec.get('seller_name') or '-')}</td>
          <td style="font-size:11px; color:#94a3b8">{route_html}</td>
          <td style="font-weight:700">{format_price(rec.get('price'))}</td>
          <td style="color:#94a3b8">{format_price(rec.get('prev_price'))}</td>
          <td style="color:{status_color}">{delta_str}</td>
          <td style="color:{status_color}; font-weight:700">{pct_str}</td>
          <td style="font-size:12px; color:#94a3b8">{py_html.escape(str(rec.get('search_rank') or '-'))}</td>
          <td style="color:{status_color}; font-size:12px; font-weight:700">{py_html.escape(str(status_cls or ""))}</td>
          <td style="font-size:11px; color:#cbd5e1">{py_html.escape(str(rec.get('status') or ''))}</td>
        </tr>""")

            section = f"""
  <section style="margin-bottom:40px">
    <h2 style="color:#f1f5f9; border-bottom:1px solid #334155; padding-bottom:8px; margin-bottom:12px">{name}</h2>
    <div style="overflow-x:auto">
      <table style="width:100%; border-collapse:collapse; font-size:14px">
        <thead>
            <tr style="background:#1e293b; color:#94a3b8">
            <th style="padding:10px; text-align:left">?섏쭛?쒓컖</th>
            <th style="padding:10px; text-align:left">?곹뭹紐?/th>
            <th style="padding:10px; text-align:left">?먮ℓ??/th>
            <th style="padding:10px; text-align:left">?섏쭛寃쎈줈</th>
            <th style="padding:10px; text-align:left">?꾩옱媛</th>
            <th style="padding:10px; text-align:left">?댁쟾媛</th>
            <th style="padding:10px; text-align:left">蹂?숈븸</th>
            <th style="padding:10px; text-align:left">蹂?숇쪧</th>
            <th style="padding:10px; text-align:left">?쒖쐞</th>
            <th style="padding:10px; text-align:left">蹂?숈긽??/th>
            <th style="padding:10px; text-align:left">?섏쭛?곹깭</th>
          </tr>
        </thead>
        <tbody style="color:#e2e8f0">
          {''.join(rows_html)}
        </tbody>
      </table>
    </div>
  </section>"""
            sections.append(section)

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>?ㅼ씠踰??쇳븨 媛寃?異붿쟻 由ы룷??/title>
<style>
  body {{ background: #0f172a; color: #e2e8f0; font-family: system-ui, sans-serif; padding: 30px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 12px; border-bottom: 1px solid #1e293b; }}
  tr:hover {{ background: #1e293b; }}
</style>
</head>
<body>
  <h1 style="margin-bottom:8px">?뱤 媛寃?異붿쟻 由ы룷??/h1>
  <p style="color:#64748b; margin-bottom:30px">?앹꽦: {now_str}</p>
  {''.join(sections)}
</body>
</html>"""
        out = Path(out_path).resolve()
        ensure_dir(out.parent)
        out.write_text(html_content, encoding="utf-8")
        return str(out)

    def close(self) -> None:
        self.conn.close()


class RankingStore:
    def __init__(self, db_path: str) -> None:
        db_path = str(Path(db_path).resolve())
        ensure_dir(Path(db_path).parent)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        
        # [Migration] is_ad 而щ읆 異붽? (湲곗〈 DB ???
        try:
            self.conn.execute("ALTER TABLE ranking_history ADD COLUMN is_ad INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # ?대? 而щ읆??議댁옱??
            
        self.conn.commit()

    def insert_ranking_batch(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        columns = [
            "query", "rank", "collected_at", "title", "price",
            "seller_name", "product_id", "product_type", "product_url", "image_url", "is_ad"
        ]
        
        values = []
        for row in rows:
            values.append([row.get(col) for col in columns])
            
        self.conn.executemany(
            f"INSERT INTO ranking_history ({','.join(columns)}) VALUES ({','.join(['?'] * len(columns))})",
            values
        )
        self.conn.commit()

    def get_latest_rankings(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        # 媛??理쒓렐 ?섏쭛???쒓컙??李얠쓬
        recent_time_row = self.conn.execute(
            "SELECT collected_at FROM ranking_history WHERE query = ? ORDER BY collected_at DESC LIMIT 1", 
            (query,)
        ).fetchone()
        
        if not recent_time_row:
            return []
            
        recent_time = recent_time_row["collected_at"]
        
        rows = self.conn.execute(
            """
            SELECT * FROM ranking_history 
            WHERE query = ? AND collected_at = ?
            ORDER BY rank ASC
            LIMIT ?
            """,
            (query, recent_time, limit)
        ).fetchall()
        
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()

