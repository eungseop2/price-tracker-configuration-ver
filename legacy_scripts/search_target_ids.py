import asyncio
import os
import logging
import json
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    # 媛ㅻ윮??踰꾩쫰4?꾨줈 釉붾옓???몄쬆??ID?쇨퀬 吏紐⑸맂 媛?
    cert_ids = ["[숫자_ID]", "[숫자_ID]", "[숫자_ID]", "[숫자_ID]"]
    
    for c_id in cert_ids:
        print(f"\nSearching for ID directly: {c_id}")
        payload = client.search(query=c_id, display=10)
        items = payload.get("items", [])
        print(f"Found {len(items)} items")
        for i in items:
            print(f" - Title: {i.get('title').replace('<b>','').replace('</b>','')} | PID: {i.get('productId')} | MallPID: {i.get('mallProductId')} | Mall: {i.get('mallName')}")

if __name__ == "__main__":
    asyncio.run(main())

