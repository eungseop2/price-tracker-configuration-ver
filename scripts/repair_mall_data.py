
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import sys

# src 경로 추가
sys.path.append(os.getcwd())

from src.tracker.gsheet_store import GoogleSheetStore, HEADERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("repair")

def is_iso_date(val):
    try:
        if not val or not isinstance(val, str): return False
        return val.startswith("20") and "T" in val
    except: return False

def is_price(val):
    try:
        if not val: return False
        s_val = str(val).replace(",", "").strip()
        if not s_val: return False
        iv = int(float(s_val))
        return iv > 100
    except: return False

def repair_mall_observations():
    load_dotenv()
    spreadsheet_id = os.getenv("GSHEET_ID")
    service_account_json = os.getenv("GCP_SA_KEY") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
    
    if not spreadsheet_id or not service_account_json:
        logger.error("환경변수 누락")
        return
    
    store = GoogleSheetStore(spreadsheet_id, service_account_json)
    store._connect()
    
    try:
        ws = store._get_worksheet("mall_observations")
        all_values = ws.get_all_values()
        if len(all_values) < 2:
            logger.info("복구할 데이터 없음")
            return

        headers = all_values[0]
        expected_headers = HEADERS["mall_observations"]
        
        logger.info(f"현재 헤더: {headers}")
        logger.info(f"예상 헤더: {expected_headers}")

        repaired_rows = []
        fixed_count = 0
        
        for i, row in enumerate(all_values[1:], 1):
            # 현재 행의 데이터를 딕셔너리로 매핑 시도
            item = {}
            for j, h in enumerate(headers):
                if j < len(row):
                    item[h] = row[j]
            
            # 새로운 정렬된 로우 생성
            new_item = {h: "" for h in expected_headers}
            
            # 패턴 기반 복구
            remaining_vals = [v for v in row if v] # 빈값 제외하고 분석
            
            # 1. 날짜 찾기
            for val in list(remaining_vals):
                if is_iso_date(val):
                    new_item["collected_at"] = val
                    remaining_vals.remove(val)
                    break
            
            # 2. 가격 찾기
            for val in list(remaining_vals):
                if is_price(val):
                    new_item["price"] = val
                    remaining_vals.remove(val)
                    break
            
            # 3. URL 찾기
            for val in list(remaining_vals):
                if str(val).startswith("http"):
                    if "pstatic.net" in str(val):
                        new_item["image_url"] = val
                        remaining_vals.remove(val)
                    elif "shopping.naver.com" in str(val) or "smartstore" in str(val):
                        new_item["product_url"] = val
                        remaining_vals.remove(val)

            # 4. 나머지 필드들은 헤더 이름 대조로 최대한 복구
            for h in expected_headers:
                if not new_item[h] and h in item:
                    new_item[h] = item[h]

            # 최종 로우 생성
            new_row = [str(new_item.get(h, "")) for h in expected_headers]
            repaired_rows.append(new_row)
            fixed_count += 1

        if repaired_rows:
            # 먼저 헤더 강제 업데이트
            ws.update('A1', [expected_headers])
            
            # 데이터 일괄 업데이트 (성능을 위해 100개씩 끊어서 진행할 수도 있지만 일단 전체)
            # gspread의 update는 리스트의 리스트를 받음
            # range_name을 계산하여 A2부터 시작
            last_col = chr(64 + len(expected_headers))
            range_name = f"A2:{last_col}{len(repaired_rows) + 1}"
            ws.update(range_name, repaired_rows)
            logger.info(f"총 {fixed_count}개의 행 복구 완료")

    except Exception as e:
        logger.exception(f"복구 중 오류 발생: {e}")
    finally:
        store.close()

if __name__ == "__main__":
    repair_mall_observations()
