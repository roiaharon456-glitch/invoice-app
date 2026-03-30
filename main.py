from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
import os
from database import Database
from email_sender import send_email

app = FastAPI()
db = Database()


@app.get("/api/check-user")
async def check_user(name: str):
    user = db.get_user(name)
    if user:
        return {"exists": True, "user": user}
    return {"exists": False}


@app.post("/api/submit")
async def submit(
    name: str = Form(...),
    bank_name: str = Form(None),
    bank_number: str = Form(None),
    branch_number: str = Form(None),
    account_number: str = Form(None),
    account_holder: str = Form(None),
    invoice: UploadFile = File(...),
    expense_reason: str = Form(""),
    expense_amount: str = Form(""),
):
    user = db.get_user(name)

    if not user:
        if not all([bank_name, bank_number, branch_number, account_number, account_holder]):
            raise HTTPException(status_code=400, detail="פרטי בנק חסרים למשתמש חדש")
        db.save_user(name, bank_name, bank_number, branch_number, account_number, account_holder)
        user = db.get_user(name)

    invoice_bytes = await invoice.read()
    filename = invoice.filename or "invoice.jpg"
    content_type = invoice.content_type or "image/jpeg"

    await send_email(user, invoice_bytes, filename, content_type, expense_reason, expense_amount)

    return {"success": True, "message": "הבקשה נשלחה בהצלחה!"}


@app.put("/api/update-user")
async def update_user(
    name: str = Form(...),
    bank_name: str = Form(...),
    bank_number: str = Form(...),
    branch_number: str = Form(...),
    account_number: str = Form(...),
    account_holder: str = Form(...),
):
    db.update_user(name, bank_name, bank_number, branch_number, account_number, account_holder)
    return {"success": True}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
