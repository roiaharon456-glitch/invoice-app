import google.generativeai as genai
import base64
import os
import json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")


async def extract_invoice_details(image_bytes: bytes, content_type: str) -> dict:
    image_part = {
        "mime_type": content_type if content_type in [
            "image/jpeg", "image/png", "image/gif", "image/webp"
        ] else "image/jpeg",
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }

    prompt = """אתה עוזר לחלץ פרטים מחשבוניות.
חלץ את הפרטים הבאים מהחשבונית ותחזיר JSON בלבד (ללא טקסט נוסף):
{
  "supplier": "שם הספק/העסק",
  "amount": "סכום כולל עם מטבע (לדוגמה: 150.00 ₪)",
  "date": "תאריך החשבונית",
  "description": "תיאור קצר של הקנייה"
}
אם לא ניתן לקרוא שדה מסוים, השתמש ב-"לא ידוע"."""

    response = model.generate_content([image_part, prompt])
    text = response.text.strip()

    try:
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception:
        return {
            "supplier": "לא זוהה",
            "amount": "לא זוהה",
            "date": "לא זוהה",
            "description": "לא זוהה",
        }
