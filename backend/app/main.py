import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Uvicorn configures its own `uvicorn`/`uvicorn.access`/`uvicorn.error`
# loggers but leaves the root logger at the Python default (WARNING, no
# handler) — so app-level `logging.getLogger("mradio.*")` calls are
# silently dropped unless we configure this ourselves. `docker logs`
# already captures stderr, so a plain stream handler is all that's needed.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

from .db import close_db, init_db
from .enrichers import shutdown_all as shutdown_enrichers
from .routers import auth as auth_router
from .routers import config as config_router
from .routers import enrich as enrich_router
from .routers import favorites as favorites_router
from .routers import settings as settings_router
from .routers import stations as stations_router
from .routers import stream as stream_router
from .routers import users as users_router
from .routers import ws as ws_router
from .users import bootstrap_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await bootstrap_admin()
    yield
    await shutdown_enrichers()
    await close_db()


app = FastAPI(title="mradio-web", lifespan=lifespan)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(stream_router.router)
app.include_router(settings_router.router)
app.include_router(enrich_router.router)
app.include_router(favorites_router.router)
app.include_router(stations_router.router)
app.include_router(config_router.router)
app.include_router(ws_router.router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
