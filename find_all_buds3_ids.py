import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    # 갤럭시 버즈3 검색 시도
    queries = [
        "갤럭시 버즈3 실버",
        "갤럭시 버즈3 화이트",
        "갤럭시 버즈3프로 실버",
        "갤럭시 버즈3프로 화이트"
    ]
    
    print(f"\n{'='*100}")
    print(f"{'Query':<25} | {'PID':<12} | {'Mall':<15} | {'Title'}")
    print(f"{'-'*100}")
    
    for q in queries:
        payload = client.search(query=q, display=20) # 좀 더 많이 검색
        items = payload.get("items", [])
        for i in items:
            p_id = i.get("productId")
            p_type = i.get("productType")
            m_name = i.get("mallName")
            title = i.get("title").replace("<b>", "").replace("</b>", "")
            
            # 카탈로그 형태(2, 3)를 우선적으로 찾음
            if str(p_type) in ['2', '3']:
                print(f"{q:<25} | {p_id:<12} | [CATALOG]      | {title}")

if __name__ == "__main__":
    asyncio.run(main())
