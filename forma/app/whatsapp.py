"""WhatsApp Cloud API: webhook signature check, sending, media download."""
import hashlib
import hmac
import logging
import re

import httpx

from . import config

log = logging.getLogger("forma.wa")
GRAPH = "https://graph.facebook.com"
_http = httpx.Client(timeout=30)


def _auth():
    return {"Authorization": f"Bearer {config.WA_TOKEN}"}


def verify_signature(body: bytes, header: str) -> bool:
    if not config.WA_APP_SECRET:
        return True  # not configured (local testing only)
    expected = "sha256=" + hmac.new(config.WA_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")


def _post(payload: dict) -> dict:
    url = f"{GRAPH}/{config.WA_GRAPH_VERSION}/{config.WA_PHONE_NUMBER_ID}/messages"
    r = _http.post(url, json={"messaging_product": "whatsapp", **payload}, headers=_auth())
    if r.status_code >= 400:
        log.error("WhatsApp send failed %s: %s", r.status_code, r.text[:500])
        r.raise_for_status()
    return r.json()


def mark_read_typing(message_id: str):
    try:
        _post({"status": "read", "message_id": message_id, "typing_indicator": {"type": "text"}})
    except Exception:
        pass  # cosmetic only


def split(text: str, limit=3800):
    parts, cur = [], ""
    for para in text.split("\n"):
        if len(cur) + len(para) + 1 > limit and cur:
            parts.append(cur)
            cur = ""
        cur = (cur + "\n" + para) if cur else para
    if cur:
        parts.append(cur)
    return parts or [""]


def send_text(to: str, text: str):
    for part in split(text):
        _post({"to": to, "type": "text", "text": {"body": part, "preview_url": True}})


def send_template(to: str, text: str):
    """Messages outside the 24-hour window must use an approved template with one body variable.
    Template variables cannot contain newlines, so the text is flattened."""
    flat = re.sub(r"\s*\n+\s*", " · ", text).strip()
    flat = re.sub(r" {4,}", "   ", flat)[:1000]
    _post({"to": to, "type": "template", "template": {"name": config.WA_TEMPLATE, "language": {"code": config.WA_TEMPLATE_LANG},
                                                    "components": [{"type": "body", "parameters": [{"type": "text", "text": flat}]}]}})


def download_media(media_id: str):
    """Returns (mime_type, bytes)."""
    meta = _http.get(f"{GRAPH}/{config.WA_GRAPH_VERSION}/{media_id}", headers=_auth())
    meta.raise_for_status()
    info = meta.json()
    data = _http.get(info["url"], headers=_auth())
    data.raise_for_status()
    return info.get("mime_type", "application/octet-stream").split(";")[0].strip(), data.content


def extract_messages(payload: dict):
    """Yields the incoming message objects from a webhook payload (ignores delivery statuses)."""
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for m in (change.get("value") or {}).get("messages", []) or []:
                yield m
