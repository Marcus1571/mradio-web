"""Admin-only recording controls and the saved-tracks list (see recorder.py)."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .. import recorder
from ..deps import require_admin

router = APIRouter(prefix="/api", tags=["recordings"])


class RecordRequest(BaseModel):
    sid: str
    on: bool


@router.post("/record")
async def set_recording(body: RecordRequest, user: dict = Depends(require_admin)) -> dict:
    if not body.on:
        recorder.ARMED.discard(body.sid)
        return {"on": False}
    s = recorder.STREAMS.get(body.sid)
    if not s or s["user_id"] != user["id"]:
        raise HTTPException(409, "no active stream to record")
    if not s["recordable"]:
        raise HTTPException(409, "only MP3 streams that send track titles can be recorded")
    recorder.ARMED.add(body.sid)
    return {"on": True}


@router.get("/recordings")
async def list_recordings(user: dict = Depends(require_admin)) -> list[dict]:
    return recorder.list_recordings(user["id"])


def _path(user: dict, name: str) -> Path:
    if Path(name).name != name or not name.endswith(".mp3"):
        raise HTTPException(400, "bad file name")
    p = recorder.rec_dir(user["id"]) / name
    if not p.is_file():
        raise HTTPException(404, "not found")
    return p


@router.get("/recordings/{name}")
async def download(name: str, user: dict = Depends(require_admin)):
    return FileResponse(_path(user, name), media_type="audio/mpeg", filename=name)


@router.delete("/recordings/{name}", status_code=204)
async def delete(name: str, user: dict = Depends(require_admin)) -> None:
    _path(user, name).unlink()
