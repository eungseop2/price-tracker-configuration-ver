import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.config import load_config
from tracker.naver_api import NaverShoppingSearchClient, collect_lowest_offer_via_api

async def main():
    logging.basicConfig(level=logging.ERROR)
    load_dotenv()
    
    cfg = load_config("targets.yaml")
    client = NaverShoppingSearchClient()
    
    results = []
    for t in cfg.targets:
        if t.mode == "api_query":
            res = collect_lowest_offer_via_api(client, cfg, t)
            results.append({
                "name": t.name,
                "status": res.get("status"),
                "price": res.get("price"),
                "product_id": t.match.product_id
            })
            
    with open("summary_status.txt", "w", encoding="utf-8") as f:
        f.write("?꾩껜 ?곹뭹 API 理쒖?媛 ?섏쭛 ?꾪솴\n")
        f.write("="*50 + "\n")
        for r in results:
            price_str = f"{r['price']:,}" if r['price'] else "-"
            f.write(f"[{r['status']}] {r['name']:<25} | {price_str:>10}??| ID: {r['product_id']}\n")

if __name__ == "__main__":
    asyncio.run(main())

