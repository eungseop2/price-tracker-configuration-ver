from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class MatchConfig:
    required_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    product_id: str | None = None
    allowed_product_types: list[int] = field(default_factory=list)


@dataclass
class EmailConfig:
    email_from: str | None = None
    email_password: str | None = None
    email_to: list[str] = field(default_factory=list)


@dataclass
class RequestConfig:
    pages: int = 1
    sort: str = "sim"
    filter: str | None = None


@dataclass
class BrowserConfig:
    wait_until: str = "networkidle"
    click_selectors: list[str] = field(default_factory=list)
    offer_row_selector: str = "li"
    seller_selector: str = "a, span"
    price_selector: str = "strong, em, span"
    take_screenshot_on_failure: bool = True


@dataclass
class TargetConfig:
    name: str
    mode: str
    query: str | None = None
    rank_query: str | None = None
    url: str | None = None
    fallback_url: str | None = None
    category: str = "湲고?"  # ?곹뭹 移댄뀒怨좊━ (遺꾨쪟??
    match: MatchConfig = field(default_factory=MatchConfig)
    request: RequestConfig = field(default_factory=RequestConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)


@dataclass
class AppConfig:
    display: int = 100
    exclude: str = "used:cbshop"
    timeout_seconds: int = 20
    alert_threshold_percent: float = 5.0
    email: EmailConfig = field(default_factory=EmailConfig)
    targets: list[TargetConfig] = field(default_factory=list)


def _to_match(raw: dict[str, Any] | None) -> MatchConfig:
    raw = raw or {}
    return MatchConfig(
        required_keywords=list(raw.get("required_keywords", []) or []),
        exclude_keywords=list(raw.get("exclude_keywords", []) or []),
        product_id=(str(raw["product_id"]) if raw.get("product_id") is not None else None),
        allowed_product_types=[int(x) for x in (raw.get("allowed_product_types", []) or [])],
    )


def _to_request(raw: dict[str, Any] | None) -> RequestConfig:
    raw = raw or {}
    try:
        pages = int(raw.get("pages", 1))
    except (ValueError, TypeError):
        pages = 0  # validate_config will catch this
    return RequestConfig(
        pages=pages,
        sort=str(raw.get("sort", "asc")),
        filter=raw.get("filter"),
    )


def _to_browser(raw: dict[str, Any] | None) -> BrowserConfig:
    raw = raw or {}
    return BrowserConfig(
        wait_until=str(raw.get("wait_until", "networkidle")),
        click_selectors=list(raw.get("click_selectors", []) or []),
        offer_row_selector=str(raw.get("offer_row_selector", "li")),
        seller_selector=str(raw.get("seller_selector", "a, span")),
        price_selector=str(raw.get("price_selector", "strong, em, span")),
        take_screenshot_on_failure=bool(raw.get("take_screenshot_on_failure", True)),
    )


def validate_config(app: AppConfig, extra_errors: list[str] | None = None) -> None:
    """?ㅼ젙 ?좏슚?깆쓣 寃利앺븯怨??ㅻ쪟媛 ?덉쑝硫?ValueError瑜?諛쒖깮?쒗궢?덈떎 (Fail-Fast)."""
    errors: list[str] = list(extra_errors or [])
    names: set[str] = set()

    for t in app.targets:
        # ?대쫫 以묐났 寃??
        if t.name in names:
            errors.append(f"以묐났???寃??대쫫: {t.name}")
        names.add(t.name)

        # 紐⑤뱶 寃??
        if t.mode not in ("api_query", "browser_url"):
            errors.append(f"[{t.name}] 吏?먰븯吏 ?딅뒗 mode: {t.mode!r}")

        # ?꾩닔 ?꾨뱶 寃??
        if t.mode == "api_query" and not t.query:
            errors.append(f"[{t.name}] api_query 紐⑤뱶?먮뒗 'query' ?꾨뱶媛 ?꾩닔?낅땲??")
        if t.mode == "browser_url" and not t.url:
            errors.append(f"[{t.name}] browser_url 紐⑤뱶?먮뒗 'url' ?꾨뱶媛 ?꾩닔?낅땲??")

        # ?대갚 議곌굔 寃??
        if t.fallback_url and t.mode != "api_query":
            errors.append(f"[{t.name}] fallback_url? api_query 紐⑤뱶?먯꽌留??ъ슜?????덉뒿?덈떎.")

        # ?섏씠吏 踰붿쐞 寃??
        if t.request.pages < 1:
            errors.append(f"[{t.name}] pages??1 ?댁긽?댁뼱???⑸땲??")

    # ?뚮┝ ?꾧퀎媛?寃??
    if not (0 < app.alert_threshold_percent < 100):
        errors.append(f"alert_threshold_percent 踰붿쐞媛 鍮꾩젙?곸쟻?낅땲??(0~100): {app.alert_threshold_percent}")

    if errors:
        raise ValueError("?ㅼ젙 ?좏슚??寃利??ㅽ뙣:\n" + "\n".join(f"- {e}" for e in errors))


