from typing import Literal

from fastapi import APIRouter, Depends

from .. import history, nowplaying
from ..deps import require_admin
from ..models import AnalyticsStats, HistoryEntry, LiveSession

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/live", response_model=list[LiveSession])
async def live_sessions(admin: dict = Depends(require_admin)):
    return nowplaying.live_snapshot()


@router.get("/history", response_model=list[HistoryEntry])
async def recent_history(limit: int = 50, offset: int = 0,
                         admin: dict = Depends(require_admin)):
    limit = max(1, min(limit, 200))
    return await history.recent_history(limit, offset)


@router.get("/stats", response_model=AnalyticsStats)
async def stats(since: Literal["7d", "30d", "all"] = "30d",
                admin: dict = Depends(require_admin)):
    return await history.stats(since)
