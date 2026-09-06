"""Outbound email via plain SMTP (stdlib only — smtplib + EmailMessage,
no new dependency). Used for the "forgot password" reset link and the
Email settings page's test-send button."""

import asyncio
import smtplib
from email.message import EmailMessage

from . import smtp_settings


def _send_sync(cfg: dict, to_address: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from_address"] or cfg["username"]
    msg["To"] = to_address
    msg.set_content(body)
    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as smtp:
        if cfg.get("use_tls", True):
            smtp.starttls()
        if cfg["username"]:
            smtp.login(cfg["username"], cfg["password"])
        smtp.send_message(msg)


async def send_email(to_address: str, subject: str, body: str) -> tuple[bool, str]:
    """Runs the blocking smtplib call in a thread so it doesn't stall the
    event loop. Returns (ok, message) instead of raising, so callers can
    build a clean test-result response without their own try/except."""
    cfg = smtp_settings.load()
    if not cfg["host"]:
        return False, "SMTP is not configured."
    try:
        await asyncio.to_thread(_send_sync, cfg, to_address, subject, body)
        return True, "sent"
    except (OSError, smtplib.SMTPException) as e:
        return False, str(e)
