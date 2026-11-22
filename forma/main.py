"""Forma server: web app + API + WhatsApp webhook + reminder cron."""
import base64
import json
import logging
import os
import re
import threading

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse

from app import agent, auth, config, reminders, transcribe, whatsapp
from app import domain as D
from app.store import make_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("forma")

app = FastAPI(docs_url=None, redoc_url=None)
repo = D.Repo(make_store())
ROOT = os.path.dirname(os.path.abspath(__file__))
DEV_NO_AUTH = os.environ.get("DEV_NO_AUTH") == "1"


# ---------------- web app ----------------
@app.get("/")
def index():
    return FileResponse(os.path.join(ROOT, "static", "index.html"), headers={"Cache-Control": "no-cache"})


@app.get("/plan_lib.json")
def plan_lib():
    return FileResponse(os.path.join(ROOT, "app", "plan_lib.json"))


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/login")
def login(t: str = ""):
    if not auth.check_token(t, "link"):
        return HTMLResponse('<meta charset="utf-8"><body dir="rtl" style="font-family:sans-serif;padding:24px">הקישור פג תוקף. שלח לסוכן בווטסאפ "קישור לאפליקציה" כדי לקבל קישור חדש.</body>', status_code=401)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(auth.COOKIE, auth.make_token("session", auth.SESSION_TTL), max_age=auth.SESSION_TTL, httponly=True, secure=config.PUBLIC_URL.startswith("https"), samesite="lax")
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(auth.COOKIE)
    return resp


def require_session(request: Request):
    if DEV_NO_AUTH:
        return
    if not auth.check_token(request.cookies.get(auth.COOKIE, ""), "session"):
        raise HTTPException(401, "login required")


KINDS = {"profile": r"main", "weights": r"main", "coach": r"main", "day": r"\d{4}-\d{2}-\d{2}", "log": r"\d{4}-\d{2}-\d{2}_s\d{1,2}"}


@app.get("/api/state", dependencies=[Depends(require_session)])
def state():
    since = D.add_days(D.today(), -150)
    return {
        "profile": repo.profile(),
        "weights": repo.weights(),
        "coach": repo.coach(),
        "days": repo.days(since),
        "logs": repo.logs(since),
        "ai": bool(config.ANTHROPIC_API_KEY),
        "whatsapp": bool(config.WA_TOKEN and config.OWNER_PHONE),
    }


@app.put("/api/doc/{kind}/{key}", dependencies=[Depends(require_session)])
async def put_doc(kind: str, key: str, request: Request):
    if kind not in KINDS or not re.fullmatch(KINDS[kind], key):
        raise HTTPException(400, "bad document path")
    data = await request.json()
    if not isinstance(data, dict) or len(json.dumps(data)) > 250_000:
        raise HTTPException(400, "bad document")
    repo.s.put(kind, key, data)
    return {"ok": True}


@app.delete("/api/doc/{kind}/{key}", dependencies=[Depends(require_session)])
def delete_doc(kind: str, key: str):
    if kind not in KINDS or not re.fullmatch(KINDS[kind], key):
        raise HTTPException(400, "bad document path")
    repo.s.delete(kind, key)
    return {"ok": True}


@app.post("/api/chat", dependencies=[Depends(require_session)])
async def chat(request: Request):
    text = str((await request.json()).get("text", "")).strip()[:2000]
    if not text:
        raise HTTPException(400, "empty")
    reply = await _in_thread(agent.safe_run, repo, text, "app", make_link=auth.login_link)
    return {"reply": reply}


@app.post("/api/estimate", dependencies=[Depends(require_session)])
async def estimate(request: Request):
    text = str((await request.json()).get("text", "")).strip()[:600]
    p = repo.profile() or {}
    diet = ", ".join(D.DIET.get(k, k) for k in p.get("diet") or [])
    prompt = (f"אתה תזונאי. הערך ערכים תזונתיים לארוחה שתוארה. אם לא צוינה כמות, הנח מנה ישראלית מקובלת למבוגר. {('המשתמש: ' + diet + '.') if diet else ''}\n"
              "name: שם קצר לארוחה. לכל פריט: amount = כמות במילים, kcal, ו-p/c/f = חלבון/פחמימות/שומן בגרמים, מספרים שלמים.\n"
              f"התיאור: {text}")
    try:
        return await _in_thread(agent.structured, prompt, agent.MEAL_SCHEMA)
    except Exception as e:
        log.warning("estimate failed: %s", e)
        raise HTTPException(502, "estimate failed")


