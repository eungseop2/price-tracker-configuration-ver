import json
import os
from dotenv import load_dotenv
load_dotenv()
from tracker.naver_api import NaverShoppingSearchClient
from tracker.config import AppConfig, TargetConfig, MatchConfig

def find_seller_id(query, product_id):
    client = NaverShoppingSearchClient()
    app_config = AppConfig()
    
    print(f"Searching for {query} (ID: {product_id})...")
    res = client.search(query=query, display=100) # Use query instead of ID to broader results
    items = res.get("items", [])
    
    print(f"{'Seller Name':<20} | {'Mall Product ID':<15} | {'Price':<10} | {'Catalog ID':<15}")
    print("-" * 70)
    for item in items:
        mall_name = item.get("mallName", "N/A")
        mall_pid = item.get("mallProductId", "N/A")
        price = item.get("lprice", "0")
        cat_id = item.get("productId", "N/A")
        
        # Only print if Mall Product ID exists (potential certified seller)
        if mall_pid:
            print(f"{mall_name:<20} | {mall_pid:<15} | {price:<10} | {cat_id:<15}")

if __name__ == "__main__":
    # 媛ㅻ윮??踰꾩쫰3 ?ㅻ쾭 Catalog: [숫자_ID]
    print("Listing all sellers for catalog [숫자_ID] (Galaxy Buds 3 Silver)...")
    find_seller_id("媛ㅻ윮??踰꾩쫰3 ?ㅻ쾭", "[숫자_ID]")
    
    # Also check Buds 3 White Catalog: [숫자_ID]
    print("\nListing all sellers for catalog [숫자_ID] (Galaxy Buds 3 White)...")
    find_seller_id("媛ㅻ윮??踰꾩쫰3 ?붿씠??, "[숫자_ID]")

