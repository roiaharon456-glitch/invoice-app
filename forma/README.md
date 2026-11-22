# פורמה

מאמן כושר ותזונה אישי ל-Recomp: סוכן בווטסאפ ואפליקציית ווב שעובדים על אותם נתונים.

```
ווטסאפ  ⇄  שרת FastAPI (Render)  ⇄  Supabase (טבלת docs)
                 ⇅                         ⇅
          Claude API (הסוכן)        אפליקציית הווב (static/index.html)
          Gemini (תמלול קוליות)
```

## מה הסוכן יודע לעשות

| אתה שולח | מה קורה |
|---|---|
| "אכלתי 2 ביצים, טוסט וקוטג׳" | רושם ארוחה עם הערכה תזונתית, ומחזיר כמה נשאר היום |
| 📷 תמונה של צלחת | מזהה את המנה, מעריך כמויות ורושם |
| 🎤 הודעה קולית | מתמלל עם Gemini ומטפל כמו בהודעת טקסט |
| "81.4" (אחרי תזכורת שקילה) | שומר שקילה ומחזיר את המגמה |
| "מה האימון היום?" | התרגילים עם המשקל המומלץ לפי האימון הקודם |
| "סקוואט 80 3×8, לחיצת חזה 60 3×10, סיימתי" | רושם את הסטים ומסמן שהאימון הסתיים |
| "מה לאכול עכשיו?" | הצעה לפי מה שנשאר והגבלות התזונה |
| "תזכיר לי לשקול ב-6:45" | מעדכן את שעת התזכורת |
| "קישור לאפליקציה" | קישור כניסה אישי לאתר (תקף ל-15 דקות) |

תזכורות יזומות: שקילה בבוקר, האימון של היום (רק בימי אימון), סיכום ערב וסיכום שבועי. את השעות אפשר לשנות בווטסאפ או בהגדרות של האתר.

## הקמה

### 1. Supabase
1. צור פרויקט חדש בשם `forma` (אזור Frankfurt).
2. ב-SQL Editor הרץ את `schema.sql`.
3. ב-Project Settings ← API העתק את ה-URL ואת המפתח `service_role` (לא את `anon`).

### 2. מפתחות API
- **Claude:** ב-console.anthropic.com ← API Keys. החיוב לפי שימוש.
- **Gemini:** מפתח מ-aistudio.google.com, אותו מפתח שכבר יש לך ב-invoice-app.

### 3. פריסה ל-Render
הקוד נמצא בתיקייה `forma/` בריפו `invoice-app`, בענף `claude/friendly-knuth-shf0e5`.

1. ב-Render: New ← Web Service ← בחר את הריפו `invoice-app`.
2. מלא:
   - Branch: `claude/friendly-knuth-shf0e5`
   - Root Directory: `forma`
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance Type: Free
3. ב-Environment הוסף:

   | משתנה | ערך |
   |---|---|
   | `PYTHON_VERSION` | `3.12.8` |
   | `ANTHROPIC_API_KEY` | המפתח מ-console.anthropic.com |
   | `GEMINI_API_KEY` | המפתח מ-invoice-app |
   | `SUPABASE_URL` | מ-Supabase ← Project Settings ← API |
   | `SUPABASE_SERVICE_KEY` | המפתח הסודי (secret / service_role) מאותו מסך |
   | `SESSION_SECRET`, `CRON_SECRET`, `WA_VERIFY_TOKEN` | כל מחרוזת אקראית ארוכה, שונה לכל אחד |
   | `PUBLIC_URL` | הכתובת ש-Render נותן לשירות, למשל `https://forma-xxxx.onrender.com` |

   את משתני הווטסאפ מוסיפים בשלב הבא.
4. Deploy. כשהשירות עולה, `https://<הכתובת>/health` מחזיר `{"ok":true}`.

