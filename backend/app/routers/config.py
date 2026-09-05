from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import get_active_user
from ..userdata import load_cfg, persist_cfg

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdate(BaseModel):
    theme: str | None = None
    volume: int | None = None
    mute: bool | None = None
    last_url: str | None = None
    last_name: str | None = None
    language: str | None = None


@router.get("")
async def get_config(user: dict = Depends(get_active_user)):
    return await load_cfg(user["id"])


@router.patch("")
async def update_config(body: ConfigUpdate, user: dict = Depends(get_active_user)):
    fields = body.model_dump(exclude_unset=True)
    await persist_cfg(user["id"], **fields)
    return await load_cfg(user["id"])
