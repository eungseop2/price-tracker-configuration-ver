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
    # 갤럭시 버즈4프로 블랙의 인증점 ID라고 지목된 값
    cert_ids = ["13104063712", "13104069397", "13104046827", "13104060742"]
    
    for c_id in cert_ids:
        print(f"\nSearching for ID directly: {c_id}")
        payload = client.search(query=c_id, display=10)
        items = payload.get("items", [])
        print(f"Found {len(items)} items")
        for i in items:
            print(f" - Title: {i.get('title').replace('<b>','').replace('</b>','')} | PID: {i.get('productId')} | MallPID: {i.get('mallProductId')} | Mall: {i.get('mallName')}")

if __name__ == "__main__":
    asyncio.run(main())
