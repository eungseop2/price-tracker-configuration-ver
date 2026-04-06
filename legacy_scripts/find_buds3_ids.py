import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    queries = ["媛ㅻ윮??踰꾩쫰3 ?ㅻ쾭", "媛ㅻ윮??踰꾩쫰3 ?붿씠??]
    
    print(f"\n{'='*80}")
    print(f"{'Query':<25} | {'PID':<12} | {'Mall':<15} | {'Title'}")
    print(f"{'-'*80}")
    
    for q in queries:
        payload = client.search(query=q, display=10)
        items = payload.get("items", [])
        for i in items:
            p_id = i.get("productId")
            p_type = i.get("productType")
            m_name = i.get("mallName")
            title = i.get("title").replace("<b>", "").replace("</b>", "")
            
            # 移댄깉濡쒓렇 ?뺥깭(2, 3)瑜??곗꽑?곸쑝濡?李얠쓬
            is_catalog = "[CATALOG]" if str(p_type) in ['2', '3'] else ""
            print(f"{q:<25} | {p_id:<12} | {m_name if m_name else 'N/A':<15} | {is_catalog} {title}")

if __name__ == "__main__":
    asyncio.run(main())

