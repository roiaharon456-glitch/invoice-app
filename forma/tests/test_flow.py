"""End-to-end tests with a scripted fake Claude and a fake WhatsApp. Run: pytest -q"""
import json
import os
import sys
import tempfile
from types import SimpleNamespace as NS

os.environ.update({
    "DB_PATH": os.path.join(tempfile.mkdtemp(), "t.db"), "OWNER_PHONE": "972500000000", "WA_TOKEN": "x", "WA_PHONE_NUMBER_ID": "1",
    "WA_VERIFY_TOKEN": "vt", "CRON_SECRET": "cs", "SESSION_SECRET": "ss", "PUBLIC_URL": "https://forma.test", "ANTHROPIC_API_KEY": "k",
})
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

import main
from app import agent, auth, reminders, whatsapp
from app import domain as D
from app.tools import run_tool


class FakeLLM:
    """Replays a script: each step is a list of ("tool", name, input) / ("text", str) blocks."""

    def __init__(self, steps):
        self.steps, self.calls = list(steps), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        blocks = self.steps.pop(0)
        content = [NS(type="tool_use", id=f"t{i}", name=b[1], input=b[2]) if b[0] == "tool" else NS(type="text", text=b[1]) for i, b in enumerate(blocks)]
        return NS(stop_reason="tool_use" if any(b[0] == "tool" for b in blocks) else "end_turn", content=content)


PROFILE = {"name": "רועי", "sex": "m", "age": 29, "height": 178, "weight": 82, "lifestyle": "light", "train_days": [0, 2, 4], "equip": "gym", "diet": ["kosher"]}


@pytest.fixture(scope="module")
def repo():
    return main.repo


@pytest.fixture()
def sent(monkeypatch):
    out = []
    monkeypatch.setattr(whatsapp, "send_text", lambda to, text: out.append(("text", to, text)))
    monkeypatch.setattr(whatsapp, "send_template", lambda to, text: out.append(("template", to, text)))
    monkeypatch.setattr(whatsapp, "mark_read_typing", lambda mid: None)
    return out


def test_profile_and_targets(repo):
    r = run_tool(repo, "update_profile", PROFILE)
    assert r["saved"] and r["created"]
    assert r["targets"]["training_day_kcal"] > r["targets"]["rest_day_kcal"]
    assert r["targets"]["protein"] == round(82 * 2.1)
    assert len(r["plan"]) == 3
    p = repo.profile()
    assert p["trainDays"] == [0, 2, 4] and p["reminders"]["enabled"]


def test_meal_water_weight_tools(repo):
    r = run_tool(repo, "log_meal", {"name": "שקשוקה", "items": [{"name": "ביצים", "amount": "2", "kcal": 160, "protein": 13, "carbs": 1, "fat": 11}, {"name": "לחם", "kcal": 140, "protein": 5, "carbs": 26, "fat": 2}]})
    assert r["logged"]["kcal"] == 300 and r["day"]["eaten"]["protein"] == 18
    mid = r["logged"]["id"]
    assert run_tool(repo, "log_water", {"cups": 3, "mode": "add"})["water_cups"] == 3
    assert run_tool(repo, "log_water", {"cups": 2, "mode": "add"})["water_cups"] == 5
    assert run_tool(repo, "delete_meal", {"meal_id": mid})["deleted"]
    assert run_tool(repo, "delete_meal", {"meal_id": "nope"})["error"]
    assert run_tool(repo, "log_weight", {"kg": 81.6})["saved"]["kg"] == 81.6
    assert "error" in run_tool(repo, "log_weight", {"kg": 8})


def test_workout_progression(repo):
    p = repo.profile()
    d = "2026-11-22"  # a Sunday -> first planned session
    w = run_tool(repo, "get_workout", {"date": d})
    assert w["session_index"] == 0 and w["exercises"][0]["name"] == "סקוואט עם מוט"
    first = w["exercises"][0]
    sets = [{"weight_kg": 80, "reps": first_max} for first_max in [10, 10, 10]]
    r = run_tool(repo, "log_workout", {"date": d, "exercises": [{"name": first["name"], "sets": sets}], "finished": True})
    assert r["finished"] and r["volume_kg"] == 2400
    nxt = run_tool(repo, "get_workout", {"date": "2026-11-29"})  # next Sunday: all sets hit the top of the range -> add weight
    assert nxt["exercises"][0]["suggested_weight"] == 82.5
    prog = run_tool(repo, "get_progress", {"days": 30})
    assert prog["personal_records_e1rm"][0]["exercise"] == "סקוואט עם מוט"


