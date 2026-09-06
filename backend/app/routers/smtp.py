from fastapi import APIRouter, Depends

from .. import email_sender
from .. import smtp_settings
from ..deps import require_admin
from ..models import AITestResult, SmtpSettingsUpdate

router = APIRouter(prefix="/api/settings/smtp", tags=["settings"])


@router.get("")
async def get_smtp_settings(admin: dict = Depends(require_admin)):
    return smtp_settings.redacted(smtp_settings.load())


@router.patch("")
async def update_smtp_settings(body: SmtpSettingsUpdate, admin: dict = Depends(require_admin)):
    fields = body.model_dump(exclude_unset=True)
    smtp_settings.save(**fields)
    return smtp_settings.redacted(smtp_settings.load())


@router.post("/test", response_model=AITestResult)
async def test_smtp(admin: dict = Depends(require_admin)) -> AITestResult:
    if not admin.get("email"):
        return AITestResult(ok=False, message="Your admin account has no email address set.")
    ok, message = await email_sender.send_email(
        admin["email"], "mradio-web SMTP test",
        "This is a test email from mradio-web's Email settings page.",
    )
    return AITestResult(ok=ok, message=message)
