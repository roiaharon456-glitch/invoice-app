"""Login without passwords: the WhatsApp agent sends a short-lived signed link; opening it sets a long-lived session cookie."""
import base64
import hashlib
import hmac
import time

from . import config

COOKIE = "forma_session"
LINK_TTL = 15 * 60
SESSION_TTL = 90 * 24 * 3600


def _sign(payload: str) -> str:
    mac = hmac.new(config.SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")


def make_token(kind: str, ttl: int) -> str:
    payload = f"{kind}.{int(time.time()) + ttl}"
    return f"{payload}.{_sign(payload)}"


def check_token(token: str, kind: str) -> bool:
    if not config.SESSION_SECRET or not token:
        return False
    try:
        k, exp, sig = token.split(".")
    except ValueError:
        return False
    payload = f"{k}.{exp}"
    return k == kind and hmac.compare_digest(_sign(payload), sig) and int(exp) > time.time()


def login_link() -> str | None:
    if not (config.PUBLIC_URL and config.SESSION_SECRET):
        return None
    return f"{config.PUBLIC_URL}/login?t={make_token('link', LINK_TTL)}"
