from tracker.naver_api import NaverShoppingSearchClient
import json
from dotenv import load_dotenv
load_dotenv()

def debug_certified_search(catalog_id, cert_id):
    client = NaverShoppingSearchClient()
    print(f"Searching for catalog_id: {catalog_id}...")
    res = client.search(query=catalog_id, display=100)
    items = res.get("items", [])
    
    print(f"Total items found: {len(items)}\n")
    for i, item in enumerate(items[:30]):
        mid = str(item.get("mallProductId", ""))
        mall_name = str(item.get("mallName", ""))
        pid = str(item.get("productId", ""))
        price = item.get("lprice", "0")
        
        print(f"[{i:02d}] Mall: {mall_name:<25} | MallPID: {mid:<15} | PID: {pid:<15} | Price: {price}")
        if mid == cert_id:
            print(f"     >>> FOUND EXACT MATCH! index: {i} <<<")

if __name__ == "__main__":
    # 媛ㅻ윮??踰꾩쫰3 ?ㅻ쾭 (?곹뭹紐낆쑝濡?寃?됲븯??移댄깉濡쒓렇 留ㅼ묶 ?뺤씤)
    debug_certified_search("媛ㅻ윮??踰꾩쫰3 ?ㅻ쾭", None) # 移댄깉濡쒓렇 ID [숫자_ID] ?뺤씤??

