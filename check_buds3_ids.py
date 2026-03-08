import asyncio
import os
import logging
import json
from dotenv import load_dotenv
from tracker.config import load_config
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    # 갤럭시 버즈3프로 화이트 (Catalog: 53508451504, Expected CertID: 11554945823)
    target_query = "갤럭시 버즈3프로 화이트"
    catalog_id = "53508451504"
    
    print(f"Searching for: {target_query}")
    payload = client.search(query=target_query, display=100)
    items = payload.get("items", [])
    
    print(f"\nItems in catalog {catalog_id}:")
    for i in items:
        p_id = str(i.get("productId"))
        if p_id == catalog_id:
            m_id = i.get("mallProductId")
            m_name = i.get("mallName")
            title = i.get("title").replace("<b>", "").replace("</b>", "")
            print(f" - Mall: {m_name:<15} | MallPID: {m_id:<15} | Title: {title[:30]}...")

if __name__ == "__main__":
    asyncio.run(main())
