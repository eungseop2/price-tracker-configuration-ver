import asyncio
import os
import logging
import json
from dotenv import load_dotenv
from tracker.config import load_config
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    queries = [
        ('갤럭시 버즈4프로 블랙', '59061283797'),
        ('갤럭시 버즈4 블랙', '59061250873')
    ]
    
    for q_str, expected_id in queries:
        print(f"\nSearching for: {q_str} (Expected Catalog ID: {expected_id})")
        payload = client.search(query=q_str, display=100)
        items = payload.get("items", [])
        
        found = False
        for i in items:
            p_id = str(i.get("productId"))
            m_name = i.get("mallName")
            m_p_id = i.get("mallProductId")
            title = i.get("title").replace("<b>", "").replace("</b>", "")
            
            if p_id == expected_id:
                print(f"[FOUND MATCH!] {title} | PID: {p_id} | Mall: {m_name} | MallPID: {m_p_id}")
                found = True
            elif expected_id in title:
                print(f"[Potential?] {title} | PID: {p_id} | Mall: {m_name} | MallPID: {m_p_id}")

        if not found:
            print("No catalog match found in top 100 items.")
            # Let's see some non-matches
            print("First 5 items returned:")
            for i in items[:5]:
                print(f" - {i.get('title')} | PID: {i.get('productId')}")

if __name__ == "__main__":
    asyncio.run(main())
