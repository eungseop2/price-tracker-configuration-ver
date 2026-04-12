from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable
import os

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
PRICE_RE = re.compile(r"([0-9][0-9,]{0,20})")


def kst_now() -> datetime:
    """한국 표준시(KST) 현재 시각을 반환합니다."""
    return datetime.now(timezone(timedelta(hours=9)))


def now_iso() -> str:
    """KST 현재 시각을 ISO 포맷(YYYY-MM-DDTHH:MM:SS.mmmmmm+09:00)으로 반환합니다."""
    return kst_now().isoformat()


def utc_now_iso() -> str:
    """기존 코드와의 호환성을 유지하되, 내부적으로 KST(now_iso)를 사용합니다."""
    return now_iso()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = html.unescape(text)
    text = TAG_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def normalize_for_match(value: Any) -> str:
    """매칭을 위해 텍스트를 정규화합니다. (소문자 변환, 공백 및 특수문자 제거)"""
    text = clean_text(value).lower()
    # 알파벳, 숫자, 한글만 남기고 모두 제거 (매칭 견고함 향상)
    return re.sub(r'[^a-z0-9가-힣]', '', text)


def parse_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    match = PRICE_RE.search(str(value).replace("원", ""))
    if not match:
        return default
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return default


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def all_keywords_present(text: str, keywords: Iterable[str]) -> bool:
    haystack = normalize_for_match(text)
    return all(normalize_for_match(k) in haystack for k in keywords)


def any_keyword_present(text: str, keywords: Iterable[str]) -> bool:
    haystack = normalize_for_match(text)
    return any(normalize_for_match(k) in haystack for k in keywords)


def format_price(value: int | None) -> str:
    """정수 가격을 '12,345원' 형식의 문자열로 변환합니다."""
    if value is None:
        return "-"
    return f"{value:,}원"


def calc_change_metrics(current: int, previous: int | None) -> tuple[int | None, float | None]:
    """이전 가격 대비 현재 가격의 변동액(delta)과 변동률(delta_pct)을 반환합니다."""
    if previous is None or previous == 0:
        return None, None
    delta = current - previous
    pct = round(delta / previous * 100, 2)
    return delta, pct
def is_night_time_kst() -> bool:
    """KST(한국 표준시) 기준 야간 시간(21:00 ~ 08:00) 여부를 확인합니다."""
    kst = timezone(timedelta(hours=9))
    current_hour_kst = datetime.now(kst).hour
    # 21시부터 다음 날 08시 사이는 야간으로 간주
    return current_hour_kst >= 21 or current_hour_kst < 8


def get_dashboard_url() -> str:
    """대시보드 URL을 환경 변수에서 가져오거나 자동 생성합니다."""
    # 1. 명시적 환경 변수 (커스텀 도메인 등)
    env_url = os.getenv("DASHBOARD_URL")
    if env_url:
        return env_url.rstrip("/") + "/"

    # 2. GitHub 환경 변수 기반 자동 생성
    # GITHUB_REPOSITORY = "owner/repo"
    repo_full_name = os.getenv("GITHUB_REPOSITORY")
    if repo_full_name and "/" in repo_full_name:
        owner, repo = repo_full_name.split("/", 1)
        return f"https://{owner}.github.io/{repo}/"

    # 3. 기본값 (원본 저장소)
    return "https://eungseop2.github.io/price-tracker-configuration-ver/"
