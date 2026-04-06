import yaml
import json
import os
import sys
from tracker.naver_api import NaverShoppingSearchClient, collect_certified_rank

def main():
    client = NaverShoppingSearchClient()
    # 媛ㅻ윮??踰꾩쫰3?꾨줈 ?ㅻ쾭 (Catalog: [숫자_ID])
    catalog_id = "[숫자_ID]"
    certified_id = "[숫자_ID]"
    
    class AppConfig:
        def __init__(self): self.exclude = ""
            
    class TargetMatch:
        def __init__(self): self.product_id = catalog_id
            
    class Target:
        def __init__(self):
            self.name = "Test"
            self.query = "媛ㅻ윮??踰꾩쫰3?꾨줈 ?ㅻ쾭"
            self.mode = "api"
            self.match = TargetMatch()
            self.certified_item_id = certified_id
            
    print(f"\nCalling collect_certified_rank for {catalog_id} / {certified_id}...")
    result = collect_certified_rank(client, AppConfig(), Target())
    print(f"Result: {result}")

if __name__ == "__main__":
    main()

