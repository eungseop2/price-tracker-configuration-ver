import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.config import load_config
from tracker.naver_api import NaverShoppingSearchClient, any_keyword_present
from tracker.util import clean_text, all_keywords_present

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    config_path = "./targets.yaml"
    app_config = load_config(config_path)
    client = NaverShoppingSearchClient()
    
    target_query = "媛ㅻ윮??踰꾩쫰3?꾨줈 ?ㅻ쾭"
    catalog_id = "[숫자_ID]"
    
    # ?대떦 ?寃?李얘린
    target = None
    for t in app_config.targets:
        if t.name == target_query:
            target = t
            break
            
    if not target:
        print(f"Error: Target '{target_query}' not found in config.")
        return
    
    print(f"Target: {target_query} | Expected CatalogID: {catalog_id}")
    
    all_items = []
    for start_idx in [1, 101, 201, 301]:
        payload = client.search(query=target_query, display=100, start=start_idx)
        items = payload.get("items", [])
        if not items: break
        all_items.extend(items)
        print(f" - Page {start_idx//100 + 1}: Found {len(items)} items")
    
    output_path = "silver_id_list_all_400.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Target: {target_query} | Expected CatalogID: {catalog_id}\n")
        f.write(f"Total Items Collected: {len(all_items)}\n\n")
        f.write(f"{'No':>3} | {'PID':<12} | {'Mid':<12} | {'Mall':<20} | {'Title'}\n")
        f.write("-" * 120 + "\n")
        for idx, i in enumerate(all_items):
            p_id = str(i.get("productId"))
            m_id = i.get("mallProductId")
            m_name = i.get("mallName")
            title = i.get("title").replace("<b>", "").replace("</b>", "")
            match_mark = "[CATALOG MATCH!]" if p_id == catalog_id else ""
            f.write(f"{idx+1:>3} | {p_id:<12} | {str(m_id):<12} | {m_name:<20} | {match_mark} {title}\n")
    
    print(f"Successfully saved {len(all_items)} raw items to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())

