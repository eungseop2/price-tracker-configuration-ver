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
    
    # 분석 대상: 버즈3프로 화이트, 실버 (카탈로그 ID가 있는 대표 모델)
    test_targets = [t for t in app_config.targets if "버즈3프로" in t.name]
    
    for target in test_targets:
        print(f"\n{'='*80}")
        print(f"Target: {target.name}")
        print(f"Config - CatalogID: {target.match.product_id} | CertID: {target.certified_item_id}")
        print(f"{'-'*80}")
        
        # 1. 카탈로그 ID로 직접 검색 시도
        if target.match.product_id:
            print(f"1. Searching by CatalogID: {target.match.product_id}")
            payload = client.search(query=target.match.product_id, display=100)
            items = payload.get("items", [])
            print(f"   Found {len(items)} items")
            for i in items[:10]: # 상위 10개만 출력
                print(f"   - Mall: {i.get('mallName'):<15} | PID: {i.get('productId'):<12} | MallPID: {i.get('mallProductId'):<12} | Title: {i.get('title')[:30]}...")

        # 2. 상품명 쿼리로 검색 시도
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
