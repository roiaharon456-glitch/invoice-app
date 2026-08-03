# אוטומציית סרטון דמו

יוצר אוטומטית סרטון דמו (mp4) של האפליקציה: דפדפן אמיתי עובר על התהליך המלא -
הזנת שם, מילוי פרטי בנק (משתמש חדש), העלאת חשבונית לדוגמה, ושליחת הבקשה עד
למסך ההצלחה. הסרטון כולל כתוביות בעברית, ובאופן אופציונלי גם קריינות.

הכל רץ מול שרת מקומי זמני (DB זמני, שליחת המייל מדומה - לא באמת יוצא מייל
ולא נדרש `RESEND_API_KEY`), כך שאפשר להריץ את זה בכל שלב בלי תלות בסביבת
הפרודקשן.

## התקנה (חד-פעמי)

```bash
cd scripts/video_demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Playwright צריך דפדפן Chromium. אם אין לך אחד מותקן כבר:
```bash
playwright install chromium
```
(אם `PLAYWRIGHT_BROWSERS_PATH` מצביע לתיקייה עם build בגרסה לא תואמת, ה-
סקריפט ינסה למצוא `chromium-1194` שם אוטומטית; אחרת הוא ייפול חזרה לברירת
המחדל של Playwright).

צריך גם `ffmpeg` מותקן במערכת (`apt-get install ffmpeg` / `brew install ffmpeg`).

## הרצה

```bash
source .venv/bin/activate
python make_demo_video.py
```

הפלט: `output/invoice_app_demo.mp4`

### אופציות

- `--no-narration` - בלי קריינות, רק כתוביות שרופות (מהיר יותר, בלי תלות ברשת)
- `--voice he-IL-AvriNeural` - קול אחר ל-TTS (רשימת קולות: `edge-tts --list-voices | grep he-IL`)
- `--output path/to/file.mp4` - נתיב פלט אחר
- `--keep-tmp` - לא למחוק את תיקיית העבודה הזמנית (שימושי לדיבוג)

## איך זה עובד

1. `sample_invoice.py` מייצר תמונת חשבונית פיקטיבית (עם Pillow) שמשמשת כקובץ
   ההעלאה בהדגמה.
2. `server_entry.py` מריץ את `main.py` (האפליקציה עצמה) על DB זמני, עם
   `send_email` מוחלף בפונקציית stub (כדי שלא תישלח בקשה אמיתית ל-Resend).
3. `make_demo_video.py` פותח דפדפן עם Playwright ומבצע את התהליך המלא. במקום
   הקלטת וידאו המובנית של Playwright (`record_video_dir`) - שבסביבות מסוימות
   בלי GPU מפיקה פריימים ריקים - הסקריפט לוקח `page.screenshot()` על ציר זמן
   ומרכיב מהם וידאו עם FFmpeg (`concat` demuxer, פריים-רייט משתנה לפי הזמן
   האמיתי בין צילומים).
4. אם `--no-narration` לא צוין, `narration.py` מנסה לייצר קריינות עברית עם
   `edge-tts` (חינמי, מקומי-ish, אבל דורש גישת רשת ל-WebSocket של מיקרוסופט).
   אם אין גישת רשת מתאימה, הסקריפט מדפיס אזהרה וממשיך בלי קול - הסרטון עדיין
   יוצא תקין, רק שקט.
5. FFmpeg שורף כתוביות (`drawtext`, עם הפונט המצורף `NotoSansHebrew`
   ואלגוריתם ה-bidi כדי להציג עברית נכון) ומערבב את הקריינות (אם יש) לפי
   התזמון האמיתי של כל שלב בהקלטה.

## פונטים מצורפים

`assets/fonts/` מכיל את `NotoSansHebrew` (עברית) ו-`DejaVuSans` (ספרות/סימני
פיסוק לועזיים, כי ה-subset של NotoSansHebrew לא כולל אותם) - שניהם רישיון חופשי
(OFL / public domain), כדי שהסקריפט לא יהיה תלוי בפונטים שמותקנים במערכת.

**הערה**: הכתוביות הכתובות מראש (`SCENES` בתוך `make_demo_video.py`) נמנעות
בכוונה מפסיקים לועזיים (פסיק, נקודה, ספרות) כי `drawtext` של FFmpeg מקבל פונט
אחד בלבד לכל קריאה - אז לכתוביות (בניגוד לתמונת החשבונית, שמשתמשת בשני
הפונטים יחד) יש רק את NotoSansHebrew. הטקסט המדובר (narration) יכול כן לכלול
פיסוק רגיל, כי TTS לא תלוי בזמינות glyph בפונט.

## עדכון התסריט

כדי לשנות את מה שקורה בהדגמה (שם, פרטי בנק, טקסטים) - ערוך את הקבועים
בראש `make_demo_video.py` (`DEMO_NAME`, `DEMO_BANK`, `DEMO_REASON`,
`DEMO_AMOUNT`, `SCENES`) ואת `run_scenario()` אם צריך להוסיף/לשנות צעדים
בממשק עצמו.
