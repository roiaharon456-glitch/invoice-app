"""Business logic shared by the WhatsApp agent, reminders and API.

The formulas mirror the ones in static/index.html (calcTargets, movingAvg, suggest) - keep them in sync.
"""
import copy
import json
import math
import os
import secrets
from datetime import date, datetime, timedelta

from . import config

LIFE = {
    "sed": (1.2, "ישיבה רוב היום"),
    "light": (1.3, "פעילות קלה"),
    "active": (1.45, "עבודה פעילה"),
    "very": (1.6, "עבודה פיזית"),
}
EQUIP = {"gym": "חדר כושר", "dumbbells": "בית עם משקולות", "bodyweight": "בלי ציוד"}
DIET = {"kosher": "כשר", "vegetarian": "צמחוני", "vegan": "טבעוני", "gluten": "ללא גלוטן", "lactose": "ללא לקטוז", "nofish": "ללא דגים"}
DAY_L = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]  # index = JS getDay (0 = Sunday)

with open(os.path.join(os.path.dirname(__file__), "plan_lib.json"), encoding="utf8") as f:
    PLAN_LIB = json.load(f)

DEFAULT_REMINDERS = {"enabled": True, "weigh": "07:30", "workout": "16:30", "evening": "21:30", "weekly_day": 5, "weekly": "10:00"}


def now() -> datetime:
    return datetime.now(config.TZ)


def today() -> str:
    return now().date().isoformat()


def parse(d: str) -> date:
    return date.fromisoformat(d)


def add_days(d: str, n: int) -> str:
    return (parse(d) + timedelta(days=n)).isoformat()


def js_weekday(d: str) -> int:
    """0 = Sunday ... 6 = Saturday (same as JS getDay)."""
    return (parse(d).weekday() + 1) % 7


def num(v) -> float:
    try:
        x = float(str(v).replace(",", "."))
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def r10(n: float) -> int:
    return int(round(n / 10.0) * 10)


def gen_plan(n: int, equip: str) -> dict:
    lib = PLAN_LIB["lib"].get(equip) or PLAN_LIB["lib"]["gym"]
    keys = PLAN_LIB["splits"][str(max(1, min(6, n)))]
    sessions = []
    for k in keys:
        t = PLAN_LIB["templates"][k]
        sessions.append({"name": t["name"], "focus": t["focus"], "exercises": [copy.deepcopy(lib[p]) for p in t["pats"]]})
    return {"source": "auto", "sessions": sessions}


def calc_targets(p: dict, w: float, training: bool) -> dict:
    bmr = 10 * w + 6.25 * num(p.get("height")) - 5 * num(p.get("age")) + (-161 if p.get("sex") == "f" else 5)
    fac = LIFE.get(p.get("lifestyle"), (1.3,))[0] + len(p.get("trainDays") or []) * 0.035
    tdee = bmr * fac
    adj = num(p.get("kcalAdjust"))
    kcal = r10(tdee + adj if training else tdee * 0.85 + adj)
    pr, f = round(w * 2.1), round(w * 0.8)
    c = max(50, round((kcal - pr * 4 - f * 9) / 4))
    cups = math.ceil(w * 35 / 250) + (2 if training else 0)
    return {"kcal": kcal, "p": pr, "c": c, "f": f, "cups": cups, "tdee": round(tdee), "training": training}


def moving_avg(entries: list) -> list:
    e = sorted(entries, key=lambda x: x["d"])
    out = []
    for i, x in enumerate(e):
        s = n = 0
        j = i
        while j >= 0 and (parse(x["d"]) - parse(e[j]["d"])).days < 7:
            s += e[j]["kg"]
            n += 1
            j -= 1
        out.append({"d": x["d"], "kg": x["kg"], "ma": s / n})
    return out