### 4. WhatsApp Cloud API
1. ב-developers.facebook.com: Create App ← סוג Business ← הוסף את המוצר WhatsApp.
2. במסך API Setup תקבל מספר בדיקה. הוסף את המספר שלך ברשימת הנמענים ואמת אותו בקוד שיגיע אליך.
3. העתק ל-Render:
   - `WA_PHONE_NUMBER_ID`: ה-Phone number ID מהמסך הזה.
   - `WA_TOKEN`: הטוקן במסך זמני ל-24 שעות. לטוקן קבוע: Business Settings ← System users ← צור משתמש ← Generate token עם ההרשאות `whatsapp_business_messaging` ו-`whatsapp_business_management`.
   - `WA_APP_SECRET`: App settings ← Basic ← App secret.
   - `OWNER_PHONE`: המספר שלך, רק ספרות עם קידומת מדינה, למשל `972501234567`. הסוכן מתעלם מכל מספר אחר.
4. Webhook (WhatsApp ← Configuration):
   - Callback URL: `https://<הכתובת שלך>/webhook`
   - Verify token: הערך של `WA_VERIFY_TOKEN` מ-Render
   - Webhook fields: סמן `messages`.
5. **תבנית לתזכורות.** ווטסאפ מרשה לשלוח הודעה חופשית רק תוך 24 שעות מההודעה האחרונה שלך. מחוץ לחלון הזה התזכורות נשלחות דרך תבנית מאושרת. ב-WhatsApp Manager ← Message templates צור:
   - שם: `forma_update`, קטגוריה: Utility, שפה: Hebrew
   - גוף: `עדכון מפורמה: {{1}}`

   האישור לוקח בדרך כלל כמה דקות עד שעות. כל עוד אתה כותב לסוכן כל יום, התזכורות נשלחות כהודעה רגילה.
6. כשתרצה מספר קבוע במקום מספר הבדיקה: WhatsApp ← Phone numbers ← Add. צריך מספר שלא פעיל כרגע באפליקציית ווטסאפ.

### 5. תזמון התזכורות
ב-cron-job.org (חינם) צור משימה שרצה כל 10 דקות על הכתובת:
```
https://<הכתובת שלך>/cron/tick?key=<CRON_SECRET>
```
הקריאה הזו גם מונעת מהשרת החינמי של Render להירדם, כך שהסוכן עונה מהר.

### 6. מתחילים
שלח לסוכן "היי". אם עוד אין פרופיל, הוא ישאל כמה שאלות ויבנה לך יעדים ותוכנית. אחר כך שלח "קישור לאפליקציה" כדי להיכנס לאתר.

## עלויות
- Render, Supabase ו-cron-job.org: בחינם בתוכניות הבסיסיות.
- ווטסאפ: תשובות להודעות שאתה שולח בחינם. תבנית (תזכורת מחוץ לחלון 24 השעות) עולה כמה אגורות להודעה.
- Claude: לפי שימוש. ההנחיות והכלים נשמרים במטמון, כך שכל הודעה עולה בדרך כלל סנטים בודדים. אפשר לשנות דגם ב-`AGENT_MODEL` ואת עומק החשיבה ב-`AGENT_EFFORT` (`low` מהיר וזול, `medium` מעמיק יותר).

## פיתוח מקומי
```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q                                   # בדיקות מקצה לקצה, עם Claude ו-WhatsApp מדומים
DEV_NO_AUTH=1 uvicorn main:app --reload     # האתר על http://localhost:8000 עם SQLite מקומי
```
בלי `SUPABASE_URL` השרת שומר לקובץ `data/forma.db`.

## מבנה
- `main.py`: נתיבים (אתר, API, webhook, cron)
- `app/agent.py`: לולאת הסוכן מול Claude, כולל fallback אוטומטי לדגם חלופי כשיש סירוב
- `app/tools.py`: הכלים שהסוכן מפעיל (רישום ארוחות, אימונים, שקילות, פרופיל, תזכורות)
- `app/domain.py`: חישובי יעדים, מגמת משקל, התקדמות באימונים (זהים לחישובים באתר)
- `app/reminders.py`: התזכורות היזומות
- `app/whatsapp.py`, `app/transcribe.py`, `app/auth.py`
- `static/index.html`: האפליקציה
- `app/plan_lib.json`: ספריית התרגילים, משותפת לשרת ולאתר
