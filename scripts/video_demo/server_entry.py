"""Runs the invoice-app FastAPI server for the demo recording: isolated temp DB,
email sending stubbed out so the recording never hits Resend or a real inbox.
"""
import asyncio
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

import main as app_module  # noqa: E402


async def _fake_send_email(user, invoice_bytes, filename, content_type, expense_reason="", expense_amount=""):
    await asyncio.sleep(0.4)  # mimic real network latency so the loading step reads naturally


app_module.send_email = _fake_send_email

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("DEMO_PORT", "8765"))
    uvicorn.run(app_module.app, host="127.0.0.1", port=port, log_level="warning")
