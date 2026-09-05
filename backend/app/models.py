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


class LiveSession(BaseModel):
    user_id: int
    username: str
    station: str
    genre: str
    city: str | None
    country: str | None
    lat: float | None
    lon: float | None
    elapsed_seconds: int


class HistoryEntry(BaseModel):
    id: int
    username: str
    station_name: str
    genre: str
    started_at: str
    ended_at: str | None
    city: str | None
    country: str | None
    lat: float | None
    lon: float | None


class StationCount(BaseModel):
    station_name: str
    plays: int
    seconds: float | None


class GenreCount(BaseModel):
    genre: str
    plays: int
    seconds: float | None


class UserCount(BaseModel):
    username: str
    plays: int
    seconds: float | None


class DayCount(BaseModel):
    day: str
    plays: int


class AnalyticsStats(BaseModel):
    top_stations: list[StationCount]
    top_genres: list[GenreCount]
    top_users: list[UserCount]
    by_day: list[DayCount]


class TriviaHistoryEntry(BaseModel):
    id: int
    raw_title: str
    station_name: str
    artist: str
    title: str
    performer: str
    work: str
    trivia: str
    wiki: str
    created_at: str
