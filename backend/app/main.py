from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .db import close_db, init_db
from .routers import auth as auth_router
from .routers import users as users_router
from .users import bootstrap_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await bootstrap_admin()
    yield
    await close_db()


app = FastAPI(title="mradio-web", lifespan=lifespan)

app.include_router(auth_router.router)
app.include_router(users_router.router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
