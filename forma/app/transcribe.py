"""Voice-note transcription with Gemini (Claude does not take audio input)."""
import base64
import logging

import httpx

from . import config

log = logging.getLogger("forma.stt")


def transcribe(mime: str, audio: bytes) -> str:
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": mime or "audio/ogg", "data": base64.b64encode(audio).decode()}},
        {"text": "תמלל את ההקלטה מילה במילה, בשפה שבה היא נאמרה (בדרך כלל עברית). החזר רק את התמלול, בלי הקדמה."},
    ]}]}
    r = httpx.post(url, json=body, headers={"x-goog-api-key": config.GEMINI_API_KEY}, timeout=60)
    if r.status_code >= 400:
        log.error("Gemini transcription failed %s: %s", r.status_code, r.text[:300])
        r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return " ".join(p.get("text", "") for p in parts).strip()
