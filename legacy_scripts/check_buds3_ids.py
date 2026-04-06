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
    # 媛ㅻ윮??踰꾩쫰3?꾨줈 ?붿씠??(Catalog: [숫자_ID], Expected CertID: [숫자_ID])
    target_query = "媛ㅻ윮??踰꾩쫰3?꾨줈 ?붿씠??
    catalog_id = "[숫자_ID]"
    
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

