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
    
    # 遺꾩꽍 ??? 踰꾩쫰3?꾨줈 ?붿씠?? ?ㅻ쾭 (移댄깉濡쒓렇 ID媛 ?덈뒗 ???紐⑤뜽)
    test_targets = [t for t in app_config.targets if "踰꾩쫰3?꾨줈" in t.name]
    
    for target in test_targets:
        print(f"\n{'='*80}")
        print(f"Target: {target.name}")
        print(f"Config - CatalogID: {target.match.product_id} | CertID: {target.certified_item_id}")
        print(f"{'-'*80}")
        
        # 1. 移댄깉濡쒓렇 ID濡?吏곸젒 寃???쒕룄
        if target.match.product_id:
            print(f"1. Searching by CatalogID: {target.match.product_id}")
            payload = client.search(query=target.match.product_id, display=100)
            items = payload.get("items", [])
            print(f"   Found {len(items)} items")
            for i in items[:10]: # ?곸쐞 10媛쒕쭔 異쒕젰
                print(f"   - Mall: {i.get('mallName'):<15} | PID: {i.get('productId'):<12} | MallPID: {i.get('mallProductId'):<12} | Title: {i.get('title')[:30]}...")

        # 2. ?곹뭹紐?荑쇰━濡?寃???쒕룄
        print(f"\n2. Searching by Query: {target.query}")
        payload = client.search(query=target.query, display=100)
        items = payload.get("items", [])
        print(f"   Found {len(items)} items")
        
        matches = [i for i in items if str(i.get("productId")) == str(target.match.product_id)]
        print(f"   Items matching CatalogID ({target.match.product_id}): {len(matches)}")
        for i in matches:
            print(f"   - Mall: {i.get('mallName'):<15} | PID: {i.get('productId'):<12} | MallPID: {i.get('mallProductId'):<12} | Title: {i.get('title')[:30]}...")
            
        print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())

