import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    # 媛ㅻ윮??踰꾩쫰3 寃???쒕룄
    queries = [
        "媛ㅻ윮??踰꾩쫰3 ?ㅻ쾭",
        "媛ㅻ윮??踰꾩쫰3 ?붿씠??,
        "媛ㅻ윮??踰꾩쫰3?꾨줈 ?ㅻ쾭",
        "媛ㅻ윮??踰꾩쫰3?꾨줈 ?붿씠??
    ]
    
    print(f"\n{'='*100}")
    print(f"{'Query':<25} | {'PID':<12} | {'Mall':<15} | {'Title'}")
    print(f"{'-'*100}")
    
    for q in queries:
        payload = client.search(query=q, display=20) # 醫 ??留롮씠 寃??
        items = payload.get("items", [])
        for i in items:
            p_id = i.get("productId")
            p_type = i.get("productType")
            m_name = i.get("mallName")
            title = i.get("title").replace("<b>", "").replace("</b>", "")
            
            # 移댄깉濡쒓렇 ?뺥깭(2, 3)瑜??곗꽑?곸쑝濡?李얠쓬
            if str(p_type) in ['2', '3']:
                print(f"{q:<25} | {p_id:<12} | [CATALOG]      | {title}")

if __name__ == "__main__":
    asyncio.run(main())

