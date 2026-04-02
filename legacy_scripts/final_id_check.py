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
    
    print("\n--- Galaxy Buds 3 / 3 Pro ID Check ---")
    for q in queries:
        print(f"\nQuery: {q}")
        payload = client.search(query=q, display=10)
        items = payload.get("items", [])
        
        found = False
        for i in items:
            # productType 2 or 3 is a Catalog
            if str(i.get("productType")) in ["2", "3"]:
                p_id = i.get("productId")
                title = i.get("title").replace("<b>", "").replace("</b>", "")
                print(f"  [CATALOG] ID: {p_id} | Title: {title}")
                found = True
        if not found:
            print("  [No catalog found in top 10]")

if __name__ == "__main__":
    asyncio.run(main())
