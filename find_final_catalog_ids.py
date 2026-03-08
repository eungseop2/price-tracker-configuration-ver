import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.ERROR)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    queries = [
        "갤럭시 버즈3 실버",
        "갤럭시 버즈3 화이트",
        "갤럭시 버즈3프로 실버",
        "갤럭시 버즈3프로 화이트"
    ]
    
    print(f"\n{'Target':<25} | {'PID':<12} | {'Title'}")
    print(f"{'-'*100}")
    
    for q in queries:
        payload = client.search(query=q, display=20)
        items = payload.get("items", [])
        catalog_found = False
        for i in items:
            p_type = i.get("productType")
            if str(p_type) in ['2', '3']:
                p_id = i.get("productId")
                title = i.get("title").replace("<b>", "").replace("</b>", "")
                print(f"{q:<25} | {p_id:<12} | {title}")
                catalog_found = True
                break
        if not catalog_found:
             print(f"{q:<25} | [CATALOG NOT FOUND]")

if __name__ == "__main__":
    asyncio.run(main())
