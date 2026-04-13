import os
import logging
import json
from dotenv import load_dotenv
from .config import load_config
from .gsheet_store import GoogleSheetStore
from .util import any_keyword_present, normalize_for_match

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tracker.cleanup")

# 제외 키워드 리스트 (사용자 피드백 반영: 미개봉, 강화유리, 스트랩, 케이스, 구형 모델 제외에서 제거)
KEYWORDS_TO_EXCLUDE = [
    "패키지", "시계줄", "밴드", "충전독", "거치대", "파우치", 
    "스탠드", "스킨", "커버", "필름", "보호막", "어댑터", "젠더", "이어팁", "청소키트", 
    "공구", "헤드폰", "이어캡", "버클", "브레이슬릿", "이용권", "보이스캐디", "증정", 
    "사은품", "학생전용", "쿠폰", "갤럭시S", "S25", "S26", "퀀텀", "버디", "와이드", 
    "갤럭시탭", "탭A", "갤럭시북", "아이폰", "에어팟", "갤럭시핏", "핏3", "핏e", 
    "그랑데AI", "중고", "리퍼", "가개통"
]

def cleanup():
    load_dotenv()
    
    # 설정 로드
    yaml_path = "targets.yaml"
    app_config = load_config(yaml_path)
    
    # 로컬 실행을 위해 발견된 값 설정
    gsheet_id = os.getenv("GSHEET_ID") or app_config.gsheet_id or "1eDCtiuTHLfbw2uSZ-hW7f-hYkRYJMuM33W9UcFe8Osw"
    
    credential_json = os.getenv("GCP_SA_KEY") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
    if not credential_json and os.path.exists("temp_gcp_key.json"):
        with open("temp_gcp_key.json", "rb") as f:
            raw_data = f.read()
            for encoding in ["utf-8-sig", "latin-1", "cp1252"]:
                try:
                    credential_json = raw_data.decode(encoding)
                    json.loads(credential_json)
                    break
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue

    if not gsheet_id:
        logger.error("GSHEET_ID가 설정되어 있지 않습니다.")
        return
        
    if not credential_json:
        logger.error("구글 서비스 계정 키(GCP_SA_KEY)가 설정되어 있지 않습니다.")
        return
        
    logger.info(f"Using GSHEET_ID: {gsheet_id[:5]}...")
    store = GoogleSheetStore(gsheet_id, credential_json)
    
    sheets_to_clean = ["mall_observations", "observations", "ranking_history"]
    
    for sheet_name in sheets_to_clean:
        logger.info(f"시트 '{sheet_name}' 정리 시작...")
        try:
            ws = store._get_worksheet(sheet_name)
            all_values = ws.get_all_values()
            if len(all_values) <= 1:
                logger.info(f"시트 '{sheet_name}'에 데이터가 없습니다.")
                continue
                
            headers = all_values[0]
            title_idx = headers.index("title") if "title" in headers else -1
            
            if title_idx == -1:
                logger.warning(f"시트 '{sheet_name}'에 'title' 컬럼이 없어 건너뜜")
                continue
                
            new_rows = [headers]
            removed_count = 0
            
            for row in all_values[1:]:
                if title_idx >= len(row): continue
                title = row[title_idx]
                
                # 제외 키워드 체크
                if any_keyword_present(title, KEYWORDS_TO_EXCLUDE):
                    removed_count += 1
                    continue
                
                new_rows.append(row)
            
            if removed_count > 0:
                logger.info(f"시트 '{sheet_name}': {removed_count}건의 불필요 데이터 정리 중...")
                ws.clear()
                chunk_size = 1000
                for i in range(0, len(new_rows), chunk_size):
                    chunk = new_rows[i:i + chunk_size]
                    ws.update(f'A{i+1}', chunk)
                logger.info(f"시트 '{sheet_name}' 정리 완료 ({removed_count}건 삭제됨)")
            else:
                logger.info(f"시트 '{sheet_name}'에 삭제할 데이터가 없습니다.")
                
        except Exception as e:
            logger.error(f"시트 '{sheet_name}' 정리 중 오류: {e}")

if __name__ == "__main__":
    cleanup()