@app.post("/api/plan", dependencies=[Depends(require_session)])
async def plan(request: Request):
    req = str((await request.json()).get("request", "")).strip()[:400]
    p = repo.profile()
    if not p:
        raise HTTPException(400, "no profile")
    n = len(p.get("trainDays") or [])
    prompt = (f"בנה תוכנית אימוני כוח שבועית ל-Recomp עבור: {D.profile_summary(p, repo.cur_weight(p))}\n"
              f"מספר אימונים בשבוע: {n}. {('בקשות מיוחדות: ' + req) if req else ''}\n"
              f"כללים: בדיוק {n} אימונים. תרגילים מורכבים בתחילת כל אימון, 4–6 תרגילים לאימון, 2–4 סטים, איזון בין דחיפה, משיכה ורגליים לאורך השבוע. "
              f"רק תרגילים שאפשר לבצע עם: {D.EQUIP.get(p.get('equip'), '')}. שמות בעברית, name עד 3 מילים.\n"
              "unit: kg למשקל חיצוני, reps למשקל גוף, sec לתרגיל זמן (min/max בשניות). inc = תוספת משקל בק״ג להתקדמות (0 כש-unit אינו kg). rest בשניות.")
    try:
        return await _in_thread(agent.structured, prompt, agent.PLAN_SCHEMA, "medium")
    except Exception as e:
        log.warning("plan failed: %s", e)
        raise HTTPException(502, "plan failed")


async def _in_thread(fn, *args, **kw):
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(fn, *args, **kw)


# ---------------- WhatsApp ----------------
_seen_lock = threading.Lock()


@app.get("/webhook")
def wa_verify(request: Request):
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and config.WA_VERIFY_TOKEN and q.get("hub.verify_token") == config.WA_VERIFY_TOKEN:
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(403, "verification failed")


@app.post("/webhook")
async def wa_webhook(request: Request, background: BackgroundTasks):
    body = await request.body()
    if not whatsapp.verify_signature(body, request.headers.get("x-hub-signature-256", "")):
        raise HTTPException(401, "bad signature")
    try:
        payload = json.loads(body)
    except ValueError:
        return {"ok": True}
    for m in whatsapp.extract_messages(payload):
        background.add_task(handle_wa_message, m)
    return {"ok": True}  # answer Meta immediately; the reply is sent from the background task


def _first_time(mid: str) -> bool:
    with _seen_lock:
        st = repo.sys("seen")
        ids = st.get("ids", [])
        if mid in ids:
            return False
        st["ids"] = (ids + [mid])[-300:]
        repo.save_sys("seen", st)
        return True


def handle_wa_message(m: dict):
    frm, mid, typ = m.get("from", ""), m.get("id", ""), m.get("type")
    if not config.OWNER_PHONE or frm != config.OWNER_PHONE:
        log.warning("Ignoring WhatsApp message from %s (OWNER_PHONE is %r)", frm, config.OWNER_PHONE)
        return
    if not mid or not _first_time(mid):
        return
    st = repo.sys("wa")
    st["last_inbound"] = int(D.now().timestamp() * 1000)
    repo.save_sys("wa", st)
    whatsapp.mark_read_typing(mid)
    try:
        if typ == "text":
            reply = agent.safe_run(repo, m["text"]["body"], "wa", make_link=auth.login_link)
        elif typ == "image":
            mime, data = whatsapp.download_media(m["image"]["id"])
            if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
                mime = "image/jpeg"
            reply = agent.safe_run(repo, m["image"].get("caption", ""), "wa", images=[(mime, base64.b64encode(data).decode())], make_link=auth.login_link)
        elif typ == "audio":
            mime, data = whatsapp.download_media(m["audio"]["id"])
            try:
                text = transcribe.transcribe(mime, data)
            except Exception:
                log.exception("transcription failed")
                text = ""
            reply = agent.safe_run(repo, text, "wa", note="הודעה קולית", make_link=auth.login_link) if text else "לא הצלחתי לתמלל את ההקלטה. נסה שוב או כתוב לי."
        elif typ in ("interactive", "button"):
            txt = (m.get("button") or {}).get("text") or ((m.get("interactive") or {}).get("button_reply") or {}).get("title") or ""
            reply = agent.safe_run(repo, txt, "wa", make_link=auth.login_link) if txt else "קיבלתי."
        else:
            reply = "אני מבין טקסט, תמונות של אוכל והודעות קוליות."
    except Exception:
        log.exception("handling WhatsApp message failed")
        reply = "משהו השתבש אצלי. נסה שוב בעוד רגע."
    try:
        whatsapp.send_text(frm, reply)
    except Exception:
        log.exception("sending WhatsApp reply failed")


def send_proactive(text: str):
    last = repo.sys("wa").get("last_inbound", 0)
    in_window = D.now().timestamp() * 1000 - last < 23.5 * 3600 * 1000
    (whatsapp.send_text if in_window else whatsapp.send_template)(config.OWNER_PHONE, text)
    repo.append_turns({"role": "assistant", "content": text, "ch": "wa", "t": int(D.now().timestamp() * 1000), "kind": "reminder"})


# ---------------- cron ----------------
@app.api_route("/cron/tick", methods=["GET", "POST"])
def cron_tick(key: str = ""):
    if not config.CRON_SECRET or key != config.CRON_SECRET:
        raise HTTPException(403, "bad key")
    if not (config.WA_TOKEN and config.OWNER_PHONE):
        return {"sent": [], "note": "WhatsApp is not configured"}
    try:
        return {"sent": reminders.tick(repo, send_proactive)}
    except Exception:
        log.exception("cron tick failed")
        return JSONResponse({"error": "tick failed"}, status_code=500)
