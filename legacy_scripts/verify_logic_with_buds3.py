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
    
    # ?대? ?몄쬆?먯씠 ???≫엳??寃껋쑝濡??뚮젮吏?踰꾩쫰3?꾨줈 釉붾옓/?붿씠???뚯뒪??
    test_targets = [t for t in app_config.targets if "踰꾩쫰3?꾨줈" in t.name]
    
    print(f"\n{'='*60}")
    print(f"{'Target Name':<30} | {'Status':<10} | {'Price':<10}")
    print(f"{'-'*60}")
    
    for target in test_targets:
        try:
            rank_data = collect_certified_rank(client, app_config, target)
            if rank_data:
                print(f"{target.name:<30} | {'OK':<10} | {rank_data['certified_price']:<10,}")
                print(f"  - Rank: {rank_data['rank']}/{rank_data['total']}")
                print(f"  - Low: {rank_data['certified_lowest_price']:,}")
                print(f"  - Between: {rank_data['certified_between_non_auth_count']}")
            else:
                print(f"{target.name:<30} | {'FAILED':<10} | {'-':<10}")
        except Exception as e:
            print(f"{target.name:<30} | {'ERROR':<10} | {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())

