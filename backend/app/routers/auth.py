from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from .. import auth, email_sender, email_templates, password_reset, smtp_settings, users
from ..auth import SESSION_COOKIE_NAME
from ..deps import get_current_user
from ..models import (ChangePasswordRequest, ForgotPasswordRequest, LoginRequest,
                      ResetPasswordRequest, UserOut)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_USER_OUT_FIELDS = ("id", "username", "email", "full_name", "is_admin", "disabled",
                    "must_change_password", "created_at")


def _user_out(user: dict) -> UserOut:
    return UserOut(**{k: user[k] for k in _USER_OUT_FIELDS})


@router.post("/login", response_model=UserOut)
async def login(body: LoginRequest, response: Response):
    user = await users.get_by_username(body.username)
    if user is None or not auth.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid username or password")
    if user["disabled"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account disabled")
    token = await auth.create_session(user["id"])
    # The server-side session (and its real expiry) is identical either
    # way — only the cookie's own persistence differs. Omitting max_age
    # makes it a browser-session cookie (cleared on browser close);
    # passing it makes the browser hold onto it for the full
    # SESSION_TTL even across restarts. "Remember me" unchecked doesn't
    # shorten how long the session is valid, just whether the browser
    # keeps offering it after being closed.
    response.set_cookie(
        SESSION_COOKIE_NAME, token,
        httponly=True, secure=True, samesite="lax",
        max_age=int(auth.SESSION_TTL.total_seconds()) if body.remember_me else None,
        path="/",
    )
    return _user_out(user)


@router.post("/logout")
async def logout(request: Request, response: Response,
                 user: dict = Depends(get_current_user)):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        await auth.delete_session(token)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return _user_out(user)


@router.post("/change-password", response_model=UserOut)
async def change_password(body: ChangePasswordRequest,
                          user: dict = Depends(get_current_user)):
    ok = await users.change_own_password(user["id"], body.current_password,
                                         body.new_password)
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "current password is incorrect")
    return _user_out(await users.get_by_id(user["id"]))


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    # Always the same response regardless of outcome — whether the email
    # exists, is disabled, sending failed, or SMTP isn't configured at
    # all. Anyone probing this endpoint must not be able to tell which
    # emails are registered.
    user = await users.get_by_email(body.email)
    if user is not None and not user["disabled"]:
        cfg = smtp_settings.load()
        base = email_sender.base_url(request, cfg.get("public_url", ""))
        if base:
            token = await password_reset.create_reset_token(user["id"])
            link = f"{base}/reset-password?token={token}"
            # Also serves as a "forgot my username" recovery: the email
            # always states it, so someone who only needed the reminder
            # (and still remembers their real password) can go back to
            # the still-open login page and sign in normally — the
            # unused reset link doesn't block that, and just expires
            # untouched. See password_reset.py's peek_reset_token() for
            # the matching "show it on the set-password page too" half
            # of this.
            await email_sender.send_email(
                user["email"], "Reset your mradio web password",
                f"Your username is {user['username']}.\n\n"
                f"Click the link below to reset your password:\n\n{link}\n\n"
                "This link expires in 1 hour and can only be used once. "
                "If you didn't request this, you can ignore this email.",
                html_body=email_templates.password_reset_html(link, user["username"]),
            )
    return {"ok": True}


@router.get("/reset-password-info")
async def reset_password_info(token: str):
    """Read-only lookup (see password_reset.peek_reset_token — doesn't
    consume the token) so the set-password page can show "signing in as
    <username>" before the user submits anything, same reasoning as the
    username reminder in the email itself: no auth required, since the
    token itself is already the credential this whole flow runs on."""
    user_id = await password_reset.peek_reset_token(token)
    if user_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired token")
    user = await users.get_by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired token")
    return {"username": user["username"]}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    user_id = await password_reset.consume_reset_token(body.token)
    if user_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired token")
    await users.set_password(user_id, body.new_password, must_change_password=False)
    return {"ok": True}
