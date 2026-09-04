from fastapi import APIRouter, Depends, HTTPException, status

from .. import users
from ..deps import get_current_user, require_admin
from ..models import UserCreateRequest, UserOut, UserUpdateRequest

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(admin: dict = Depends(require_admin)):
    return await users.list_users()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreateRequest, admin: dict = Depends(require_admin)):
    if await users.get_by_username(body.username) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "username already taken")
    user = await users.create_user(body.username, body.password, body.email, body.is_admin)
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
    return await users.get_by_id(user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot delete yourself")
    if await users.get_by_id(user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    await users.delete_user(user_id)
