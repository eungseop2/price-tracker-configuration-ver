import asyncio
import os
import logging
from dotenv import load_dotenv
from tracker.naver_api import NaverShoppingSearchClient

async def main():
    logging.basicConfig(level=logging.ERROR)
    load_dotenv()
    
    client = NaverShoppingSearchClient()
    # 寃利앺븷 PID 由ъ뒪??
    test_pids = [
        "[숫자_ID]", # 湲곗〈 Buds3 Pro White
        "[숫자_ID]", # 湲곗〈 Buds3 Pro Silver / ?ъ슜??Buds3 Silver
        "[숫자_ID]", # ?ъ슜??Buds3 White
        "[숫자_ID]"  # ?뱀떆 紐⑤? ?ㅻⅨ ?꾨낫
    ]
    
    print(f"\n{'PID':<12} | {'Title'}")
    print(f"{'-'*80}")
    
    for pid in test_pids:
        payload = client.search(query=pid, display=1)
        items = payload.get("items", [])
        if items:
            title = items[0].get("title").replace("<b>", "").replace("</b>", "")
            print(f"{pid:<12} | {title}")
        else:
            print(f"{pid:<12} | [NOT FOUND]")

if __name__ == "__main__":
    asyncio.run(main())

