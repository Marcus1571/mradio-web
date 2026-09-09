from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import email_sender, email_templates, password_reset, smtp_settings, users
from ..deps import get_current_user, require_admin
from ..models import UserCreateRequest, UserOut, UserUpdateRequest

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(admin: dict = Depends(require_admin)):
    return await users.list_users()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreateRequest, request: Request,
                      admin: dict = Depends(require_admin)):
    if await users.get_by_username(body.username) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "username already taken")
    user = await users.create_user(body.username, body.password, body.email,
                                   body.is_admin, full_name=body.full_name)
    # Only when an email was given right at creation — an admin adding
    # one later via profile edit is a deliberate, separate action that
    # shouldn't trigger a surprise invite email (the user's own
    # distinction: "if the user adds it later on his own, no email").
    if body.email:
        cfg = smtp_settings.load()
        base = email_sender.base_url(request, cfg.get("public_url", ""))
        if base:
            token = await password_reset.create_reset_token(
                user["id"], ttl=password_reset.INVITE_TTL)
            link = f"{base}/reset-password?token={token}"
            greeting = body.full_name or body.username
            await email_sender.send_email(
                body.email, "You've been invited to mradio web",
                f"Someone wonderful has invited you to mradio web.\n\n"
                f"Hi {greeting},\n\n"
                f"Your username is {body.username}.\n\n"
                f"Set your password to get started:\n\n{link}\n\n"
                "This link expires in 7 days and can only be used once.",
                html_body=email_templates.welcome_html(greeting, body.username, link),
            )
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, body: UserUpdateRequest,
                      admin: dict = Depends(require_admin)):
    target = await users.get_by_id(user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    if user_id == admin["id"] and body.is_admin is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "cannot remove your own admin rights")
    if body.disabled is not None:
        await users.set_disabled(user_id, body.disabled)
    if body.is_admin is not None:
        await users.set_admin(user_id, body.is_admin)
    if body.password:
        await users.set_password(user_id, body.password)
    profile_fields = body.model_dump(exclude_unset=True, include={"full_name", "email"})
    if profile_fields:
        await users.update_profile(user_id, **profile_fields)
    return await users.get_by_id(user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot delete yourself")
    if await users.get_by_id(user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    await users.delete_user(user_id)
