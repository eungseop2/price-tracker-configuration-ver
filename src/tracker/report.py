import sqlite3
from datetime import datetime, timedelta, timezone
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from .config import TargetConfig
from .util import format_price

logger = logging.getLogger("tracker.report")

def generate_daily_report_html(db_path: str, targets: list[TargetConfig]) -> str:
    """理쒓렐 10?쇨컙??媛寃??숉뼢 HTML 蹂닿퀬?쒕? ?앹꽦?⑸땲??"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # 10?쇱튂 ?좎쭨 怨꾩궛 (KST 湲곗?)
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    # ?ㅻ뒛 ?ы븿 怨쇨굅 10??
    dates_kst = [(now_kst - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(9, -1, -1)]
    
    cutoff_utc = now_utc - timedelta(days=12)
    
    rows = conn.execute(
        """
        SELECT target_name, collected_at, price 
        FROM observations 
        WHERE success = 1 AND price IS NOT NULL AND collected_at >= ?
        """,
        (cutoff_utc.isoformat(),)
    ).fetchall()
    
    daily_min = {}
    for r in rows:
        t_name = r["target_name"]
        t_utc = datetime.fromisoformat(r["collected_at"].replace('Z', '+00:00'))
        t_kst = t_utc + timedelta(hours=9)
        d_str = t_kst.strftime("%Y-%m-%d")
        
        if d_str not in daily_min:
            daily_min[d_str] = {}
        if t_name not in daily_min[d_str]:
            daily_min[d_str][t_name] = r["price"]
        else:
            daily_min[d_str][t_name] = min(daily_min[d_str][t_name], r["price"])
            
    conn.close()
    
    # HTML 鍮뚮뱶
    target_names = [t.name for t in targets]
    
    # ?뚯씠釉??ㅻ뜑
    header_html = ''.join(f'<th style="padding:10px;text-align:right;border:1px solid #ddd;background:#f8f9fa;">{d[5:]}</th>' for d in dates_kst)
    
    rows_html = ""
    for name in target_names:
        row_cells = []
        prev_price = None
        for i, d in enumerate(dates_kst):
            price_val = daily_min.get(d, {}).get(name)
            if price_val is not None:
                color = "#000"
                if prev_price is not None:
                    if price_val < prev_price: color = "#2563eb" # ?섎씫(?뚮???
                    elif price_val > prev_price: color = "#dc2626" # ?곸듅(鍮④컙??
                row_cells.append(f'<td style="padding:10px;text-align:right;border:1px solid #ddd;color:{color};">{format_price(price_val)}</td>')
                prev_price = price_val
            else:
                row_cells.append('<td style="padding:10px;text-align:right;border:1px solid #ddd;color:#aaa;">-</td>')
        
        rows_html += f"<tr><td style='padding:10px;border:1px solid #ddd;font-weight:bold;'>{name}</td>{''.join(row_cells)}</tr>"

    html_body = f"""
    <html><body style="font-family:sans-serif;max-width:900px;margin:auto;padding:20px">
    <h2 style="color:#1e293b">?뱤 理쒓렐 10??紐⑤뜽蹂?理쒖?媛 ?쇱씪 由ы룷??/h2>
    <p style="color:#64748b;font-size:14px;margin-bottom:20px">KST 湲곗?, 留ㅼ씪 ?섏쭛??媛寃?以?理쒖?媛瑜?蹂댁뿬以띾땲?? (?앹꽦: {now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST)</p>
    <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; font-size:13px; min-width:800px;">
            <thead>
                <tr>
                    <th style="padding:10px;text-align:left;border:1px solid #ddd;background:#f8f9fa;width:180px;">紐⑤뜽紐?/th>
                    {header_html}
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    <div style="margin-top:32px;text-align:center">
        <a href="https://youngseop77.github.io/price-tracker-configuration-ver/" 
           style="background-color:#2563eb;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block">
           ?뱤 ??쒕낫??諛붾줈媛湲?
        </a>
    </div>
    </body></html>
    """
    return html_body


def send_daily_report(db_path: str, email_from: str, email_password: str, email_to: str | list[str], targets: list[TargetConfig]) -> bool:
    if not all([email_from, email_password, email_to]):
        logger.info("?대찓???ㅼ젙???놁뼱 ?곗씪由?由ы룷???뚮┝??嫄대꼫?곷땲??")
        return False
        
    html_body = generate_daily_report_html(db_path, targets)
    
    # 10?쇱튂 ?좎쭨 怨꾩궛 (?쒕ぉ??
    now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
    date_str = now_kst.strftime("%Y-%m-%d")
    subject = f"?뱤 [Daily Report] {date_str} 理쒖?媛 蹂???붿빟"
    
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

        logger.info("?곗씪由?由ы룷???대찓??諛쒖넚 ?꾨즺 ??%s", ", ".join(recipients))
        return True
    except Exception as e:
        logger.error("?곗씪由?由ы룷???대찓??諛쒖넚 ?ㅽ뙣: %s", e)
        return False

