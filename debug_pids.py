import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.ERROR)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    # 검증할 PID 리스트
    test_pids = [
        "53508451504", # 기존 Buds3 Pro White
        "53508451505", # 기존 Buds3 Pro Silver / 사용자 Buds3 Silver
        "53507707536", # 사용자 Buds3 White
        "53508451507"  # 혹시 모를 다른 후보
    ]
    
    print(f"\n{'PID':<12} | {'Title'}")
    print(f"{'-'*80}")
    
    for pid in test_pids:
        payload = client.search(query=pid, display=1)
        items = payload.get("items", [])
        if items:
            title = items[0].get("title").replace("<b>", "").replace("</b>", "")
            print(f"{pid:<12} | {title}")
        else:
            print(f"{pid:<12} | [NOT FOUND]")

if __name__ == "__main__":
    asyncio.run(main())
