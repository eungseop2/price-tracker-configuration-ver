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



def _item_matches(target: TargetConfig, item: dict[str, Any], global_excludes: list[str] = None) -> bool:
    title = clean_text(item.get("title"))
    product_id = str(item.get("productId", "") or "").strip()
    target_id = str(target.match.product_id or "").strip()
    product_type = int(item.get("productType", 0) or 0)
    price = int(item.get("lprice", 0) or 0)

    # 0. 필수 필터링: 5만원 미만의 본품 아닌 제품 필터링 방어 코드
    if price > 0 and price < 50000:
        return False

    # 0-1. 최소 가격 필터링 (min_price 설정된 경우)
    if target.match.min_price and price < target.match.min_price:
        return False

    # 1. productId가 지정된 경우 (플레이스홀더인 '[숫자_ID]' 등은 제외)
    is_placeholder = "[" in target_id or "ID" in target_id or not target_id
    
    if target_id and not is_placeholder:
        if product_id == target_id:
            if target.match.allowed_product_types and product_type not in target.match.allowed_product_types:
                return False
            return True
        # 카탈로그 ID가 지정된 경우, ID가 다르면 제목과 상관없이 무조건 제외 (액세서리 오매칭 방지)
        return False

    # 2. product_id가 없는 경우 기존 키워드 기반 매칭 유지
    if target.match.allowed_product_types and product_type not in target.match.allowed_product_types:
        return False
    if target.match.required_keywords and not all_keywords_present(title, target.match.required_keywords):
        return False
    if target.match.exclude_keywords and any_keyword_present(title, target.match.exclude_keywords):
        return False
    # 추가: 글로벌 제외 키워드 체크
    if global_excludes and any_keyword_present(title, global_excludes):
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
        "search_rank": item.get("_search_rank"),
        "image_url": item.get("image"),  # 도용 감시용
    }



def collect_lowest_offer_via_api(client: NaverShoppingSearchClient, app_config: AppConfig, target: TargetConfig, broad_items: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not target.query:
        raise ValueError(f"target '{target.name}' 에 query 가 없습니다.")

    # 1. 상세 쿼리 수집 (기존 로직)
    search_sort = target.request.sort
    display_limit = app_config.display or 30
    pages = max(1, target.request.pages)
    
    if target.match.product_id:
        search_sort = "sim"
        display_limit = 100
        pages = 1 
        logger.info(f"  └─ [{target.name}] ID 기반 매칭 모드: 내부 수집 범위 확장(100건) - 판매처 매칭용")

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

    # 2. 후보군 추출 (상세 검색 결과)
    global_excludes = getattr(app_config, "global_exclude_keywords", [])
    candidates = [_normalized_item(item) for item in items if _item_matches(target, item, global_excludes=global_excludes)]
    
    # 3. 브로드 아이템(캐시) 병합 및 완화된 매칭 적용
    if broad_items:
        # 핵심 키워드(상위 2개)만 사용한 완화된 필터링
        main_keywords = target.match.required_keywords[:2] if target.match.required_keywords else []
        
        merged_count = 0
        for b_item in broad_items:
            b_id = str(b_item.get("productId", ""))
            
            # 기존 상세 결과에 동일한 ID가 있는 경우, 이를 제거하고 몰 전용 결과로 교체 (몰 이름 보존)
            existing_indices = [i for i, c in enumerate(candidates) if str(c.get("product_id")) == b_id]
            if existing_indices:
                for idx in reversed(existing_indices):
                    candidates.pop(idx)
                
            # 완화된 매칭 조건: 핵심 키워드가 포함되어 있는가?
            b_title = clean_text(b_item.get("title"))
            if main_keywords and all_keywords_present(b_title, main_keywords):
                candidates.append(_normalized_item(b_item))
                merged_count += 1
        
        if merged_count > 0:
            logger.debug(f"  └─ [{target.name}] 확장 검색(Broad Search) 결과 병합 중... {merged_count}건 추가 발견")

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
            "error_message": f"조건에 맞는 상품을 찾지 못했습니다. (검색: {len(items)}건)",
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
    }, [_normalized_item(item) for item in items]

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
    exclude_kws = getattr(target, "exclude_keywords", [])

    for item in items:
        seller = clean_text(item.get("mallName"))
        title = clean_text(item.get("title"))

        # 1. 셀러명 일치 확인
        if target_mall not in seller:
            continue
        
        # 2. 제외 키워드 확인
        if exclude_kws and any(k in title for k in exclude_kws):
            continue

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