def test_agent_loop_runs_tools_and_stores_history(repo):
    llm = FakeLLM([
        [("text", "רושם"), ("tool", "log_meal", {"name": "קוטג׳", "items": [{"name": "קוטג׳ 5%", "kcal": 190, "protein": 22, "carbs": 6, "fat": 10}]})],
        [("text", "נרשם: 190 קק״ל. נשארו עוד *140 ג׳ חלבון*.")],
    ])
    reply = agent.run(repo, "אכלתי קוטג׳", "wa", llm=llm)
    assert "נרשם" in reply
    assert any(m["name"] == "קוטג׳" for m in repo.day(D.today())["meals"])
    # second request carries the tool result back, and the request uses fallbacks + cached system prompt
    second = llm.calls[1]
    assert second["fallbacks"] == "default" and second["system"][0]["cache_control"]
    tool_result = second["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and json.loads(tool_result["content"])["logged"]["kcal"] == 190
    turns = repo.coach()["turns"]
    assert turns[-2]["role"] == "user" and turns[-1]["content"] == reply and turns[-1]["tools"] == ["log_meal"]


def test_history_starts_with_user(repo):
    repo.append_turns({"role": "assistant", "content": "תזכורת", "ch": "wa"})
    msgs = agent.history_messages(repo, limit=1)
    assert msgs == []  # a lone assistant turn is dropped


def test_webhook_text_flow(repo, sent, monkeypatch):
    llm = FakeLLM([[("text", "שלום! מה אכלת היום?")]])
    monkeypatch.setattr(agent, "client", lambda: llm)
    c = TestClient(main.app)
    assert c.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "123"}).text == "123"
    assert c.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "bad", "hub.challenge": "1"}).status_code == 403
    payload = {"entry": [{"changes": [{"value": {"messages": [{"from": "972500000000", "id": "wamid.1", "type": "text", "text": {"body": "היי"}}]}}]}]}
    assert c.post("/webhook", json=payload).status_code == 200
    assert sent == [("text", "972500000000", "שלום! מה אכלת היום?")]
    c.post("/webhook", json=payload)  # duplicate delivery from Meta -> ignored
    assert len(sent) == 1
    stranger = {"entry": [{"changes": [{"value": {"messages": [{"from": "972511111111", "id": "wamid.2", "type": "text", "text": {"body": "hi"}}]}}]}]}
    c.post("/webhook", json=stranger)
    assert len(sent) == 1


def test_webhook_voice_and_image(repo, sent, monkeypatch):
    llm = FakeLLM([[("text", "רשמתי מהקולית")], [("text", "רשמתי מהתמונה")]])
    monkeypatch.setattr(agent, "client", lambda: llm)
    monkeypatch.setattr(whatsapp, "download_media", lambda mid: ("audio/ogg" if mid == "a1" else "image/jpeg", b"\x00\x01"))
    monkeypatch.setattr(main.transcribe, "transcribe", lambda mime, data: "אכלתי שתי ביצים")
    c = TestClient(main.app)
    c.post("/webhook", json={"entry": [{"changes": [{"value": {"messages": [{"from": "972500000000", "id": "wamid.v", "type": "audio", "audio": {"id": "a1"}}]}}]}]})
    c.post("/webhook", json={"entry": [{"changes": [{"value": {"messages": [{"from": "972500000000", "id": "wamid.i", "type": "image", "image": {"id": "i1", "caption": "צהריים"}}]}}]}]})
    assert [s[2] for s in sent] == ["רשמתי מהקולית", "רשמתי מהתמונה"]
    voice_req = llm.calls[0]["messages"][-1]["content"][-1]["text"]
    assert "הודעה קולית: אכלתי שתי ביצים" in voice_req
    img_req = llm.calls[1]["messages"][-1]["content"]
    assert img_req[0]["type"] == "image" and img_req[0]["source"]["media_type"] == "image/jpeg"


def test_signature_check(monkeypatch):
    monkeypatch.setattr(main.config, "WA_APP_SECRET", "sec")
    c = TestClient(main.app)
    assert c.post("/webhook", content=b"{}", headers={"x-hub-signature-256": "sha256=bad"}).status_code == 401
    import hashlib, hmac
    good = "sha256=" + hmac.new(b"sec", b"{}", hashlib.sha256).hexdigest()
    assert c.post("/webhook", content=b"{}", headers={"x-hub-signature-256": good}).status_code == 200


def test_reminders_window_and_once_per_day(repo, sent, monkeypatch):
    from datetime import datetime
    fake_now = datetime(2026, 11, 22, 21, 40, tzinfo=D.config.TZ)  # Sunday evening, a training day
    monkeypatch.setattr(D, "now", lambda: fake_now)
    repo.save_sys("reminders", {})
    repo.save_sys("wa", {"last_inbound": int(fake_now.timestamp() * 1000) - 3600_000})  # inside 24h window
    c = TestClient(main.app)
    assert c.get("/cron/tick", params={"key": "bad"}).status_code == 403
    r = c.get("/cron/tick", params={"key": "cs"}).json()
    assert r["sent"] == ["workout", "evening"] or r["sent"] == ["evening"]
    assert all(kind == "text" for kind, _, _ in sent)
    again = c.get("/cron/tick", params={"key": "cs"}).json()
    assert again["sent"] == []
    # outside the 24h window -> template message, flattened to one line
    repo.save_sys("reminders", {})
    repo.save_sys("wa", {"last_inbound": 0})
    sent.clear()
    c.get("/cron/tick", params={"key": "cs"})
    assert sent and sent[0][0] == "template"


