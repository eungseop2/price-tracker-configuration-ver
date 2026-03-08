import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    # 검증할 ID 리소드
    ids = [
        ("53508451504", "User says: Buds3 Pro White?"),
        ("53508451505", "User says: Buds3 Silver? (Existing says Pro Silver)"),
        ("53507707536", "User says: Buds3 White?"),
        ("53508451507", "Maybe Buds3 Pro Silver??")
    ]
    
    print(f"\n{'='*90}")
    print(f"{'Catalog ID':<15} | {'Note':<35} | {'API Title'}")
    print(f"{'-'*90}")
    
    for c_id, note in ids:
        payload = client.search(query=c_id, display=1)
        items = payload.get("items", [])
        if items:
            title = items[0].get("title").replace("<b>", "").replace("</b>", "")
            print(f"{c_id:<15} | {note:<35} | {title}")
        else:
            print(f"{c_id:<15} | {note:<35} | NOT FOUND")

if __name__ == "__main__":
    asyncio.run(main())
