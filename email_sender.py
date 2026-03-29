import httpx
import base64
import os

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "roiaharon456@gmail.com")


async def send_email(user: dict, details: dict, invoice_bytes: bytes, filename: str, content_type: str):
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

    safe_filename = filename.encode("ascii", "ignore").decode() or "invoice.jpg"
    attachment_content = base64.b64encode(invoice_bytes).decode("utf-8")

    subject = f"בקשת החזר | {user['name']} | {details.get('supplier', '')} | {details.get('amount', '')}"

    payload = {
        "from": "מערכת החזר הוצאות <onboarding@resend.dev>",
        "to": [RECIPIENT_EMAIL],
        "subject": subject,
        "html": html_body,
        "attachments": [
            {
                "filename": safe_filename,
                "content": attachment_content
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        response.raise_for_status()
