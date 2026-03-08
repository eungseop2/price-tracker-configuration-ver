import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    queries = ["갤럭시 버즈3 실버", "갤럭시 버즈3 화이트"]
    
    print(f"\n{'='*80}")
    print(f"{'Query':<25} | {'PID':<12} | {'Mall':<15} | {'Title'}")
    print(f"{'-'*80}")
    
    for q in queries:
        payload = client.search(query=q, display=10)
        items = payload.get("items", [])
        for i in items:
            p_id = i.get("productId")
            p_type = i.get("productType")
            m_name = i.get("mallName")
            title = i.get("title").replace("<b>", "").replace("</b>", "")
            
            # 카탈로그 형태(2, 3)를 우선적으로 찾음
            is_catalog = "[CATALOG]" if str(p_type) in ['2', '3'] else ""
            print(f"{q:<25} | {p_id:<12} | {m_name if m_name else 'N/A':<15} | {is_catalog} {title}")

if __name__ == "__main__":
    asyncio.run(main())
