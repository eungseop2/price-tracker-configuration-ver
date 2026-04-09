import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트를 패키지 경로에 추가
sys.path.append(str(Path(__file__).parent.parent))

from src.tracker.gsheet_store import GoogleSheetStore, HEADERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_sheets")

def main():
    load_dotenv()
    
    gsheet_id = os.getenv("GSHEET_ID")
    service_account_json = os.getenv("GCP_SA_KEY") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
    
    if not gsheet_id or not service_account_json:
        logger.error("GSHEET_ID 또는 GCP_SA_KEY 환경변수가 설정되지 않았습니다.")
        return

    print("--- 구글 시트 데이터 전체 초기화 시작 ---")
    store = GoogleSheetStore(gsheet_id, service_account_json)
    
    try:
        store._connect()
    except Exception as e:
        logger.error(f"연결 실패: {e}")
        return

    for name, headers in HEADERS.items():
        try:
            print(f"[{name}] 초기화 중...")
            ws = store._sh.worksheet(name)
            
            # 모든 데이터 삭제 (헤더 포함 전체)
            ws.clear()
            
            # 헤더 다시 쓰기
            ws.update('A1', [headers])
            
            # 시트 크기를 데이터에 맞춰 축소 (헤더 1행 + 여유 99행 = 100행)
            ws.resize(rows=100)
            
            print(f"  - 완료: {ws.row_count} x {ws.col_count} 행")
            
        except Exception as e:
            print(f"[{name}] 오류 발생: {e}")

    print("--- 모든 시트 초기화 완료 ---")

if __name__ == "__main__":
    main()
