import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

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
from .routers import analytics as analytics_router
from .routers import auth as auth_router
from .routers import config as config_router
from .routers import enrich as enrich_router
from .routers import favorites as favorites_router
from .routers import settings as settings_router
from .routers import smtp as smtp_router
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
app.include_router(smtp_router.router)
app.include_router(enrich_router.router)
app.include_router(favorites_router.router)
app.include_router(stations_router.router)
app.include_router(config_router.router)
app.include_router(ws_router.router)
app.include_router(analytics_router.router)

class _CacheAwareStaticFiles(StaticFiles):
    """Only files actually under /assets/* are Vite-content-hashed (a new
    build always gets a new filename there) — those are safe to cache
    forever. Everything else served from this mount, including files Vite
    just copies verbatim from public/ (manifest.webmanifest, favicon.svg,
    the PWA icons, apple-touch-icon.png) as well as index.html itself,
    keeps the *same* filename across deploys despite content changing, so
    caching those at all risks a browser holding onto a stale copy
    indefinitely — this bit us twice already: once with index.html
    pointing at a previous deploy's JS/CSS, and once with the PWA install
    prompt quoting a manifest name from before a rename."""

    def file_response(self, full_path, stat_result, scope: Scope, status_code: int = 200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        if "/assets/" in str(full_path).replace("\\", "/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    # A reset-password link clicked from an email is a real GET to this
    # exact path with no matching file — StaticFiles(html=True) only
    # serves index.html for the root path, so without this it 404s.
    # Registered before the "/" mount so it takes priority.
    @app.get("/reset-password", include_in_schema=False)
    async def reset_password_page():
        return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    app.mount("/", _CacheAwareStaticFiles(directory=STATIC_DIR, html=True), name="static")