class Repo:
    """Typed access to the documents for the single owner of this deployment."""

    def __init__(self, store):
        self.s = store

    # ----- raw docs -----
    def profile(self):
        return self.s.get("profile", "main")

    def save_profile(self, p):
        self.s.put("profile", "main", p)

    def weights(self):
        w = self.s.get("weights", "main") or {}
        w.setdefault("entries", [])
        w.setdefault("measures", [])
        return w

    def save_weights(self, w):
        self.s.put("weights", "main", w)

    def day(self, d):
        doc = self.s.get("day", d) or {"date": d, "meals": [], "water": 0}
        doc.setdefault("meals", [])
        doc.setdefault("water", 0)
        return doc

    def save_day(self, doc):
        self.s.put("day", doc["date"], doc)

    def days(self, since):
        return self.s.list("day", since)

    def logs(self, since=None):
        return self.s.list("log", since)

    def save_log(self, log):
        self.s.put("log", log["id"], log)

    def coach(self):
        c = self.s.get("coach", "main") or {}
        c.setdefault("turns", [])
        return c

    def append_turns(self, *turns):
        c = self.coach()
        c["turns"] = (c["turns"] + list(turns))[-40:]
        self.s.put("coach", "main", c)

    def sys(self, name):
        return self.s.get("sys", name) or {}

    def save_sys(self, name, data):
        self.s.put("sys", name, data)

    # ----- derived -----
    def cur_weight(self, profile=None):
        e = self.weights()["entries"]
        if e:
            return moving_avg(e)[-1]["ma"]
        p = profile or self.profile() or {}
        return num(p.get("weight")) or 75.0

    def scheduled_idx(self, p, d):
        sessions = (p.get("plan") or {}).get("sessions") or []
        if not sessions:
            return None
        days = sorted(p.get("trainDays") or [])
        wd = js_weekday(d)
        return days.index(wd) % len(sessions) if wd in days else None

    def logs_on(self, d):
        return [l for l in self.s.list("log", d).values() if l.get("date") == d]

    def is_training(self, p, d):
        return self.scheduled_idx(p, d) is not None or bool(self.logs_on(d))

    def targets(self, d, p=None):
        p = p or self.profile()
        return calc_targets(p, self.cur_weight(p), self.is_training(p, d))

    @staticmethod
    def sums(doc):
        t = {"kcal": 0.0, "p": 0.0, "c": 0.0, "f": 0.0}
        for m in doc.get("meals", []):
            for k in t:
                t[k] += num(m.get(k))
        return {k: round(v) for k, v in t.items()}

    def trend(self):
        m = moving_avg(self.weights()["entries"])
        if len(m) < 2:
            return None
        last, ref = m[-1], m[0]
        for x in m:
            if (parse(last["d"]) - parse(x["d"])).days >= 14:
                ref = x
        span = (parse(last["d"]) - parse(ref["d"])).days
        change = last["ma"] - ref["ma"]
        per_week = change / span * 7 if span > 0 else 0
        return {"weight_trend": round(last["ma"], 1), "change_kg": round(change, 2), "per_week_kg": round(per_week, 2), "span_days": span, "weigh_ins": len(m)}

    def suggest(self, ex, before):
        past = sorted((l for l in self.logs().values() if l.get("date", "") < before), key=lambda l: l["date"], reverse=True)
        for l in past:
            e = next((x for x in l.get("exercises", []) if x["name"] == ex["name"]), None)
            if not e:
                continue
            done = [s for s in e["sets"] if s.get("done") and num(s.get("r")) > 0]
            if not done:
                continue
            w = max(num(s.get("w")) for s in done)
            min_r = min(num(s.get("r")) for s in done)
            if ex["unit"] == "kg":
                if len(done) >= ex["sets"] and min_r >= ex["max"] and ex["inc"] > 0:
                    return {"w": round(w + ex["inc"], 2), "r": ex["min"], "hint": {"type": "up", "text": f"+{ex['inc']} ק״ג · כל הסטים הגיעו ל-{ex['max']}"}}
                r = int(min(ex["max"], min_r + 1))
                return {"w": w, "r": r, "hint": {"type": "reps", "text": f"{w:g} ק״ג · נסה {r} חזרות"}}
            r = int(min_r + (5 if ex["unit"] == "sec" else 1))
            ul = "שניות" if ex["unit"] == "sec" else "חזרות"
            return {"w": "", "r": r, "hint": {"type": "up" if min_r >= ex["max"] else "reps", "text": f"יעד: {r} {ul}"}}
        return {"w": "", "r": "", "hint": {"type": "new", "text": "פעם ראשונה · בחר משקל שמשאיר 2 חזרות ברזרבה" if ex["unit"] == "kg" else "פעם ראשונה · עצור 2 חזרות לפני כשל"}}

    def get_or_new_log(self, p, d, idx):
        lid = f"{d}_s{idx}"
        existing = self.s.get("log", lid)
        if existing:
            return existing
        ses = p["plan"]["sessions"][idx]
        exs = []
        for ex in ses["exercises"]:
            sg = self.suggest(ex, d)
            exs.append({**{k: ex[k] for k in ("name", "unit", "min", "max", "rest", "inc")}, "hint": sg["hint"],
                        "sets": [{"w": sg["w"], "r": sg["r"], "done": False} for _ in range(ex["sets"])]})
        return {"id": lid, "date": d, "idx": idx, "name": ses["name"], "focus": ses.get("focus", ""), "started": None, "finished": None, "exercises": exs}

    def streak(self):
        d = today()
        since = add_days(d, -400)
        days = self.days(since)
        logs = self.logs(since)
        finished = {l["date"] for l in logs.values() if l.get("finished")}

        def has(x):
            return bool((days.get(x) or {}).get("meals")) or x in finished

        if not has(d):
            d = add_days(d, -1)
        n = 0
        while has(d) and n < 400:
            n += 1
            d = add_days(d, -1)
        return n


def new_id(prefix="m"):
    return prefix + secrets.token_hex(4)


def profile_summary(p: dict, w: float) -> str:
    diet = ", ".join(DIET.get(k, k) for k in p.get("diet") or []) or "אין"
    days = ", ".join(DAY_L[i] for i in sorted(p.get("trainDays") or []))
    return (f"{'אישה' if p.get('sex') == 'f' else 'גבר'}, גיל {p.get('age')}, גובה {p.get('height')} ס״מ, משקל מגמה {w:.1f} ק״ג. "
            f"אורח חיים: {LIFE.get(p.get('lifestyle'), (0, '?'))[1]}. מטרה: Recomp. ימי אימון: {days}. ציוד: {EQUIP.get(p.get('equip'), '?')}. "
            f"הגבלות: {diet}." + (f" לא אוהב: {p['dislikes']}." if p.get("dislikes") else ""))
