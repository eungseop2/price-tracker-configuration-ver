import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.config import load_config
from tracker.naver_api import NaverShoppingSearchClient, collect_certified_rank

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    config_path = "./targets.yaml"
    app_config = load_config(config_path)
    client = NaverShoppingSearchClient()
    
    # 핏3 테스트 (정상 작동 예상)
    target = next(t for t in app_config.targets if "핏3" in t.name)
    
    print(f"\nTesting: {target.name}")
    print(f"Catalog ID: {target.match.product_id}")
    payload = client.search(query=target.query, display=100)
    items = payload.get("items", [])
    
    found = False
    for i in items:
        if str(i.get("productId")) == str(target.match.product_id):
            print(f"Found Catalog in Search! PID: {i.get('productId')} | MallPID: {i.get('mallProductId')} | Mall: {i.get('mallName')}")
            found = True
            break
            
    if not found:
        print("Catalog ID NOT found in top 100 search results for Fit 3.")
        # Show what IDs ARE there
        pids = [str(i.get("productId")) for i in items[:5]]
        print(f"Top 5 PIDs found: {pids}")

if __name__ == "__main__":
    asyncio.run(main())
