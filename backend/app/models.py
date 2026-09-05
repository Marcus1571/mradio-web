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
    must_change_password: bool
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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class AISettingsUpdate(BaseModel):
    ollama_url: str | None = None
    ollama_model: str | None = None
    ollama_timeout: int | None = None
    ollama_gpu: int | None = None
    api_base: str | None = None
    api_key: str | None = None
    api_model: str | None = None
    api_timeout: int | None = None
    opencode: str | None = None
    opencode_timeout: int | None = None


class ProviderSwitchRequest(BaseModel):
    name: str


class AITestResult(BaseModel):
    ok: bool
    message: str
