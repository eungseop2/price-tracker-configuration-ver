import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.ERROR)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    queries = ["갤럭시 버즈3", "갤럭시 버즈3프로"]
    
    print(f"\n{'Query':<20} | {'PID':<12} | {'Type':<5} | {'Title'}")
    print(f"{'-'*100}")
    
    for q in queries:
        payload = client.search(query=q, display=20)
        items = payload.get("items", [])
        for i in items:
            p_id = i.get("productId")
            p_type = i.get("productType")
            title = i.get("title").replace("<b>", "").replace("</b>", "")
            
            # 카탈로그(2, 3) 위주로 출력
            if str(p_type) in ['2', '3']:
                print(f"{q:<20} | {p_id:<12} | {p_type:<5} | {title}")

if __name__ == "__main__":
    asyncio.run(main())
