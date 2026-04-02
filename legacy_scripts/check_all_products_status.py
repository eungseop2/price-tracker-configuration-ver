import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.config import load_config
from tracker.naver_api import NaverShoppingSearchClient, collect_lowest_offer_via_api

async def main():
    logging.basicConfig(level=logging.ERROR)
    load_dotenv()
    
    config_path = "./targets.yaml"
    app_config = load_config(config_path)
    client = NaverShoppingSearchClient()
    
    print(f"\n{'='*90}")
    print(f"{'Target Name':<30} | {'Mode':<10} | {'Status':<10} | {'Price':<10} | {'PID'}")
    print(f"{'-'*90}")
    
    for target in app_config.targets:
        if target.mode != "api_query":
            print(f"{target.name:<30} | {target.mode:<10} | SKIP       | -")
            continue
            
        try:
            res = collect_lowest_offer_via_api(client, app_config, target)
            status = res.get("status", "Unknown")
            price = f"{res.get('price', 0):,}" if res.get("price") else "-"
            p_id = res.get("product_id", "-")
            print(f"{target.name:<30} | {target.mode:<10} | {status:<10} | {price:<10} | {p_id}")
        except Exception as e:
            print(f"{target.name:<30} | {target.mode:<10} | ERROR      | {str(e)[:20]}")

if __name__ == "__main__":
    asyncio.run(main())
