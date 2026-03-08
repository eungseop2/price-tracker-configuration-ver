import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.config import load_config
from tracker.browser_scraper import collect_lowest_offer_via_browser

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    config_path = "./targets.yaml"
    app_config = load_config(config_path)
    
    # 테스트 대상: 갤럭시 버즈3프로 실버 (URL 모드)
    target = next(t for t in app_config.targets if t.name == "갤럭시 버즈3프로 실버")
    
    print(f"\n[Browser Scrape Test] Target: {target.name}")
    print(f"URL: {target.url}")
    print(f"{'='*60}")
    
    try:
        # 실제 브라우저를 띄워 수집 시도 (artifacts/test_scrape 폴더에 결과 저장)
        result = await collect_lowest_offer_via_browser(target, artifacts_dir="./artifacts/test_scrape")
        
        if result.get("success"):
            print(f"Status: SUCCESS")
            print(f"Title: {result.get('title')}")
            print(f"Lowest Price: {result.get('price'):,}원 ({result.get('seller_name')})")
            
            if "certified_price" in result:
                print(f"Certified Price: {result.get('certified_price'):,}원")
                print(f"Rank: {result.get('rank')}/{result.get('total')}")
            else:
                print("Certified data NOT found in this page.")
        else:
            print(f"Status: FAILED")
            print(f"Error: {result.get('error_message')}")
            
    except Exception as e:
        print(f"Status: ERROR")
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
