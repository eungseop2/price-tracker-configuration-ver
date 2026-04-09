import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트를 패키지 경로에 추가
sys.path.append(str(Path(__file__).parent.parent))

from src.tracker.gsheet_store import GoogleSheetStore

def main():
    load_dotenv()
    
    gsheet_id = os.getenv("GSHEET_ID")
    gcp_key = os.getenv("GCP_SA_KEY")
    
    if not gsheet_id or not gcp_key:
        print("에러: GSHEET_ID 또는 GCP_SA_KEY 환경변수가 설정되지 않았습니다.")
        return

    print("--- 구글 시트 긴급 복구 및 데이터 최적화 시작 ---")
    store = GoogleSheetStore(gsheet_id, gcp_key)
    store._connect()
    
    sheets = ["mall_observations", "observations", "ranking_history"]
    total_cells = 0
    
    for name in sheets:
        try:
            print(f"\n[{name}] 처리 중...")
            ws = store._get_worksheet(name)
            
            # 1. 오래된 데이터 정리 (지능형 최적화 보관 주기 적용)
            days = 5 if name == "mall_observations" else 60
            print(f"  - {days}일 보관 최적화 실행 중...")
            store.cleanup_old_records(name, days=days)
            
            # 2. 빈 행 삭제 (Resize)
            print(f"  - 빈 행 정리 (Resize) 중...")
            store.resize_to_content(name)
            
            # 최종 상태 확인
            final_ws = store._sh.worksheet(name)
            rows = final_ws.row_count
            cols = final_ws.col_count
            cells = rows * cols
            total_cells += cells
            print(f"  - 완료: 현재 {rows}행 x {cols}열 (약 {cells:,} 셀 사용)")
            
        except Exception as e:
            print(f"[{name}] 오류 발생: {e}")

    print("\n" + "="*40)
    print(f"전체 시트 추정 셀 사용량: {total_cells:,} / 10,000,000")
    print(f"사용률: {(total_cells / 10000000 * 100):.2f}%")
    print("="*40)
    print("--- 모든 최적화 작업 완료 ---")

if __name__ == "__main__":
    main()
