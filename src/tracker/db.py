from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import TargetConfig

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
    search_rank INTEGER,
    product_code TEXT,
    is_unauthorized INTEGER DEFAULT 0
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
    is_ad INTEGER DEFAULT 0,
    product_code TEXT,
    is_unauthorized INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_ranking_query_time
ON ranking_history(query, collected_at DESC);
"""

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
    ("product_code", "TEXT"),
    ("is_unauthorized", "INTEGER DEFAULT 0"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    """기존 DB에 신규 컬럼이 없으면 ALTER TABLE로 추가합니다."""
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
            "target_name", "source_mode", "collected_at", "success", "status",
            "config_mode", "fallback_used", "title", "price", "seller_name",
            "product_id", "product_type", "product_url", "raw_payload", "error_message",
            "price_change_status", "prev_price", "price_delta", "price_delta_pct",
            "alert_triggered", "image_url", "search_rank", "product_code", "is_unauthorized"
        ]
        values = [payload.get(col) for col in columns]
        self.conn.execute(
            f"INSERT INTO observations ({','.join(columns)}) VALUES ({','.join(['?']*len(columns))})",
            values,
        )
        self.conn.commit()

    def get_latest_success(self, target_name: str) -> dict[str, Any] | None:
        """특정 상품의 가장 최근 성공 수집 기록을 반환합니다."""
        row = self.conn.execute(
            """
            SELECT * FROM observations
            WHERE target_name = ? AND success = 1 AND price IS NOT NULL
            ORDER BY collected_at DESC, id DESC
            LIMIT 1
            """, (target_name,)
        ).fetchone()
        return dict(row) if row else None

    def get_price_history(self, target_name: str, limit: int = 20) -> list[dict[str, Any]]:
        """특정 상품의 최근 수집 이력을 반환합니다."""
        rows = self.conn.execute(
            """
            SELECT * FROM observations
            WHERE target_name = ?
            ORDER BY collected_at DESC, id DESC
            LIMIT ?
            """, (target_name, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_dashboard_data(self, targets: list[TargetConfig], monitored_sellers: list[str] | None = None) -> dict[str, Any]:
        """대시보드 시각화용 통합 데이터를 생성합니다."""
        target_map = {t.name: t for t in targets}
        target_names = list(target_map.keys())
        monitored_sellers = monitored_sellers or []

        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "products": []
        }

        for name in target_names:
            t_config = target_map[name]
            latest = self.get_latest_success(name)
            if not latest: continue

            hist_all = self.conn.execute(
                "SELECT collected_at, price FROM observations WHERE target_name = ? AND success = 1 ORDER BY collected_at ASC", (name,)
            ).fetchall()
            
            stats = self.conn.execute(
                "SELECT MIN(price) as min_p, MAX(price) as max_p FROM observations WHERE target_name = ? AND success = 1", (name,)
            ).fetchone()

            def calc_avg(days):
                cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                prices = [r["price"] for r in hist_all if datetime.fromisoformat(r["collected_at"].replace('Z', '+00:00')) >= cutoff]
                return round(sum(prices) / len(prices)) if prices else None

            data["products"].append({
                "name": name, "category": t_config.category, "rank_query": t_config.rank_query,
                "current_price": latest["price"], "seller": latest["seller_name"] or "네이버",
                "status": latest["price_change_status"], "change_pct": latest["price_delta_pct"],
                "avg_7d": calc_avg(7), "avg_30d": calc_avg(30), "avg_90d": calc_avg(90),
                "all_time_low": stats["min_p"], "all_time_high": stats["max_p"],
                "image_url": latest["image_url"], "search_rank": latest.get("search_rank"),
                "product_code": latest.get("product_code"),
                "is_unauthorized": latest.get("is_unauthorized", 0),
                "history": [{"t": r["collected_at"], "p": r["price"]} for r in hist_all[-500:]]
            })

        # 쇼핑몰 추적 데이터 생성
        mall_reports = {"categories": {}}
        for name in target_names:
            t_config = target_map[name]
            cat = t_config.category or "기타"
            if cat not in mall_reports["categories"]: mall_reports["categories"][cat] = {}
            
            query = t_config.rank_query or name
            latest_rankings = self.conn.execute(
                """
                SELECT * FROM ranking_history WHERE query = ? AND collected_at = (
                    SELECT collected_at FROM ranking_history WHERE query = ? ORDER BY collected_at DESC LIMIT 1
                )
                """, (query, query)
            ).fetchall()
            
            for mall in monitored_sellers:
                if mall not in mall_reports["categories"][cat]:
                    mall_reports["categories"][cat][mall] = {"total_products": 0, "products": []}
                
                mall_prods = [dict(r) for r in latest_rankings if mall in (r["seller_name"] or "")]
                for p in mall_prods:
                    mall_reports["categories"][cat][mall]["products"].append({
                        "collected_at": p["collected_at"][:16].replace("T", " "),
                        "title": p["title"], "curr_price_fmt": format_price(p["price"]),
                        "url": p["product_url"], "history": [{"t": p["collected_at"], "p": p["price"]}]
                    })
                    mall_reports["categories"][cat][mall]["total_products"] += 1

        data["mall_reports"] = mall_reports
        return data

    def close(self) -> None:
        self.conn.close()


class RankingStore:
    def __init__(self, db_path: str) -> None:
        db_path = str(Path(db_path).resolve())
        ensure_dir(Path(db_path).parent)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        try:
            self.conn.execute("ALTER TABLE ranking_history ADD COLUMN is_ad INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass
        self.conn.commit()

    def insert_ranking_batch(self, rows: list[dict[str, Any]]) -> None:
        if not rows: return
        cols = ["query", "rank", "collected_at", "title", "price", "seller_name", "product_id", "product_type", "product_url", "image_url", "is_ad", "product_code", "is_unauthorized"]
        self.conn.executemany(f"INSERT INTO ranking_history ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
                             [[r.get(c) for c in cols] for r in rows])
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
