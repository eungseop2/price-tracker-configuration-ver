import json
from datetime import datetime, timedelta, timezone
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from .config import TargetConfig
from .util import format_price, get_dashboard_url, kst_now

logger = logging.getLogger("tracker.report")

def generate_daily_report_html(store: "GoogleSheetStore", targets: list[TargetConfig]) -> str:
    """최근 10일간의 가격 동향 HTML 보고서를 생성합니다. (GSheet 버전)"""
    # 10일치 날짜 계산 (KST 기준)
    now_kst = kst_now()
    now_utc = datetime.now(timezone.utc)
    # 오늘 포함 과거 10일
    dates_kst = [(now_kst - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(9, -1, -1)]
    
    cutoff_utc = (now_utc - timedelta(days=12)).isoformat()
    
    # GSheet에서 데이터 가져오기
    ws = store._get_worksheet("observations")
    rows = ws.get_all_records()
    filtered_rows = [r for r in rows if r.get("success") == 1 and r.get("price") and r["collected_at"] >= cutoff_utc]
    
    daily_min = {}
    for r in filtered_rows:
        t_name = r["target_name"]
        # ISO 형식에서 UTC datetime 객체 생성
        try:
            t_str = r["collected_at"].replace('Z', '+00:00')
            t_utc = datetime.fromisoformat(t_str)
            t_kst = t_utc + timedelta(hours=9)
            d_str = t_kst.strftime("%Y-%m-%d")
        except:
            continue
        
        if d_str not in daily_min:
            daily_min[d_str] = {}
        
        try:
            price_val = int(r["price"])
            seller_val = r.get("seller_name") or ""
            
            if t_name not in daily_min[d_str]:
                daily_min[d_str][t_name] = {"price": price_val, "seller": seller_val}
            else:
                if price_val < daily_min[d_str][t_name]["price"]:
                    daily_min[d_str][t_name] = {"price": price_val, "seller": seller_val}
        except:
            continue
    
    # HTML 빌드
    target_names = [t.name for t in targets]
    
    # 테이블 헤더
    header_html = ''.join(f'<th style="padding:10px;text-align:right;border:1px solid #ddd;background:#f8f9fa;">{d[5:]}</th>' for d in dates_kst)
    
    rows_html = ""
    for name in target_names:
        row_cells = []
        prev_price = None
        for i, d in enumerate(dates_kst):
            p_info = daily_min.get(d, {}).get(name)
            if p_info:
                price_val = p_info["price"]
                seller_name = p_info["seller"]
                color = "#000"
                if prev_price is not None:
                    if price_val < prev_price: color = "#2563eb" # 하락(파란색)
                    elif price_val > prev_price: color = "#dc2626" # 상승(빨간색)
                
                seller_html = f'<br/><span style="font-size:10px;color:#6b7280">({seller_name})</span>' if seller_name else ""
                row_cells.append(f'<td style="padding:10px;text-align:right;border:1px solid #ddd;color:{color};line-height:1.4;">{format_price(price_val)}{seller_html}</td>')
                prev_price = price_val
            else:
                row_cells.append('<td style="padding:10px;text-align:right;border:1px solid #ddd;color:#aaa;">-</td>')
        
        rows_html += f"<tr><td style='padding:10px;border:1px solid #ddd;font-weight:bold;'>{name}</td>{''.join(row_cells)}</tr>"

    html_body = f"""
    <html><body style="font-family:sans-serif;max-width:900px;margin:auto;padding:20px">
    <h2 style="color:#1e293b">📊 최근 10일 모델별 최저가 일일 리포트</h2>
    <p style="color:#64748b;font-size:14px;margin-bottom:20px">KST 기준, 매일 수집된 가격 중 최저가를 보여줍니다. (생성: {now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST)</p>
    <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; font-size:13px; min-width:800px;">
            <thead>
                <tr>
                    <th style="padding:10px;text-align:left;border:1px solid #ddd;background:#f8f9fa;width:180px;">모델명</th>
                    {header_html}
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    <div style="margin-top:32px;text-align:center">
        <a href="{get_dashboard_url()}" 
           style="background-color:#2563eb;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block">
           📊 대시보드 바로가기
        </a>
    </div>
    </body></html>
    """
    return html_body

def generate_mall_report_html(store: "GoogleSheetStore") -> str:
    """쇼핑몰 셀러별 가격 현황 HTML 리포트를 생성합니다."""
    mall_data = store.get_mall_report_data()
    now_kst = kst_now()
    
    sections = []
    for cat, malls in mall_data.items():
        for mall_name, m_info in malls.items():
            rows = []
            for p in m_info.get("products", []):
                price_fmt = format_price(p.get("price"))
                rows.append(f'<tr><td style="padding:8px;border:1px solid #eee;">{p.get("collected_at", "")}</td><td style="padding:8px;border:1px solid #eee;">{p.get("title", "")}</td><td style="padding:8px;border:1px solid #eee;text-align:right;">{price_fmt}</td><td style="padding:8px;border:1px solid #eee;"><a href="{p.get("url", "#")}" target="_blank">링크</a></td></tr>')
            
            sections.append(f"""
            <div style="margin-bottom:40px; background:white; padding:20px; border-radius:12px; border:1px solid #eee; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                <h3 style="margin-top:0; color:#2563eb;">[{cat}] {mall_name}</h3>
                <p style="font-size:13px; color:#64748b;">총 수집 상품: {m_info.get('total_products', 0)}개</p>
                <table style="width:100%; border-collapse:collapse; font-size:12px; border:1px solid #eee;">
                    <thead><tr style="background:#f8f9fa;"><th style="padding:8px;border:1px solid #eee;">수집시각</th><th style="padding:8px;border:1px solid #eee;">상품명</th><th style="padding:8px;border:1px solid #eee;">현재가</th><th style="padding:8px;border:1px solid #eee;">URL</th></tr></thead>
                    <tbody>{" ".join(rows)}</tbody>
                </table>
            </div>
            """)

    return f"""
    <html><body style="font-family:sans-serif; background:#f8fafc; padding:40px; max-width:1000px; margin:auto;">
        <h2 style="color:#1e293b">🏢 쇼핑몰 셀러별 추적 리포트</h2>
        <p style="color:#64748b; margin-bottom:30px;">수집 시각: {now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST</p>
        {" ".join(sections)}
        <div style="margin-top:40px; text-align:center;">
            <a href="{get_dashboard_url()}" style="color:#2563eb; text-decoration:none; font-weight:bold;">← 대시보드로 돌아가기</a>
        </div>
    </body></html>
    """


def send_daily_report(store: "GoogleSheetStore", email_from: str, email_password: str, email_to: str | list[str], targets: list[TargetConfig]) -> bool:
    if not all([email_from, email_password, email_to]):
        logger.info("이메일 설정이 없어 데일리 리포트 알림을 건너뜜")
        return False
        
    html_body = generate_daily_report_html(store, targets)
    
    # 10일치 날짜 계산 (제목용)
    now_kst = kst_now()
    date_str = now_kst.strftime("%Y-%m-%d")
    subject = f"📊 [Daily Report] {date_str} 최저가 변동 요약"
    
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

        logger.info("데일리 리포트 이메일 발송 완료 → %s", ", ".join(recipients))
        return True
    except Exception as e:
        logger.error("데일리 리포트 이메일 발송 실패: %s", e)
        return False
