"""Scheduled messages. /cron/tick calls tick() every few minutes; each reminder is sent at most once a day,
and only within 3 hours of its time (so a sleeping server never sends a stale morning reminder at night)."""
from datetime import timedelta

from . import domain as D
from .domain import num

PROTEIN_FOODS = [
    ("200 ג׳ קוטג׳ 5%", 22, {"vegan", "lactose"}),
    ("150 ג׳ חזה עוף", 46, {"vegetarian", "vegan"}),
    ("גביע יוגורט חלבון", 20, {"vegan", "lactose"}),
    ("קופסת טונה במים", 26, {"vegetarian", "vegan", "nofish"}),
    ("3 ביצים", 19, {"vegan"}),
    ("200 ג׳ טופו", 30, set()),
    ("כוס עדשים מבושלות", 18, set()),
]


def _due(now, hm, hours=3):
    try:
        h, m = map(int, hm.split(":"))
    except (ValueError, AttributeError):
        return False
    at = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return at <= now < at + timedelta(hours=hours)


def _hi(p):
    return f", {p['name']}" if p.get("name") else ""


def build(repo, p, kind, d):
    if kind == "weigh":
        if any(x["d"] == d for x in repo.weights()["entries"]):
            return None
        return f"בוקר טוב{_hi(p)} ⚖️\nזמן לשקילה: אחרי שירותים ולפני אוכל. שלח לי רק את המספר."

    if kind == "workout":
        idx = repo.scheduled_idx(p, d)
        logs = repo.logs_on(d)
        if idx is None or any(l.get("finished") for l in logs):
            return None
        log = repo.get_or_new_log(p, d, idx)
        lines = [f"היום *{log['name']}* 💪 ({log['focus']})"]
        for e in log["exercises"]:
            w = e["sets"][0].get("w")
            target = f"{len(e['sets'])}×{e['min']}–{e['max']}" + (f" · {w:g} ק״ג" if isinstance(w, (int, float)) and w else "")
            lines.append(f"• {e['name']}: {target}")
        lines.append("\nכשתסיים, שלח לי את הסטים (למשל: סקוואט 80 3×8) ואני ארשום.")
        return "\n".join(lines)

    if kind == "evening":
        doc = repo.day(d)
        t = repo.targets(d, p)
        s = repo.sums(doc)
        if not doc["meals"]:
            return "לא רשמת היום אוכל. ספר לי בקצרה מה אכלת ואסכם לך את היום."
        lines = [f"סיכום היום: *{s['kcal']:,}* מתוך {t['kcal']:,} קק״ל", f"• חלבון: {s['p']} / {t['p']} ג׳", f"• מים: {doc.get('water', 0)} / {t['cups']} כוסות"]
        left_p = t["p"] - s["p"]
        if left_p > 20:
            diet = set(p.get("diet") or [])
            ideas = [f"{n} ({g} ג׳)" for n, g, bad in PROTEIN_FOODS if not bad & diet][:2]
            lines.append(f"\nחסרים {left_p} ג׳ חלבון. אפשר להשלים עם {' או '.join(ideas)}.")
        elif s["kcal"] > t["kcal"] + 150:
            lines.append("\nעברת קצת את היעד. זה בסדר, מה שקובע זה הממוצע השבועי.")
        else:
            lines.append("\nיום מצוין. ככה בונים שריר ושורפים שומן 👌")
        return "\n".join(lines)

    if kind == "weekly":
        start = D.add_days(d, -6)
        days = repo.days(start)
        logged = [repo.sums(x) for x in days.values() if x.get("meals")]
        done = sum(1 for l in repo.logs(start).values() if l.get("finished"))
        lines = ["*הסיכום השבועי שלך*"]
        if logged:
            lines.append(f"• ממוצע: {round(sum(x['kcal'] for x in logged) / len(logged)):,} קק״ל, {round(sum(x['p'] for x in logged) / len(logged))} ג׳ חלבון ({len(logged)} ימים מתועדים)")
        lines.append(f"• אימונים: {done} מתוך {len(p.get('trainDays') or [])}")
        tr = repo.trend()
        if tr:
            lines.append(f"• משקל מגמה: {tr['weight_trend']} ק״ג ({tr['per_week_kg']:+.2f} לשבוע)")
            if tr["span_days"] >= 14 and tr["weigh_ins"] >= 6:
                pct = tr["per_week_kg"] / tr["weight_trend"] * 100
                if pct > 0.25:
                    lines.append("\nהמשקל עולה מהר מדי ל-Recomp. אני מציע להוריד 100 קק״ל ביום. לעדכן?")
                elif pct < -0.75:
                    lines.append("\nהמשקל יורד מהר מדי ויש סיכון לאבד שריר. אני מציע להוסיף 150 קק״ל ביום. לעדכן?")
                else:
                    lines.append("\nהקצב מצוין ל-Recomp. ממשיכים ככה.")
        return "\n".join(lines)
    return None


def tick(repo, send):
    """send(text) delivers to the owner. Returns the list of reminders sent."""
    p = repo.profile()
    if not p:
        return []
    r = {**D.DEFAULT_REMINDERS, **(p.get("reminders") or {})}
    if not r.get("enabled", True):
        return []
    now = D.now()
    d = now.date().isoformat()
    sent = repo.sys("reminders")
    out = []
    for kind in ("weigh", "workout", "evening", "weekly"):
        hm = r.get(kind)
        if not hm or sent.get(kind) == d or not _due(now, hm):
            continue
        if kind == "weekly" and D.js_weekday(d) != int(num(r.get("weekly_day"))):
            continue
        sent[kind] = d
        repo.save_sys("reminders", sent)
        text = build(repo, p, kind, d)
        if text:
            send(text)
            out.append(kind)
    return out