def load_config(path: str | Path) -> AppConfig:
    import os
    from dotenv import load_dotenv
    load_dotenv(override=False)
    
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"?ㅼ젙 ?뚯씪??李얠쓣 ???놁뒿?덈떎: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    common = raw.get("common", {}) or {}
    email_raw = common.get("email", {}) or {}

    errors = []
    
    # 1. common ?뱀뀡 ?뚯떛 (?먮윭 ?꾩쟻)
    try:
        display = min(100, max(1, int(common.get("display", 100))))
    except (ValueError, TypeError):
        errors.append(f"common.display 媛믪씠 ?щ컮瑜댁? ?딆뒿?덈떎: {common.get('display')}")
        display = 100

    try:
        timeout_seconds = max(5, int(common.get("timeout_seconds", 20)))
    except (ValueError, TypeError):
        errors.append(f"common.timeout_seconds 媛믪씠 ?щ컮瑜댁? ?딆뒿?덈떎: {common.get('timeout_seconds')}")
        timeout_seconds = 20

    try:
        alert_threshold_percent = float(common.get("alert_threshold_percent", 5.0))
    except (ValueError, TypeError):
        errors.append(f"common.alert_threshold_percent 媛믪씠 ?щ컮瑜댁? ?딆뒿?덈떎: {common.get('alert_threshold_percent')}")
        alert_threshold_percent = 5.0

    # 1-1. ?대찓???ㅼ젙 ?뚯떛 (?섍꼍蹂??-> YAML ?쒖꽌濡??곗꽑?쒖쐞)
    email_from = os.getenv("EMAIL_FROM") or email_raw.get("from")
    email_password = os.getenv("EMAIL_APP_PASSWORD") or email_raw.get("password")
    
    to_raw = os.getenv("EMAIL_TO") or email_raw.get("to", "")
    if isinstance(to_raw, list):
        email_to = [str(x).strip() for x in to_raw if x]
    else:
        email_to = [x.strip() for x in str(to_raw).split(",") if x.strip()]

    app = AppConfig(
        display=display,
        exclude=str(common.get("exclude", "used:cbshop")),
        timeout_seconds=timeout_seconds,
        alert_threshold_percent=alert_threshold_percent,
        email=EmailConfig(
            email_from=email_from,
            email_password=email_password,
            email_to=email_to
        ),
        targets=[],
    )

    # 2. targets ?뱀뀡 ?뚯떛 (?먮윭 ?꾩쟻)
    for i, item in enumerate(raw.get("targets", []) or []):
        try:
            name = item.get("name")
            mode = item.get("mode")
            
            if not name or not mode:
                errors.append(f"targets[{i}]??'name' ?먮뒗 'mode'媛 ?꾨씫?섏뿀?듬땲??")
                continue

            target = TargetConfig(
                name=str(name),
                mode=str(mode),
                query=item.get("query"),
                rank_query=item.get("rank_query") or str(name),
                url=item.get("url"),
                fallback_url=item.get("fallback_url"),
                category=str(item.get("category", "湲고?")),
                match=_to_match(item.get("match")),
                request=_to_request(item.get("request")),
                browser=_to_browser(item.get("browser")),
            )
            
            app.targets.append(target)
        except Exception as e:
            errors.append(f"targets[{i}] ({item.get('name', 'unknown')}) 泥섎━ 以??ㅻ쪟: {e}")

    if errors:
        # validate_config瑜??몄텧?섍린 ?꾩뿉 ?대? ?섏쭛???먮윭媛 ?덉쑝硫??ш린???섏쭏 ?섎룄 ?덉쓬
        # ?섏?留?validate_config源뚯? ?⑹퀜??蹂댁뿬二쇰뒗 寃껋씠 ?붽뎄 ?ы빆
        pass

    try:
        validate_config(app, extra_errors=errors)
    except ValueError as e:
        raise e
    
    return app

