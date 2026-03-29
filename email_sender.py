import httpx
import base64
import os

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "roiaharon456@gmail.com")


async def send_email(user: dict, details: dict, invoice_bytes: bytes, filename: str, content_type: str, expense_reason: str = ""):
    amount = details.get('amount', 'לא זוהה')
    reason_text = expense_reason if expense_reason else "הוצאה"

    html_body = f"""<!DOCTYPE html>
<html lang="he">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
</head>
<body style="margin:0;padding:20px;font-family:Arial,sans-serif;direction:rtl;text-align:right;color:#333;font-size:12pt;line-height:1.7;background:#f5f7fa;">
  <div style="max-width:580px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <div style="background:#2c5282;padding:20px 24px;">
      <h2 style="margin:0;color:#fff;font-size:16pt;direction:rtl;text-align:right;">בקשת החזר הוצאה</h2>
    </div>

    <div style="padding:24px;">

      <div style="background:#f0f7ff;border-right:4px solid #2c5282;padding:16px 18px;margin-bottom:24px;border-radius:4px;direction:rtl;text-align:right;font-size:12pt;line-height:1.9;">
        היי,<br><br>
        מצורפת חשבונית לזיכוי בגין <strong>{reason_text}</strong>, על סך: <strong>{amount}</strong>.<br>
        להלן פרטי המוטב לביצוע ההעברה.
      </div>

      <p style="margin:0 0 8px 0;font-weight:bold;color:#555;font-size:12pt;direction:rtl;text-align:right;">פרטי מגיש הבקשה</p>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;direction:rtl;font-size:12pt;margin-bottom:20px;">
        <tr><td style="border:1px solid #ddd;padding:10px 14px;background:#ebf4ff;color:#2c5282;font-weight:bold;width:40%;text-align:right;">שם</td><td style="border:1px solid #ddd;padding:10px 14px;background:#f9f9f9;text-align:right;">{user['name']}</td></tr>
        <tr><td style="border:1px solid #ddd;padding:10px 14px;background:#ebf4ff;color:#2c5282;font-weight:bold;text-align:right;">שם בעל החשבון</td><td style="border:1px solid #ddd;padding:10px 14px;background:#f9f9f9;text-align:right;">{user['account_holder']}</td></tr>
        <tr><td style="border:1px solid #ddd;padding:10px 14px;background:#ebf4ff;color:#2c5282;font-weight:bold;text-align:right;">בנק</td><td style="border:1px solid #ddd;padding:10px 14px;background:#f9f9f9;text-align:right;">{user['bank_name']}</td></tr>
        <tr><td style="border:1px solid #ddd;padding:10px 14px;background:#ebf4ff;color:#2c5282;font-weight:bold;text-align:right;">מספר בנק</td><td style="border:1px solid #ddd;padding:10px 14px;background:#f9f9f9;text-align:right;">{user['bank_number']}</td></tr>
        <tr><td style="border:1px solid #ddd;padding:10px 14px;background:#ebf4ff;color:#2c5282;font-weight:bold;text-align:right;">מספר סניף</td><td style="border:1px solid #ddd;padding:10px 14px;background:#f9f9f9;text-align:right;">{user['branch_number']}</td></tr>
        <tr><td style="border:1px solid #ddd;padding:10px 14px;background:#ebf4ff;color:#2c5282;font-weight:bold;text-align:right;">מספר חשבון</td><td style="border:1px solid #ddd;padding:10px 14px;background:#f9f9f9;text-align:right;">{user['account_number']}</td></tr>
      </table>

      <p style="margin:0 0 8px 0;font-weight:bold;color:#555;font-size:12pt;direction:rtl;text-align:right;">פרטי החשבונית</p>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;direction:rtl;font-size:12pt;margin-bottom:20px;">
        <tr><td style="border:1px solid #ddd;padding:10px 14px;background:#ebf4ff;color:#2c5282;font-weight:bold;width:40%;text-align:right;">ספק</td><td style="border:1px solid #ddd;padding:10px 14px;background:#f9f9f9;text-align:right;">{details.get('supplier', 'לא זוהה')}</td></tr>
        <tr><td style="border:1px solid #ddd;padding:10px 14px;background:#ebf4ff;color:#2c5282;font-weight:bold;text-align:right;">סכום</td><td style="border:1px solid #ddd;padding:10px 14px;background:#f9f9f9;text-align:right;"><strong>{details.get('amount', 'לא זוהה')}</strong></td></tr>
        <tr><td style="border:1px solid #ddd;padding:10px 14px;background:#ebf4ff;color:#2c5282;font-weight:bold;text-align:right;">תאריך</td><td style="border:1px solid #ddd;padding:10px 14px;background:#f9f9f9;text-align:right;">{details.get('date', 'לא זוהה')}</td></tr>
        <tr><td style="border:1px solid #ddd;padding:10px 14px;background:#ebf4ff;color:#2c5282;font-weight:bold;text-align:right;">תיאור</td><td style="border:1px solid #ddd;padding:10px 14px;background:#f9f9f9;text-align:right;">{details.get('description', 'לא זוהה')}</td></tr>
      </table>

      <p style="margin-top:16px;font-size:10pt;color:#999;direction:rtl;text-align:right;">החשבונית המקורית מצורפת למייל זה.</p>
    </div>
  </div>
</body>
</html>"""

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
