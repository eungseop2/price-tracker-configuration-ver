import json
import logging
import sqlite3
import os
from datetime import datetime, timezone
from typing import Any, list, dict

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger("tracker.gsheet_sync")

# 시트별 헤더 정의
HEADERS = {
    "observations": [
        "id", "target_name", "source_mode", "collected_at", "success", "status", 
        "price", "prev_price", "price_delta", "price_delta_pct", "price_change_status",
        "title", "seller_name", "product_id", "product_url", "image_url", "search_rank"
    ],
    "mall_observations": [
        "id", "target_name", "query", "mall_name", "category", "collected_at", 
        "title", "price", "product_id", "product_type", "product_url", "image_url", "search_rank"
    ],
    "ranking_history": [
        "id", "query", "rank", "collected_at", "title", "price", "seller_name", 
        "product_id", "product_type", "product_url", "image_url", "is_ad"
    ]
}

def _get_gsheet_client(service_account_info: dict) -> gspread.Client:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return gspread.authorize(credentials)

def sync_sqlite_to_gsheet(db_path: str, spreadsheet_id: str, service_account_json: str) -> bool:
    """SQLite DB의 내용을 구글 스프레드시트로 업로드합니다."""
    if not spreadsheet_id or not service_account_json:
        logger.error("Spreadsheet ID 또는 Service Account Key가 설정되지 않았습니다.")
        return False

    try:
        service_account_info = json.loads(service_account_json)
        gc = _get_gsheet_client(service_account_info)
        sh = gc.open_by_key(spreadsheet_id)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        for table_name, columns in HEADERS.items():
            try:
                logger.info(f"시트 동기화 중: {table_name}")
                
                # SQLite 데이터 가져오기 (최신순 500개 우선)
                query = f"SELECT {', '.join(columns)} FROM {table_name} ORDER BY id DESC LIMIT 1000"
                rows = conn.execute(query).fetchall()
                
                # 워크시트 선택 또는 생성
                try:
                    worksheet = sh.worksheet(table_name)
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = sh.add_worksheet(title=table_name, rows="100", cols=str(len(columns)))
                
                # 데이터 준비 (헤더 + 내용)
                data_to_write = [columns]
                for r in rows:
                    data_to_write.append([r[col] for col in columns])
                
                # 전체 시트 업데이트 (기존 내용 덮어쓰기)
                worksheet.clear()
                worksheet.update('A1', data_to_write)
                
                logger.info(f"  └ {table_name} 동기화 완료 ({len(rows)}개 행)")
                
            except Exception as e:
                logger.error(f"  └ {table_name} 동기화 실패: {e}")
                
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"구글 스프레드시트 동기화 실패: {e}")
        return False

def sync_gsheet_to_sqlite(spreadsheet_id: str, service_account_json: str, db_path: str) -> bool:
    """구글 스프레드시트의 내용을 로컬 SQLite DB로 내려받습니다 (복구용)."""
    # TODO: 필요한 경우 구현 (현재는 Read-only or Append-only 위주)
    logger.warning("sync-from-gsheet 기능은 아직 구현되지 않았습니다.")
    return False