def test_template_payload_is_flattened(monkeypatch):
    posted = []
    monkeypatch.setattr(whatsapp, "_post", lambda payload: posted.append(payload))
    whatsapp.send_template("972500000000", "שורה 1\n• שורה 2\n\nשורה 3")
    param = posted[0]["template"]["components"][0]["parameters"][0]["text"]
    assert "\n" not in param and param == "שורה 1 · • שורה 2 · שורה 3"
    assert posted[0]["template"]["name"] == "forma_update" and posted[0]["template"]["language"]["code"] == "he"


def test_web_api_requires_login_and_link_works(repo):
    c = TestClient(main.app)
    assert c.get("/api/state").status_code == 401
    link = auth.login_link()
    token = link.split("t=")[1]
    r = c.get("/login", params={"t": token}, follow_redirects=False)
    assert r.status_code == 303 and auth.COOKIE in r.headers["set-cookie"]
    c.cookies.set(auth.COOKIE, r.cookies[auth.COOKIE])
    st = c.get("/api/state").json()
    assert st["profile"]["name"] == "רועי" and st["ai"] and st["whatsapp"]
    assert c.put("/api/doc/day/2026-11-20", json={"date": "2026-11-20", "meals": [], "water": 4}).json()["ok"]
    assert repo.day("2026-11-20")["water"] == 4
    assert c.put("/api/doc/sys/seen", json={}).status_code == 400  # internal docs are not writable from the browser
    assert c.put("/api/doc/day/../../x", json={}).status_code in (400, 404)
    assert c.get("/login", params={"t": "link.1.bad"}).status_code == 401


def test_get_app_link_tool(repo):
    r = run_tool(repo, "get_app_link", {}, {"make_link": auth.login_link})
    assert r["link"].startswith("https://forma.test/login?t=")


def test_set_reminders_and_plan(repo):
    assert run_tool(repo, "set_reminders", {"weigh": "7:5"})["error"]
    r = run_tool(repo, "set_reminders", {"weigh": "06:45", "evening": ""})
    assert r["reminders"]["weigh"] == "06:45" and r["reminders"]["evening"] == ""
    plan = {"sessions": [{"name": "A", "focus": "x", "exercises": [{"name": "סקוואט", "sets": 9, "min": 5, "max": 3, "rest": 5, "inc": 2.5, "unit": "kg"}]}]}
    r = run_tool(repo, "set_workout_plan", plan)
    ex = repo.profile()["plan"]["sessions"][0]["exercises"][0]
    assert r["saved"] and ex["sets"] == 6 and ex["max"] >= ex["min"] and ex["rest"] == 30


def test_supabase_store_requests():
    import httpx
    from app.store import SupabaseStore
    seen, rows = [], {}

    def handler(req: httpx.Request):
        seen.append(req)
        q = dict(req.url.params)
        if req.method == "POST":
            b = json.loads(req.content)
            rows[(b["kind"], b["key"])] = b["data"]
            return httpx.Response(201)
        kind = q["kind"].removeprefix("eq.")
        if "key" in q and q["key"].startswith("eq."):
            k = q["key"].removeprefix("eq.")
            return httpx.Response(200, json=[{"data": rows[(kind, k)]}] if (kind, k) in rows else [])
        lo = q.get("key", "gte.").removeprefix("gte.")
        return httpx.Response(200, json=[{"key": k, "data": v} for (kk, k), v in sorted(rows.items()) if kk == kind and k >= lo])

    for key, bearer in (("sb_secret_abc", False), ("eyJhbGciOi.x.y", True)):
        st = SupabaseStore("https://p.supabase.co", key)
        st.http = httpx.Client(transport=httpx.MockTransport(handler), headers=st.http.headers)
        st.put("day", "2026-11-22", {"water": 3})
        st.put("day", "2026-11-23", {"water": 1})
        assert st.get("day", "2026-11-22") == {"water": 3} and st.get("day", "nope") is None
        assert list(st.list("day", "2026-11-23")) == ["2026-11-23"]
        post = next(r for r in seen if r.method == "POST")
        assert post.url.path == "/rest/v1/docs" and "merge-duplicates" in post.headers["prefer"]
        assert seen[-1].headers["apikey"] == key and (("authorization" in seen[-1].headers) == bearer)
        seen.clear()
