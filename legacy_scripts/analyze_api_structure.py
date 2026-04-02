import asyncio
import os
import logging
import json
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    # 갤럭시 핏3 (카탈로그가 잘 잡히는 제품 예시)
    query = "갤럭시 핏3"
    
    print(f"Searching for: {query}")
    payload = client.search(query=query, display=10)
    items = payload.get("items", [])
    
    for idx, i in enumerate(items):
        p_type = i.get("productType")
        p_id = i.get("productId")
        m_name = i.get("mallName")
        lprice = i.get("lprice")
        title = i.get("title").replace("<b>", "").replace("</b>", "")
        
        print(f"\n[{idx+1}] {title}")
        print(f"    - ProductType: {p_type} ({'Catalog' if str(p_type) in ['2', '3'] else 'Individual'})")
        print(f"    - ProductID (CatalogID): {p_id}")
        print(f"    - MallName: {m_name if m_name else 'N/A (Multi-vendor)'}")
        print(f"    - Lowest Price: {lprice}")
        
        # 카탈로그일 경우 내부 리스트 필드가 있는지 확인
        # (실제로는 API v1 응답에 그런 필드가 없음)
        internal_fields = [k for k in i.keys() if 'list' in k.lower() or 'offer' in k.lower()]
        if internal_fields:
            print(f"    - Found internal list fields: {internal_fields}")
        else:
            print(f"    - No internal seller list found in this search item.")

if __name__ == "__main__":
    asyncio.run(main())
