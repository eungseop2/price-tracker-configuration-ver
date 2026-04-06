import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("tracker.notifier")


def send_price_alert(
    changes: list[dict],
    email_from: str,
    email_password: str,
    email_to: str | list[str],
) -> bool:
    """媛寃?蹂????ぉ 由ъ뒪?몃? ?대찓?쇰줈 ?뚮┰?덈떎. ?깃났 ??True 諛섑솚."""
    if not all([email_from, email_password, email_to]):
        logger.info("?대찓???ㅼ젙???놁뼱 ?뚮┝??嫄대꼫?곷땲??")
        return False

    downs = [c for c in changes if c.get("price_change_status") == "PRICE_DOWN"]
    ups = [c for c in changes if c.get("price_change_status") == "PRICE_UP"]

    if not downs and not ups:
        logger.info("媛寃?蹂???놁쓬 - ?대찓??諛쒖넚 ?앸왂")
        return False

    subject = _build_subject(downs, ups)
    html_body = _build_html(downs, ups)

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = email_from
        
        if isinstance(email_to, list):
            recipients = [e.strip() for e in email_to if e.strip()]
        else:
            recipients = [e.strip() for e in email_to.split(",") if e.strip()]
            
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_from, email_password)
            server.sendmail(email_from, recipients, msg.as_string())

        logger.info("媛寃?蹂???대찓??諛쒖넚 ?꾨즺 ??%s", ", ".join(recipients))
        return True
    except Exception as e:
        logger.error("?대찓??諛쒖넚 ?ㅽ뙣: %s", e)
        return False


def _build_subject(downs: list, ups: list) -> str:
    parts = []
    if downs:
        parts.append(f"?뱣 媛寃??섎씫 {len(downs)}嫄?)
    if ups:
        parts.append(f"?뱢 媛寃??곸듅 {len(ups)}嫄?)
    return f"[Price Insight Pro] {' / '.join(parts)}"


def _build_html(downs: list, ups: list) -> str:
    rows = ""

    def make_rows(items, color, icon):
        result = ""
        for item in items:
            name = item.get("target_name", "")
            price = item.get("price", 0)
            prev = item.get("prev_price") or 0
            url = item.get("product_url", "#")
            pct = item.get("price_delta_pct")
            pct_str = f"{pct:+.1f}%" if pct is not None else ""
            result += f"""
            <tr>
                <td style="padding:8px;border-bottom:1px solid #eee">
                    <a href="{url}" style="text-decoration:none;color:#1e293b">{icon} {name}</a>
                </td>
                <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">
                    <s style="color:#999">{prev:,}??/s> ??
                    <b style="color:{color}">{price:,}??/b>
                </td>
                <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;color:{color}">
                    <b>{pct_str}</b>
                </td>
            </tr>"""
        return result

    rows += make_rows(downs, "#16a34a", "?뱣")
    rows += make_rows(ups, "#dc2626", "?뱢")

    return f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:auto;padding:20px">
    <h2 style="color:#1e293b">?뮕 Price Insight Pro 媛寃?蹂???뚮┝</h2>
    <table width="100%" style="border-collapse:collapse;margin-top:16px">
        <thead>
            <tr style="background:#f1f5f9">
                <th style="padding:8px;text-align:left">?곹뭹紐?/th>
                <th style="padding:8px;text-align:right">媛寃?/th>
                <th style="padding:8px;text-align:right">蹂?숇쪧</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    <div style="margin-top:24px;text-align:center">
        <a href="https://eungseop2.github.io/Lowest-Price-Tracker/" 
           style="background-color:#2563eb;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block">
           ?뱤 ??쒕낫??諛붾줈媛湲?
        </a>
    </div>
    <p style="color:#94a3b8;font-size:12px;margin-top:24px">
        Price Insight Pro 쨌 ?먮룞 諛쒖넚 ?대찓?쇱엯?덈떎.
    </p>
    </body></html>
    """

