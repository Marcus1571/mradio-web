from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import get_active_user
from ..enrichers import get_enricher
from ..userdata import load_cfg, persist_cfg

router = APIRouter(prefix="/api/config", tags=["config"])

_VALID_LANGUAGES = ("en", "es", "it", "pt", "fr", "ru", "de")


class ConfigUpdate(BaseModel):
    theme: str | None = None
    volume: int | None = None
    mute: bool | None = None
    last_url: str | None = None
    last_name: str | None = None
    last_genre: str | None = None
    language: str | None = None


@router.get("")
async def get_config(user: dict = Depends(get_active_user)):
    return await load_cfg(user["id"])


@router.patch("")
async def update_config(body: ConfigUpdate, user: dict = Depends(get_active_user)):
    fields = body.model_dump(exclude_unset=True)
    await persist_cfg(user["id"], **fields)
    # The Enricher caches language in memory (set once at start(), like
    # provider) — push a live update so the next AI question uses it
    # immediately, without waiting for the process to restart. The
    # frontend's setLanguage() already awaits this PATCH and then sends
    # a WS "reenrich" for the current track right after — re-submitting
    # here too would double the outbound AI request for no benefit.
    if "language" in fields and fields["language"] in _VALID_LANGUAGES:
        enricher = await get_enricher(user["id"])
        enricher.language = fields["language"]
    return await load_cfg(user["id"])
