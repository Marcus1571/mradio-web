from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from .. import auth, users
from ..auth import SESSION_COOKIE_NAME
from ..deps import get_current_user
from ..models import ChangePasswordRequest, LoginRequest, UserOut

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
    response.set_cookie(
        SESSION_COOKIE_NAME, token,
        httponly=True, secure=True, samesite="lax",
        max_age=int(auth.SESSION_TTL.total_seconds()),
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
