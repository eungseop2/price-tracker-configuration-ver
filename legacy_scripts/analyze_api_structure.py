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
    # 媛ㅻ윮???? (移댄깉濡쒓렇媛 ???≫엳???쒗뭹 ?덉떆)
    query = "媛ㅻ윮????"
    
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
        
        # 移댄깉濡쒓렇??寃쎌슦 ?대? 由ъ뒪???꾨뱶媛 ?덈뒗吏 ?뺤씤
        # (?ㅼ젣濡쒕뒗 API v1 ?묐떟??洹몃윴 ?꾨뱶媛 ?놁쓬)
        internal_fields = [k for k in i.keys() if 'list' in k.lower() or 'offer' in k.lower()]
        if internal_fields:
            print(f"    - Found internal list fields: {internal_fields}")
        else:
            print(f"    - No internal seller list found in this search item.")

if __name__ == "__main__":
    asyncio.run(main())

