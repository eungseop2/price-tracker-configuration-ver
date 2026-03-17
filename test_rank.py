import asyncio
from src.tracker.config import load_config
from src.tracker.naver_api import NaverShoppingSearchClient, collect_lowest_offer_via_api

def main():
    config = load_config("targets.yaml")
    target = None
    for t in config.targets:
        if "버즈3 화이트" in t.name:
            target = t
            break
            
    if not target:
        print("Target not found")
        return
        
    client = NaverShoppingSearchClient()
    res = collect_lowest_offer_via_api(client, config, target)
    print("API Result:")
    for k, v in res.items():
        if k != "raw_payload":
            print(f"{k}: {v}")

if __name__ == "__main__":
    main()
