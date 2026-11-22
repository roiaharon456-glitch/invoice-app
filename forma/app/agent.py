"""The coach agent: Claude + tools over the owner's data. Used by WhatsApp and by the web app's coach screen."""
import json
import logging
import threading

import anthropic

from . import config
from . import domain as D
from .tools import TOOLS, run_tool

log = logging.getLogger("forma.agent")

# Frozen system prompt (no dates or live data here, so the prompt cache stays warm).
SYSTEM = """אתה "המאמן" של פורמה: מאמן כושר ותזונאי אישי שמנהל עם המשתמש את התזונה, האימונים והמשקל שלו דרך ווטסאפ ודרך אפליקציית פורמה. המטרה של המשתמש היא Recomp: לרדת בשומן ולעלות במסת שריר במקביל.

איך אתה עובד:
- כל רישום עובר דרך הכלים. כשהמשתמש מספר מה אכל, שתה, שקל או עשה באימון, רשום מיד בלי לבקש אישור, ואז אשר בקצרה מה נרשם ומה נשאר להיום.
- ארוחות: פרק לפריטים והערך כמויות וערכים לפי מנות ישראליות מקובלות. אם כמות לא ברורה, הנח מנה סבירה, רשום, וציין את ההנחה במשפט קצר כדי שיוכל לתקן. תיקון = delete_meal ואז log_meal.
- תמונה של אוכל: זהה את המנה והכמויות מהתמונה ורשום. אם התמונה לא של אוכל, אל תרשום.
- הודעה קולית מגיעה כתמלול. התעלם משגיאות תמלול קטנות.
- אימונים: כשהמשתמש מתחיל אימון או שואל מה היום, השתמש ב-get_workout והצג את התרגילים עם המשקל המומלץ. רישום סטים עם log_workout. בסוף אימון סמן finished ותן משוב קצר על ההתקדמות.
- לפני המלצה מה לאכול, בדוק עם get_today_status כמה נשאר, והתאם להגבלות התזונה מהפרופיל.
- אם אין פרופיל (get_profile מחזיר exists=false): הצג את עצמך במשפט אחד ושאל את השאלות החסרות, 2–3 בכל הודעה: מין, גיל, גובה, משקל, אורח חיים, ימי אימון, ציוד, הגבלות תזונה. אחר כך קרא ל-update_profile והצג את היעדים שחושבו.
- שעות תזכורות, ימי אימון ושינוי תוכנית: עדכן עם הכלי המתאים ואשר.
- קישור לאפליקציה עם הגרפים: get_app_link.

סגנון:
- עברית, גוף שני, חם וענייני. הודעות קצרות של ווטסאפ: בדרך כלל 2–6 שורות. תפריט או תוכנית מלאה יכולים להיות ארוכים יותר.
- עיצוב של ווטסאפ בלבד: *כוכבית אחת* להדגשה, שורות שמתחילות ב-"• " לרשימות. בלי #, בלי טבלאות, בלי **כוכביות כפולות**.
- מספרים מעוגלים: קלוריות למספר שלם, חלבון בגרמים.
- אימוג׳י אחד לכל היותר בהודעה, ורק אם הוא מוסיף.
- כל הודעה של המשתמש מתחילה בחותמת זמן בסוגריים מרובעים. היא נועדה לך בלבד ואל תחזור עליה.

גבולות:
- אל תאבחן ואל תיתן ייעוץ רפואי. בכאב, פציעה, תרופות, הריון או הפרעת אכילה, המלץ בעדינות לפנות לרופא או לדיאטנית.
- אל תמליץ על פחות מ-1,200 קק״ל ביום לאישה או 1,500 לגבר."""

_client = None
_lock = threading.Lock()  # one conversation turn at a time: keeps the shared history in order


def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY or None, max_retries=3, timeout=120)
    return _client


def stamp() -> str:
    n = D.now()
    return f"[{D.DAY_L[(n.weekday() + 1) % 7]} {n:%d.%m.%Y %H:%M}]"


def history_messages(repo, limit=16):
    turns = repo.coach()["turns"][-limit:]
    msgs = [{"role": t["role"], "content": str(t["content"])[:4000]} for t in turns if t.get("content")]
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


