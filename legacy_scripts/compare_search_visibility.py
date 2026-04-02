import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.config import load_config
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    config_path = "./targets.yaml"
    app_config = load_config(config_path)
    client = NaverShoppingSearchClient()
    
    test_products = [
        ("버즈3프로 화이트", "53508451504"),
        ("버즈3프로 실버", "53508451505"),
        ("버즈4프로 블랙", "59061283797"),
        ("워치8 40mm 실버", "55668557960"),
        ("핏3", "55900277515")
    ]
    
    print(f"\n{'='*60}")
    print(f"{'Product Name':<20} | {'Catalog ID':<12} | {'Found in API?'}")
    print(f"{'-'*60}")
    
    for name, c_id in test_products:
        # 1. Search by ID
        payload_id = client.search(query=c_id, display=1)
        items_id = payload_id.get("items", [])
        
        # 2. Search by Name and check if ID exists in top 100
        payload_name = client.search(query=name if "버즈" not in name else "갤럭시 " + name, display=100)
        items_name = payload_name.get("items", [])
        in_top_100 = any(str(i.get("productId")) == str(c_id) for i in items_name)
        
        status_id = "YES" if items_id else "NO"
        status_top = "YES" if in_top_100 else "NO"
        
        print(f"{name:<20} | {c_id:<12} | ID Search: {status_id:<5} / Top 100: {status_top}")

if __name__ == "__main__":
    asyncio.run(main())
