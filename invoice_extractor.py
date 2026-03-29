import httpx
import base64
import os
import json
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


def convert_to_jpeg(image_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """ממיר כל תמונה ל-JPEG כדי שGemini יוכל לקרוא אותה"""
    try:
        from PIL import Image
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except Exception:
            pass

        img = Image.open(BytesIO(image_bytes))
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        output = BytesIO()
        img.save(output, format="JPEG", quality=90)
        return output.getvalue(), "image/jpeg"
    except Exception as e:
        logger.warning(f"Image conversion failed: {e}, using original")
        supported = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        mime = content_type if content_type in supported else "image/jpeg"
        return image_bytes, mime


async def extract_invoice_details(image_bytes: bytes, content_type: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set!")
        return {"supplier": "לא זוהה", "amount": "לא זוהה", "date": "לא זוהה", "description": "לא זוהה"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    # המרת התמונה ל-JPEG
    converted_bytes, mime_type = convert_to_jpeg(image_bytes, content_type)
    image_b64 = base64.b64encode(converted_bytes).decode("utf-8")

    prompt = """אתה עוזר לחלץ פרטים מחשבוניות.
חלץ את הפרטים הבאים מהחשבונית ותחזיר JSON בלבד (ללא טקסט נוסף):
{
  "supplier": "שם הספק/העסק",
  "amount": "סכום כולל עם מטבע (לדוגמה: 150.00 ₪)",
  "date": "תאריך החשבונית",
  "description": "תיאור קצר של הקנייה"
}
אם לא ניתן לקרוא שדה מסוים, השתמש ב-"לא ידוע"."""

    payload = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, json=payload)
            logger.info(f"Gemini status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Gemini error: {response.text}")
                return {"supplier": "לא זוהה", "amount": "לא זוהה", "date": "לא זוהה", "description": "לא זוהה"}

            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.info(f"Gemini response: {text[:200]}")

            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            return json.loads(text.strip())

    except Exception as e:
        logger.error(f"Invoice extraction error: {e}")
        return {"supplier": "לא זוהה", "amount": "לא זוהה", "date": "לא זוהה", "description": "לא זוהה"}
