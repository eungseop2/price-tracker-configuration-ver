
import os
import json
from src.tracker.gsheet_store import GoogleSheetStore
from src.tracker.config import AppConfig

def debug_data():
    sa_key = os.getenv("GCP_SA_KEY") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
    gsheet_id = "1nCUnrK8vO9O0qC2u452mR4rM25Fq6m-R" # 실제 ID로 확인 필요
    
    # 설정 로드 (ID 확인용)
    with open("targets.yaml", "r", encoding="utf-8") as f:
        import yaml
        cfg_raw = yaml.safe_load(f)
        gsheet_id = cfg_raw.get("gsheet_id") or "1L6Z8E3B6-C5I4W45-R" # 임시
    
    if not sa_key:
        print("SA KEY MISSING")
        return

    # 실제 gsheet_id는 환경변수나 targets.yaml에서 가져와야 함
    # 여기서는 store를 초기화해서 실제로 데이터가 몇 건이나 있는지 출력해본다.
    try:
        store = GoogleSheetStore(os.getenv("GSHEET_ID", "1Hnd06z_3pM6U-Gsc7-pS-i5mHj5vX-jG6p-W5I-R"), sa_key)
        ws = store._get_worksheet("ranking_history")
        records = store._get_all_records_safe(ws)
        print(f"TOTAL RECORDS IN ranking_history: {len(records)}")
        if records:
            print("LATEST 3 RECORDS:")
            for r in records[-3:]:
                print(f"  - Query: {r.get('query')}, Seller: {r.get('seller_name')}, Category: {r.get('category')}")
        
        # 리포트 데이터 생성 시뮬레이션
        # mall_targets가 없으면 빈 리포트가 나올 수 있음.
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    debug_data()
