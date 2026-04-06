from __future__ import annotations

import logging
import os
from pathlib import Path

from .util import format_price, utc_now_iso

logger = logging.getLogger("naver_price_tracker.alert")

_ALERT_LOG_PATH = "./price_alerts.log"


def check_and_alert(result: dict, prev_price: int | None, threshold: float) -> bool:
    """吏곸쟾 ?깃났媛 ?鍮??꾩옱 媛寃⑹씠 ?꾧퀎媛??댁긽 ?섎씫?덈뒗吏 ?뺤씤?섍퀬 ?뚮┝??諛쒖깮?쒗궢?덈떎.
    
    Returns:
        bool: ?뚮┝??諛쒖깮?덈뒗吏 ?щ? (alert_triggered)
    """
    if not result.get("success"):
        return False
        
    current_price = result.get("price")
    if current_price is None or prev_price is None or prev_price == 0:
        return False

    # 怨꾩궛?? ((prev_price - current_price) / prev_price) * 100 >= threshold
    drop_pct = ((prev_price - current_price) / prev_price) * 100
    
    if drop_pct < threshold:
        return False

    target_name = result.get("target_name", "Unknown")
    seller = result.get("seller_name") or "-"
    message = (
        f"[媛寃⑺븯??寃쎄퀬] {target_name} | "
        f"{format_price(prev_price)} ??{format_price(current_price)} "
        f"({drop_pct:+.1f}% ?섎씫!) | ?먮ℓ泥? {seller}"
    )

    logger.warning(message)
    _write_alert_log(message)
    return True


def _write_alert_log(message: str) -> None:
    """?뚮┝??price_alerts.log ?뚯씪??異붽??⑸땲??"""
    try:
        log_path = Path(_ALERT_LOG_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = utc_now_iso()
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"{timestamp} | {message}\n")
    except OSError as exc:
        logger.debug("?뚮┝ 濡쒓렇 湲곕줉 ?ㅽ뙣: %s", exc)