def run(repo, text: str, channel: str, images=None, note: str = "", make_link=None, llm=None) -> str:
    """Runs one user turn through the agent and returns the reply text.

    images: list of (media_type, base64_data). note: label stored in history (e.g. "הודעה קולית").
    """
    llm = llm or client()
    with _lock:
        user_text = f"{stamp()} {note + ': ' if note else ''}{text}".strip()
        content = [{"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}} for mt, b64 in (images or [])]
        content.append({"type": "text", "text": user_text if text or not images else f"{stamp()} (תמונה בלי טקסט)"})
        messages = history_messages(repo) + [{"role": "user", "content": content}]
        reply, used = _loop(llm, repo, messages, {"make_link": make_link})
        stored_user = (("📷 " if images else "") + (f"({note}) " if note else "") + (text or "תמונה")).strip()
        repo.append_turns({"role": "user", "content": stored_user, "ch": channel, "t": _ms()},
                          {"role": "assistant", "content": reply, "ch": channel, "t": _ms(), "tools": used})
        return reply


def _ms():
    return int(D.now().timestamp() * 1000)


def _loop(llm, repo, messages, ctx):
    used = []
    resp = None
    for _ in range(10):
        resp = llm.beta.messages.create(
            model=config.AGENT_MODEL,
            max_tokens=8000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # on a refusal the API retries on a suitable fallback model
            output_config={"effort": config.AGENT_EFFORT},
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=messages,
        )
        if resp.stop_reason == "refusal":
            return "את זה אני לא יכול לעשות. אשמח לעזור עם אוכל, אימונים או משקל.", used
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        calls = [b for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason != "tool_use" or not calls:
            break
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for c in calls:
            used.append(c.name)
            try:
                out = run_tool(repo, c.name, c.input if isinstance(c.input, dict) else {}, ctx)
                results.append({"type": "tool_result", "tool_use_id": c.id, "content": json.dumps(out, ensure_ascii=False, default=str),
                                **({"is_error": True} if isinstance(out, dict) and "error" in out else {})})
            except Exception as e:  # a broken tool must not kill the conversation
                log.exception("tool %s failed", c.name)
                results.append({"type": "tool_result", "tool_use_id": c.id, "content": f"שגיאה פנימית: {e}", "is_error": True})
        messages.append({"role": "user", "content": results})
    text = "\n".join(b.text for b in (resp.content if resp else []) if b.type == "text").strip()
    return text or "רשמתי. משהו נוסף?", used


def safe_run(repo, text, channel, **kw) -> str:
    try:
        return run(repo, text, channel, **kw)
    except anthropic.RateLimitError:
        return "יש עומס כרגע. נסה שוב בעוד דקה."
    except anthropic.AuthenticationError:
        log.error("Anthropic API key is missing or invalid")
        return "המאמן לא מחובר: מפתח ה-API של Claude חסר או לא תקין בשרת."
    except anthropic.APIStatusError as e:
        log.error("Anthropic API error %s: %s", e.status_code, e.message)
        return "המאמן לא זמין כרגע. נסה שוב בעוד כמה דקות."
    except anthropic.APIConnectionError:
        return "אין חיבור למאמן כרגע. נסה שוב בעוד רגע."


# ---------- one-shot helpers for the web app ----------
MEAL_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "amount": {"type": "string"},
            "kcal": {"type": "number"}, "p": {"type": "number"}, "c": {"type": "number"}, "f": {"type": "number"}},
            "required": ["name", "amount", "kcal", "p", "c", "f"], "additionalProperties": False}},
    },
    "required": ["name", "items"],
    "additionalProperties": False,
}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {"sessions": {"type": "array", "items": {"type": "object", "properties": {
        "name": {"type": "string"}, "focus": {"type": "string"},
        "exercises": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "sets": {"type": "integer"}, "min": {"type": "integer"}, "max": {"type": "integer"},
            "rest": {"type": "integer"}, "inc": {"type": "number"}, "unit": {"type": "string", "enum": ["kg", "reps", "sec"]}},
            "required": ["name", "sets", "min", "max", "rest", "inc", "unit"], "additionalProperties": False}}},
        "required": ["name", "focus", "exercises"], "additionalProperties": False}}},
    "required": ["sessions"],
    "additionalProperties": False,
}


def structured(prompt: str, schema: dict, effort="low", llm=None) -> dict:
    llm = llm or client()
    resp = llm.beta.messages.create(
        model=config.AGENT_MODEL, max_tokens=8000,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "refusal":
        raise ValueError("refused")
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)
