from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None
    is_admin: bool
    disabled: bool
    created_at: str


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8)
    email: str | None = None
    is_admin: bool = False


class UserUpdateRequest(BaseModel):
    disabled: bool | None = None
    is_admin: bool | None = None
    password: str | None = Field(default=None, min_length=8)
