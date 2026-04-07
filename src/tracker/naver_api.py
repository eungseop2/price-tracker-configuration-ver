from __future__ import annotations

import logging
import os
from dataclasses import asdict
from typing import Any, Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import AppConfig, TargetConfig, MallTargetConfig
from .util import all_keywords_present, any_keyword_present, clean_text, parse_int


logger = logging.getLogger(__name__)


SHOP_API_URL = "https://openapi.naver.com/v1/search/shop.json"


class NaverShoppingSearchClient:
    def __init__(self, timeout_seconds: int = 20) -> None:
        self.client_id = os.getenv("NAVER_CLIENT_ID", "")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
        self.user_agent = os.getenv("USER_AGENT", "NaverPriceTracker/1.0")
        self.timeout_seconds = int(os.getenv("REQUEST_TIMEOUT", str(timeout_seconds)))
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _headers(self) -> dict[str, str]:
        if not self.client_id or not self.client_secret:
            raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 설정되지 않았습니다.")
        return {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    def search(self, *, query: str, display: int = 100, start: int = 1, sort: str = "asc", filter_: str | None = None, exclude: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort,
        }
        if filter_:
            params["filter"] = filter_
        if exclude:
            params["exclude"] = exclude

        response = self.session.get(
            SHOP_API_URL,
            headers=self._headers(),
            params=params,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()



def _item_matches(target: TargetConfig, item: dict[str, Any]) -> bool:
    title = clean_text(item.get("title"))
    product_id = str(item.get("productId", "") or "").strip()
    target_id = str(target.match.product_id or "").strip()
    product_type = int(item.get("productType", 0) or 0)

    # 1. productId가 지정된 경우 (플레이스홀더인 '[숫자_ID]' 등은 제외)
    is_placeholder = "[" in target_id or "ID" in target_id or not target_id
    
    if target_id and not is_placeholder:
        if product_id == target_id:
            if target.match.allowed_product_types and product_type not in target.match.allowed_product_types:
                return False
            return True
        return False

    # 2. product_id가 없는 경우 기존 키워드 기반 매칭 유지
    if target.match.allowed_product_types and product_type not in target.match.allowed_product_types:
        return False
    if target.match.required_keywords and not all_keywords_present(title, target.match.required_keywords):
        return False
    if target.match.exclude_keywords and any_keyword_present(title, target.match.exclude_keywords):
        return False
    return True



def _normalized_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": clean_text(item.get("title")),
        "price": parse_int(item.get("lprice"), default=0),
        "seller_name": clean_text(item.get("mallName")),
        "product_id": str(item.get("productId", "") or "") or None,
        "product_type": int(item.get("productType", 0) or 0),
        "product_url": item.get("link"),
        "image_url": item.get("image"),
        "search_rank": item.get("_search_rank"),
        "raw_payload": item,
    }



def collect_lowest_offer_via_api(client: NaverShoppingSearchClient, app_config: AppConfig, target: TargetConfig) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not target.query:
        raise ValueError(f"target '{target.name}' 에 query 가 없습니다.")

    # 만약 product_id가 지정되어 있다면, 정확한 카탈로그를 찾기 위해 정렬을 'sim'으로 강제하고 검색 범위를 넓힘
    search_sort = target.request.sort
    display_limit = app_config.display
    pages = max(1, target.request.pages)
    
    if target.match.product_id:
        search_sort = "sim"
        display_limit = 100 # 최대치로 확장
        pages = max(2, pages) # ID 검색 시에는 최소 2페이지(200건)까지 뒤지도록 보강
        logger.info(f"  └─ [{target.name}] ID 기반 매칭 모드: 정렬=sim, 검색범위={display_limit*pages}건 확대")

    items: list[dict[str, Any]] = []

    for page_index in range(pages):
        start = page_index * display_limit + 1
        payload = client.search(
            query=target.query,
            display=display_limit,
            start=start,
            sort=search_sort,
            filter_=target.request.filter,
            exclude=app_config.exclude,
        )
        page_items = payload.get("items", []) or []
        for i, itm in enumerate(page_items, start=len(items) + 1):
            itm["_search_rank"] = i
        items.extend(page_items)

    candidates = [_normalized_item(item) for item in items if _item_matches(target, item)]
    candidates = [c for c in candidates if c["price"] > 0]

    if not candidates:
        return {
            "target_name": target.name,
            "source_mode": target.mode,
            "success": 0,
            "status": "NO_MATCH",
            "title": None,
            "price": None,
            "seller_name": None,
            "product_id": target.match.product_id,
            "product_type": None,
            "product_url": None,
            "raw_payload": {
                "query": target.query,
                "request": asdict(target.request),
                "match": asdict(target.match),
                "items_examined": len(items),
            },
            "error_message": "조건에 맞는 상품을 찾지 못했습니다.",
        }, items

    # 가격과 판매처 이름을 기준으로 정렬하여 최우선 상품 선택
    best = min(candidates, key=lambda x: (x["price"], x["seller_name"] or "zzzz"))
    return {
        "target_name": target.name,
        "source_mode": target.mode,
        "success": 1,
        "status": "OK",
        **best,
        "error_message": None,
    }, candidates

def collect_mall_inventory(client: NaverShoppingSearchClient, app_config: AppConfig, target: MallTargetConfig) -> list[dict[str, Any]]:
    if not target.query:
        raise ValueError(f"mall_target '{target.name}' 에 query 가 없습니다.")

    pages = max(1, target.request.pages)
    items: list[dict[str, Any]] = []
    
    for page_index in range(pages):
        start = page_index * app_config.display + 1
        payload = client.search(
            query=target.query,
            display=app_config.display,
            start=start,
            sort=target.request.sort,
            filter_=target.request.filter,
            exclude=app_config.exclude,
        )
        page_items = payload.get("items", []) or []
        for i, itm in enumerate(page_items, start=len(items) + 1):
            itm["_search_rank"] = i
        items.extend(page_items)

    candidates = []
    target_mall = clean_text(target.mall_name)
    for item in items:
        seller = clean_text(item.get("mallName"))
        if target_mall in seller:
            candidates.append(_normalized_item(item))

    return candidates


def collect_mall_items(client: NaverShoppingSearchClient, app_config: AppConfig, query: str, pages: int) -> list[dict[str, Any]]:
    """지정된 쿼리로 네이버 쇼핑 API를 호출하여 전체 상품 리스트를 반환합니다."""
    if not query:
        raise ValueError("query 가 없습니다.")

    pages = max(1, pages)
    items: list[dict[str, Any]] = []
    
    for page_index in range(pages):
        start = page_index * app_config.display + 1
        try:
            payload = client.search(
                query=query,
                display=app_config.display,
                start=start,
                sort="sim", # 몰 수집은 기본적으로 유사도순(랭킹순)으로 수집
                exclude=app_config.exclude,
            )
            page_items = payload.get("items", []) or []
            for i, itm in enumerate(page_items, start=len(items) + 1):
                itm["_search_rank"] = i
            items.extend(page_items)
        except Exception:
            # 한 페이지 실패해도 나머지는 계속 시도
            continue

    return [_normalized_item(item) for item in items]

