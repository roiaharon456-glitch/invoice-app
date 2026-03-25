import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

GMAIL_USER = os.getenv("GMAIL_USER", "roiaharon456@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "roiaharon456@gmail.com")


async def send_email(user: dict, details: dict, invoice_bytes: bytes, filename: str, content_type: str):
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = f"בקשת החזר | {user['name']} | {details.get('supplier', '')} | {details.get('amount', '')}"

    html_body = f"""
    <html dir="rtl">
    <head>
      <meta charset="UTF-8">
      <style>
        body {{ font-family: Arial, sans-serif; direction: rtl; text-align: right; color: #333; }}
        h2 {{ color: #2c5282; border-bottom: 2px solid #2c5282; padding-bottom: 8px; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 500px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px 14px; text-align: right; }}
        th {{ background-color: #ebf4ff; color: #2c5282; font-weight: bold; width: 40%; }}
        td {{ background-color: #f9f9f9; }}
        .section-title {{ margin-top: 24px; margin-bottom: 8px; font-weight: bold; color: #555; font-size: 14px; }}
      </style>
    </head>
    <body>
      <h2>בקשת החזר הוצאה</h2>

      <p class="section-title">פרטי מגיש הבקשה</p>
      <table>
        <tr><th>שם</th><td>{user['name']}</td></tr>
        <tr><th>שם בעל החשבון</th><td>{user['account_holder']}</td></tr>
        <tr><th>בנק</th><td>{user['bank_name']}</td></tr>
        <tr><th>מספר בנק</th><td>{user['bank_number']}</td></tr>
        <tr><th>מספר סניף</th><td>{user['branch_number']}</td></tr>
        <tr><th>מספר חשבון</th><td>{user['account_number']}</td></tr>
      </table>

      <p class="section-title">פרטי החשבונית</p>
      <table>
        <tr><th>ספק</th><td>{details.get('supplier', 'לא זוהה')}</td></tr>
        <tr><th>סכום</th><td><strong>{details.get('amount', 'לא זוהה')}</strong></td></tr>
        <tr><th>תאריך</th><td>{details.get('date', 'לא זוהה')}</td></tr>
        <tr><th>תיאור</th><td>{details.get('description', 'לא זוהה')}</td></tr>
      </table>

      <p style="margin-top: 24px; font-size: 12px; color: #888;">החשבונית המקורית מצורפת למייל זה.</p>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    part = MIMEBase("application", "octet-stream")
    part.set_payload(invoice_bytes)
    encoders.encode_base64(part)
    safe_filename = filename.encode("ascii", "ignore").decode() or "invoice.jpg"
    part.add_header("Content-Disposition", f'attachment; filename="{safe_filename}"')
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
