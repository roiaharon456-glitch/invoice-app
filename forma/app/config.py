"""All settings come from environment variables (see .env.example)."""
import os
from zoneinfo import ZoneInfo


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# Claude
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
AGENT_MODEL = env("AGENT_MODEL", "claude-opus-5-5")
AGENT_EFFORT = env("AGENT_EFFORT", "low")  # low keeps WhatsApp replies fast; raise to medium for deeper answers

# Gemini (voice-note transcription only)
GEMINI_API_KEY = env("GEMINI_API_KEY")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")

# WhatsApp Cloud API
WA_TOKEN = env("WA_TOKEN")
WA_PHONE_NUMBER_ID = env("WA_PHONE_NUMBER_ID")
WA_VERIFY_TOKEN = env("WA_VERIFY_TOKEN")
WA_APP_SECRET = env("WA_APP_SECRET")
WA_GRAPH_VERSION = env("WA_GRAPH_VERSION", "v21.0")
WA_TEMPLATE = env("WA_TEMPLATE", "forma_update")
WA_TEMPLATE_LANG = env("WA_TEMPLATE_LANG", "he")
OWNER_PHONE = env("OWNER_PHONE").lstrip("+").replace("-", "").replace(" ", "")

# Storage: Supabase in production, a local SQLite file otherwise
SUPABASE_URL = env("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_KEY = env("SUPABASE_SERVICE_KEY")
DB_PATH = env("DB_PATH", "data/forma.db")

# Web app + cron
SESSION_SECRET = env("SESSION_SECRET")
CRON_SECRET = env("CRON_SECRET")
PUBLIC_URL = env("PUBLIC_URL").rstrip("/")

TZ = ZoneInfo(env("TZ_NAME", "Asia/Jerusalem"))
