"""Tools the agent can call. Each returns a JSON-serialisable dict that goes back to Claude."""
from . import domain as D
from .domain import num

DATE = {"type": "string", "description": "תאריך בפורמט YYYY-MM-DD. ברירת מחדל: היום."}

TOOLS = [
    {
        "name": "get_today_status",
        "description": "מחזיר את מצב היום: יעדים (קלוריות, חלבון, פחמימות, שומן, מים), כמה נאכל, כמה נשאר, רשימת הארוחות עם המזהים שלהן, מים, האם יום אימון ומצב האימון. השתמש לפני שאתה ממליץ מה לאכול או עונה על 'כמה נשאר'.",
        "input_schema": {"type": "object", "properties": {"date": DATE}, "additionalProperties": False},
    },
    {
        "name": "log_meal",
        "description": "רושם ארוחה ביומן. פרק את הארוחה לפריטים והערך לכל פריט כמות, קלוריות וגרמים של חלבון, פחמימות ושומן לפי מנות ישראליות מקובלות. מחזיר את סיכום היום אחרי הרישום.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "שם קצר לארוחה, למשל 'שקשוקה ולחם'"},
                "items": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "amount": {"type": "string", "description": "כמות במילים, למשל '2 יחידות' או '150 גרם'"},
                    "kcal": {"type": "number"}, "protein": {"type": "number"}, "carbs": {"type": "number"}, "fat": {"type": "number"}},
                    "required": ["name", "kcal", "protein", "carbs", "fat"]}},
                "date": DATE,
                "time": {"type": "string", "description": "שעה HH:MM. ברירת מחדל: עכשיו."},
            },
            "required": ["name", "items"],
        },
    },
    {
        "name": "delete_meal",
        "description": "מוחק ארוחה מהיומן לפי המזהה שלה (מ-get_today_status). לתיקון ארוחה: מחק ורשום מחדש.",
        "input_schema": {"type": "object", "properties": {"meal_id": {"type": "string"}, "date": DATE}, "required": ["meal_id"]},
    },
    {
        "name": "log_water",
        "description": "מעדכן כוסות מים (250 מ״ל לכוס). mode=add מוסיף, mode=set קובע את הסך.",
        "input_schema": {"type": "object", "properties": {"cups": {"type": "integer"}, "mode": {"type": "string", "enum": ["add", "set"]}, "date": DATE}, "required": ["cups", "mode"]},
    },
    {
        "name": "log_weight",
        "description": "שומר שקילה בק״ג ומחזיר את מגמת המשקל (ממוצע נע 7 ימים, קצב שבועי).",
        "input_schema": {"type": "object", "properties": {"kg": {"type": "number"}, "date": DATE}, "required": ["kg"]},
    },
    {
        "name": "log_measurements",
        "description": "שומר מדידות היקפים בס״מ. מלא רק את מה שנמסר.",
        "input_schema": {"type": "object", "properties": {"waist": {"type": "number"}, "chest": {"type": "number"}, "arm": {"type": "number"}, "hip": {"type": "number"}, "date": DATE}},
    },
    {
        "name": "get_workout",
        "description": "מחזיר את האימון לתאריך: התרגילים, טווחי חזרות, המשקל המומלץ לפי האימון הקודם (התקדמות הדרגתית), מה כבר נרשם היום, ולוח השבוע. אם אין אימון מתוכנן, מחזיר את רשימת האימונים בתוכנית.",
        "input_schema": {"type": "object", "properties": {"date": DATE, "session_index": {"type": "integer", "description": "לבחירת אימון אחר מהתוכנית (0 = הראשון)."}}},
    },
    {
        "name": "log_workout",
        "description": "רושם סטים שבוצעו. שמות התרגילים צריכים להתאים לשמות בתוכנית (מ-get_workout) כשאפשר. סטים חדשים מתווספים או מחליפים את מה שנרשם לאותו תרגיל. finished=true מסמן שהאימון הסתיים.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": DATE,
                "session_index": {"type": "integer", "description": "ברירת מחדל: האימון המתוכנן להיום."},
                "exercises": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"},
                    "sets": {"type": "array", "items": {"type": "object", "properties": {"weight_kg": {"type": "number"}, "reps": {"type": "number", "description": "חזרות, או שניות בתרגיל זמן"}}, "required": ["reps"]}}},
                    "required": ["name", "sets"]}},
                "finished": {"type": "boolean"},
            },
            "required": ["exercises"],
        },
    },
    {
        "name": "get_progress",
        "description": "סיכום לתקופה: מגמת משקל, ממוצע קלוריות וחלבון ביום, אימונים שבוצעו, שיאים אישיים, היקפים, והמלצה לעדכון יעד הקלוריות.",
        "input_schema": {"type": "object", "properties": {"days": {"type": "integer", "description": "כמה ימים אחורה, ברירת מחדל 7"}}},
    },
    {
        "name": "get_profile",
        "description": "מחזיר את הפרופיל: פרטים אישיים, ימי אימון, ציוד, הגבלות תזונה, תוכנית האימונים ושעות התזכורות. מחזיר exists=false אם עוד לא הוגדר.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "update_profile",
        "description": "יוצר או מעדכן את הפרופיל. ביצירה ראשונה חובה: sex, age, height, weight, lifestyle, train_days, equip. שינוי בימי האימון או בציוד בונה תוכנית בסיסית חדשה.",
        "input_schema": {"type": "object", "properties": {
            "name": {"type": "string"}, "sex": {"type": "string", "enum": ["m", "f"]}, "age": {"type": "number"}, "height": {"type": "number", "description": "ס״מ"},
            "weight": {"type": "number", "description": "ק״ג"},
            "lifestyle": {"type": "string", "enum": ["sed", "light", "active", "very"], "description": "sed=ישיבה רוב היום, light=פעילות קלה, active=עבודה פעילה, very=עבודה פיזית"},
            "train_days": {"type": "array", "items": {"type": "integer"}, "description": "ימי אימון: 0=ראשון ... 6=שבת"},
            "equip": {"type": "string", "enum": ["gym", "dumbbells", "bodyweight"]},
            "diet": {"type": "array", "items": {"type": "string", "enum": list(D.DIET.keys())}},
            "dislikes": {"type": "string"},
            "kcal_adjust": {"type": "number", "description": "תוספת או הפחתה קבועה ליעד הקלוריות היומי"},
        }},
    },
    {
        "name": "set_workout_plan",
        "description": "מחליף את תוכנית האימונים. מספר האימונים צריך להתאים למספר ימי האימון. unit: kg=משקל חיצוני, reps=משקל גוף, sec=תרגיל זמן. inc=תוספת משקל להתקדמות.",
        "input_schema": {"type": "object", "properties": {"sessions": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "focus": {"type": "string"},
            "exercises": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "sets": {"type": "integer"}, "min": {"type": "integer"}, "max": {"type": "integer"},
                "rest": {"type": "integer"}, "inc": {"type": "number"}, "unit": {"type": "string", "enum": ["kg", "reps", "sec"]}},
                "required": ["name", "sets", "min", "max", "rest", "inc", "unit"]}}},
            "required": ["name", "focus", "exercises"]}}}, "required": ["sessions"]},
    },
    {
        "name": "set_reminders",
        "description": "משנה את התזכורות היזומות. שעות בפורמט HH:MM, או ריק כדי לכבות תזכורת מסוימת. weekly_day: 0=ראשון ... 6=שבת.",
        "input_schema": {"type": "object", "properties": {
            "enabled": {"type": "boolean"}, "weigh": {"type": "string"}, "workout": {"type": "string"}, "evening": {"type": "string"},
            "weekly_day": {"type": "integer"}, "weekly": {"type": "string"}}},
    },
    {
        "name": "get_app_link",
        "description": "מחזיר קישור כניסה אישי לאפליקציה (תקף 15 דקות). השתמש כשהמשתמש מבקש את האפליקציה, את הגרפים או קישור.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _date(inp):
    d = (inp.get("date") or "").strip()
    try:
        return D.parse(d).isoformat() if d else D.today()
    except ValueError:
        return D.today()


def _status(repo, p, d):
    doc = repo.day(d)
    t = repo.targets(d, p)
    s = repo.sums(doc)
    idx = repo.scheduled_idx(p, d)
    logs = repo.logs_on(d)
    workout = None
    if logs:
        l = logs[0]
        done = sum(1 for e in l["exercises"] for x in e["sets"] if x.get("done"))
        workout = {"name": l["name"], "sets_done": done, "finished": bool(l.get("finished"))}
    elif idx is not None:
        workout = {"name": p["plan"]["sessions"][idx]["name"], "sets_done": 0, "finished": False}
    return {
        "date": d, "weekday": D.DAY_L[D.js_weekday(d)], "training_day": t["training"],
        "targets": {"kcal": t["kcal"], "protein": t["p"], "carbs": t["c"], "fat": t["f"], "water_cups": t["cups"]},
        "eaten": {"kcal": s["kcal"], "protein": s["p"], "carbs": s["c"], "fat": s["f"]},
        "remaining": {"kcal": t["kcal"] - s["kcal"], "protein": t["p"] - s["p"], "carbs": t["c"] - s["c"], "fat": t["f"] - s["f"]},
        "water_cups": doc.get("water", 0),
        "meals": [{"id": m["id"], "time": m.get("t", ""), "name": m["name"], "kcal": round(num(m["kcal"])), "protein": round(num(m["p"]))} for m in doc["meals"]],
        "workout": workout,
    }


def _need_profile(p):
    return None if p else {"error": "אין עדיין פרופיל. שאל את המשתמש על הפרטים החסרים וקרא ל-update_profile."}


def run_tool(repo, name, inp, ctx=None):
    ctx = ctx or {}
    p = repo.profile()
    if name == "get_profile":
        if not p:
            return {"exists": False}
        return {"exists": True, "summary": D.profile_summary(p, repo.cur_weight(p)), "profile": {k: v for k, v in p.items() if k not in ("favorites",)},
                "reminders": p.get("reminders") or D.DEFAULT_REMINDERS}
    if name == "update_profile":
        return _update_profile(repo, p, inp)
    if name == "get_app_link":
        link = ctx.get("make_link", lambda: None)()
        return {"link": link} if link else {"error": "כתובת האתר (PUBLIC_URL) לא הוגדרה בשרת."}
    if (err := _need_profile(p)):
        return err

    if name == "get_today_status":
        return _status(repo, p, _date(inp))

    if name == "log_meal":
        d = _date(inp)
        items = []
        for it in (inp.get("items") or [])[:20]:
            items.append({"name": str(it.get("name", ""))[:60], "amount": str(it.get("amount", ""))[:40],
                          "kcal": max(0, num(it.get("kcal"))), "p": max(0, num(it.get("protein"))), "c": max(0, num(it.get("carbs"))), "f": max(0, num(it.get("fat")))})
        if not items:
            return {"error": "אין פריטים לרישום."}
        tot = {k: round(sum(i[k] for i in items)) for k in ("kcal", "p", "c", "f")}
        doc = repo.day(d)
        t_str = (inp.get("time") or "").strip()[:5] or (D.now().strftime("%H:%M") if d == D.today() else "")
        meal = {"id": D.new_id(), "t": t_str, "name": str(inp.get("name") or items[0]["name"])[:60], **tot, "items": items, "src": "wa"}
        doc["meals"].append(meal)
        repo.save_day(doc)
        st = _status(repo, p, d)
        return {"logged": {"id": meal["id"], "name": meal["name"], "kcal": tot["kcal"], "protein": tot["p"], "carbs": tot["c"], "fat": tot["f"]}, "day": st}

    if name == "delete_meal":
        d = _date(inp)
        doc = repo.day(d)
        before = len(doc["meals"])
        doc["meals"] = [m for m in doc["meals"] if m["id"] != inp.get("meal_id")]
        if len(doc["meals"]) == before:
            return {"error": "לא נמצאה ארוחה עם המזהה הזה בתאריך הזה."}
        repo.save_day(doc)
        return {"deleted": True, "day": _status(repo, p, d)}

    if name == "log_water":
        d = _date(inp)
        doc = repo.day(d)
        cups = int(num(inp.get("cups")))
        doc["water"] = max(0, (doc.get("water", 0) + cups) if inp.get("mode") == "add" else cups)
        repo.save_day(doc)
        return {"water_cups": doc["water"], "target_cups": repo.targets(d, p)["cups"]}

    if name == "log_weight":
        kg = num(inp.get("kg"))
        if not 30 <= kg <= 300:
            return {"error": "משקל לא סביר. בקש מהמשתמש לבדוק."}
        d = _date(inp)
        w = repo.weights()
        w["entries"] = sorted([x for x in w["entries"] if x["d"] != d] + [{"d": d, "kg": round(kg, 1)}], key=lambda x: x["d"])
        repo.save_weights(w)
        return {"saved": {"date": d, "kg": round(kg, 1)}, "trend": repo.trend()}

    if name == "log_measurements":
        d = _date(inp)
        e = {k: round(num(inp[k]), 1) for k in ("waist", "chest", "arm", "hip") if num(inp.get(k)) > 0}
        if not e:
            return {"error": "לא נמסרו מדידות."}
        w = repo.weights()
        ex = next((x for x in w["measures"] if x["d"] == d), None)
        if ex:
            ex.update(e)
        else:
            w["measures"].append({"d": d, **e})
        repo.save_weights(w)
        first = w["measures"][0]
        since = {k: round(e[k] - first[k], 1) for k in e if k in first} if first["d"] != d else {}
        return {"saved": e, "change_since_first_measure": since, "first_measure_date": first["d"]}

    if name == "get_workout":
        d = _date(inp)
        sessions = p["plan"]["sessions"]
        idx = inp.get("session_index")
        logs = repo.logs_on(d)
        if idx is None:
            idx = logs[0]["idx"] if logs else repo.scheduled_idx(p, d)
        days = sorted(p.get("trainDays") or [])
        week = {D.DAY_L[wd]: sessions[days.index(wd) % len(sessions)]["name"] if wd in days else "מנוחה" for wd in range(7)}
        if idx is None or not 0 <= int(idx) < len(sessions):
            return {"date": d, "rest_day": True, "week": week, "sessions": [{"index": i, "name": s["name"], "focus": s["focus"]} for i, s in enumerate(sessions)]}
        log = repo.get_or_new_log(p, d, int(idx))
        return {"date": d, "session_index": int(idx), "name": log["name"], "focus": log["focus"], "finished": bool(log.get("finished")), "week": week,
                "exercises": [{"name": e["name"], "unit": e["unit"], "sets": len(e["sets"]), "rep_range": f"{e['min']}-{e['max']}", "rest_sec": e["rest"],
                               "suggestion": e.get("hint", {}).get("text"), "suggested_weight": e["sets"][0].get("w"),
                               "done_sets": [{"weight_kg": s.get("w"), "reps": s.get("r")} for s in e["sets"] if s.get("done")]} for e in log["exercises"]]}

    if name == "log_workout":
        d = _date(inp)
        sessions = p["plan"]["sessions"]
        idx = inp.get("session_index")
        if idx is None:
            logs = repo.logs_on(d)
            idx = logs[0]["idx"] if logs else repo.scheduled_idx(p, d)
        idx = int(idx) if idx is not None and 0 <= int(idx) < len(sessions) else 0
        log = repo.get_or_new_log(p, d, idx)
        notes = []
        for ex in inp.get("exercises") or []:
            nm = str(ex.get("name", "")).strip()
            e = next((x for x in log["exercises"] if x["name"] == nm), None) or next((x for x in log["exercises"] if nm and (nm in x["name"] or x["name"] in nm)), None)
            if not e:
                e = {"name": nm, "unit": "kg", "min": 8, "max": 12, "rest": 90, "inc": 2.5, "sets": []}
                log["exercises"].append(e)
                notes.append(f"'{nm}' לא בתוכנית, נוסף לאימון")
            e["sets"] = [{"w": num(s.get("weight_kg")) or "", "r": num(s.get("reps")), "done": True} for s in ex.get("sets") or []]
        if not log.get("started"):
            log["started"] = int(D.now().timestamp() * 1000)
        if inp.get("finished"):
            log["finished"] = int(D.now().timestamp() * 1000)
        repo.save_log(log)
        vol = sum(num(s["w"]) * num(s["r"]) for e in log["exercises"] for s in e["sets"] if s.get("done"))
        done = sum(1 for e in log["exercises"] for s in e["sets"] if s.get("done"))
        total = sum(len(e["sets"]) for e in log["exercises"])
        return {"saved": True, "session": log["name"], "sets_done": done, "sets_total": total, "volume_kg": round(vol), "finished": bool(log.get("finished")), "notes": notes}

    if name == "get_progress":
        n = max(1, min(90, int(num(inp.get("days")) or 7)))
        end = D.today()
        start = D.add_days(end, -n + 1)
        days = repo.days(start)
        logged = [repo.sums(x) for k, x in days.items() if k <= end and x.get("meals")]
        logs = [l for l in repo.logs(start).values() if l.get("finished")]
        best = {}
        for l in repo.logs().values():
            for e in l.get("exercises", []):
                for s in e["sets"]:
                    if s.get("done") and e.get("unit") == "kg" and num(s.get("w")) > 0 and num(s.get("r")) > 0:
                        v = num(s["w"]) * (1 + num(s["r"]) / 30)
                        if v > best.get(e["name"], (0,))[0]:
                            best[e["name"]] = (v, f"{num(s['w']):g}×{num(s['r']):g}", l["date"])
        tr = repo.trend()
        adj = None
        if tr and tr["span_days"] >= 14 and tr["weigh_ins"] >= 6:
            pct = tr["per_week_kg"] / tr["weight_trend"] * 100
            adj = -100 if pct > 0.25 else 150 if pct < -0.75 else 0
        w = repo.weights()
        return {
            "period": {"from": start, "to": end, "days": n},
            "days_logged": len(logged),
            "avg_per_logged_day": {"kcal": round(sum(x["kcal"] for x in logged) / len(logged)), "protein": round(sum(x["p"] for x in logged) / len(logged))} if logged else None,
            "targets_today": repo.targets(end, p),
            "workouts_finished": [{"date": l["date"], "name": l["name"]} for l in sorted(logs, key=lambda l: l["date"])],
            "planned_per_week": len(p.get("trainDays") or []),
            "weight": tr,
            "suggested_kcal_adjust": adj,
            "current_kcal_adjust": p.get("kcalAdjust", 0),
            "measures_latest": w["measures"][-1] if w["measures"] else None,
            "measures_first": w["measures"][0] if len(w["measures"]) > 1 else None,
            "personal_records_e1rm": sorted([{"exercise": k, "e1rm_kg": round(v[0]), "best_set": v[1], "date": v[2]} for k, v in best.items()], key=lambda x: -x["e1rm_kg"])[:8],
            "streak_days": repo.streak(),
        }

    if name == "set_workout_plan":
        sessions = []
        for s in (inp.get("sessions") or [])[:6]:
            exs = []
            for e in (s.get("exercises") or [])[:8]:
                unit = e.get("unit") if e.get("unit") in ("kg", "reps", "sec") else "kg"
                mn = max(1, int(num(e.get("min")) or 8))
                exs.append({"name": str(e.get("name", "תרגיל"))[:50], "sets": max(1, min(6, int(num(e.get("sets")) or 3))), "min": mn,
                            "max": max(mn, int(num(e.get("max")) or mn + 4)), "rest": max(30, min(240, int(num(e.get("rest")) or 90))),
                            "inc": num(e.get("inc")) if unit == "kg" else 0, "unit": unit})
            if exs:
                sessions.append({"name": str(s.get("name", "אימון"))[:30], "focus": str(s.get("focus", ""))[:60], "exercises": exs})
        if not sessions:
            return {"error": "התוכנית ריקה."}
        p["plan"] = {"source": "ai", "sessions": sessions}
        repo.save_profile(p)
        return {"saved": True, "sessions": [s["name"] for s in sessions]}

    if name == "set_reminders":
        r = {**D.DEFAULT_REMINDERS, **(p.get("reminders") or {})}
        for k in ("weigh", "workout", "evening", "weekly"):
            if k in inp:
                v = str(inp[k] or "").strip()
                if v and not _valid_hm(v):
                    return {"error": f"שעה לא תקינה: {v}. השתמש ב-HH:MM."}
                r[k] = v
        if "weekly_day" in inp:
            r["weekly_day"] = int(num(inp["weekly_day"])) % 7
        if "enabled" in inp:
            r["enabled"] = bool(inp["enabled"])
        p["reminders"] = r
        repo.save_profile(p)
        return {"reminders": r}

    return {"error": f"כלי לא מוכר: {name}"}


def _valid_hm(v):
    try:
        h, m = v.split(":")
        return 0 <= int(h) < 24 and 0 <= int(m) < 60 and len(m) == 2
    except ValueError:
        return False


def _update_profile(repo, p, inp):
    creating = not p
    p = dict(p or {})
    mapping = {"name": "name", "sex": "sex", "age": "age", "height": "height", "weight": "weight", "lifestyle": "lifestyle",
               "train_days": "trainDays", "equip": "equip", "diet": "diet", "dislikes": "dislikes", "kcal_adjust": "kcalAdjust"}
    old_days, old_equip = len(p.get("trainDays") or []), p.get("equip")
    for src, dst in mapping.items():
        if src in inp and inp[src] is not None:
            p[dst] = inp[src]
    if "trainDays" in p:
        p["trainDays"] = sorted({int(x) % 7 for x in p["trainDays"]})
    missing = [k for k in ("sex", "age", "height", "weight", "lifestyle", "trainDays", "equip") if not p.get(k)]
    if missing:
        return {"error": "חסרים פרטים: " + ", ".join(missing)}
    for k in ("age", "height", "weight"):
        p[k] = num(p[k])
    p.setdefault("name", "")
    p.setdefault("diet", [])
    p.setdefault("dislikes", "")
    p.setdefault("kcalAdjust", 0)
    p.setdefault("favorites", [])
    p.setdefault("createdAt", int(D.now().timestamp() * 1000))
    p.setdefault("reminders", dict(D.DEFAULT_REMINDERS))
    if creating or not p.get("plan") or old_days != len(p["trainDays"]) or old_equip != p["equip"]:
        p["plan"] = D.gen_plan(len(p["trainDays"]), p["equip"])
    repo.save_profile(p)
    if "weight" in inp and inp["weight"]:
        w = repo.weights()
        d = D.today()
        w["entries"] = sorted([x for x in w["entries"] if x["d"] != d] + [{"d": d, "kg": round(num(inp["weight"]), 1)}], key=lambda x: x["d"])
        repo.save_weights(w)
    t_train = D.calc_targets(p, repo.cur_weight(p), True)
    t_rest = D.calc_targets(p, repo.cur_weight(p), False)
    return {"saved": True, "created": creating, "summary": D.profile_summary(p, repo.cur_weight(p)),
            "targets": {"training_day_kcal": t_train["kcal"], "rest_day_kcal": t_rest["kcal"], "protein": t_train["p"], "fat": t_train["f"]},
            "plan": [s["name"] for s in p["plan"]["sessions"]]}
