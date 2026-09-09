"""Outbound email via plain SMTP (stdlib only — smtplib + EmailMessage,
no new dependency). Used for the "forgot password" reset link, the
new-account welcome/invite email, and the Email settings page's
test-send button."""

import asyncio
import smtplib
from email.message import EmailMessage

from fastapi import Request

from . import smtp_settings


def base_url(request: Request, override: str) -> str:
    """Whichever domain a listener actually used to reach the app is the
    one that should come back in an emailed link — so this prefers the
    live request's own forwarded host over a fixed admin setting, which
    would be wrong for every domain except the one typed in. The admin's
    `public_url` override exists only as a fallback for an unusual proxy
    setup that doesn't forward Host/X-Forwarded-Host reliably. Shared by
    both the forgot-password and new-account-invite flows — moved here
    (rather than staying private to routers/auth.py) once a second
    caller (routers/users.py) needed it too."""
    if override:
        return override.rstrip("/")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    if not host:
        return ""
    scheme = request.headers.get("x-forwarded-proto", "https")
    return f"{scheme}://{host}"


def _send_sync(cfg: dict, to_address: str, subject: str, body: str,
               html_body: str | None) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from_address"] or cfg["username"]
    msg["To"] = to_address
    msg.set_content(body)
    if html_body:
        # multipart/alternative: plain text stays the fallback for
        # clients that don't render HTML, but any real mail client
        # picks the HTML part — same pattern every transactional-email
        # provider uses, no new dependency needed for it.
        msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as smtp:
        if cfg.get("use_tls", True):
            smtp.starttls()
        if cfg["username"]:
            smtp.login(cfg["username"], cfg["password"])
        smtp.send_message(msg)


async def send_email(to_address: str, subject: str, body: str,
                     overrides: dict | None = None,
                     html_body: str | None = None) -> tuple[bool, str]:
    """Runs the blocking smtplib call in a thread so it doesn't stall the
    event loop. Returns (ok, message) instead of raising, so callers can
    build a clean test-result response without their own try/except.

    `overrides` lets the settings page's "Test" button check whatever is
    currently typed into the form, not just what's already been saved —
    same reasoning as the AI providers page's own test buttons, which
    test in-progress field values rather than requiring a save first.

    `html_body` is optional: callers that only need a plain-text email
    (or the settings page's generic test-send) can omit it and get the
    same single-part message as before."""
    cfg = {**smtp_settings.load(), **(overrides or {})}
    if not cfg["host"]:
        return False, "Enter a host and click Save before testing."
    try:
        await asyncio.to_thread(_send_sync, cfg, to_address, subject, body, html_body)
        return True, "sent"
    except (OSError, smtplib.SMTPException) as e:
        return False, str(e)
