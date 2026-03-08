import asyncio
import os
import logging
import json
from dotenv import load_dotenv
from tracker.config import load_config
from tracker.naver_api import NaverShoppingSearchClient, collect_certified_rank

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    config_path = "./targets.yaml"
    app_config = load_config(config_path)
    client = NaverShoppingSearchClient()
    
    target_name = "갤럭시 버즈4프로 블랙"
    target = next(t for t in app_config.targets if t.name == target_name)
    
    catalog_id = target.match.product_id
    query = target.query
    
    print(f"Testing target: {target_name}")
    print(f"Catalog ID: {catalog_id}")
    print(f"Query: {query}")
    
    # 1. Test search with catalog_id as query
    print("\n--- Try searching with catalog_id ---")
    payload = client.search(query=catalog_id, display=10)
    items = payload.get("items", [])
    print(f"Found {len(items)} items")
    for i in items[:2]:
        print(f" - {i['title']} | ProductID: {i['productId']} | MallProductID: {i.get('mallProductId')}")
        
    # 2. Test search with query string
    print("\n--- Try searching with query string ---")
    payload = client.search(query=query, display=10)
    items = payload.get("items", [])
    print(f"Found {len(items)} items")
    for i in items[:2]:
         print(f" - {i['title']} | ProductID: {i['productId']} | MallProductID: {i.get('mallProductId')}")

    # 3. Run full collect_certified_rank
    print("\n--- Running collect_certified_rank ---")
    res = collect_certified_rank(client, app_config, target)
    print(f"Result: {res}")

if __name__ == "__main__":
    asyncio.run(main())
