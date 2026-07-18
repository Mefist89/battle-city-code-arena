# ── CODETANK ARENA — API Entry Point ──────────────────────────────────────────
# This file only creates the FastAPI app, configures middleware,
# and includes the routers. All logic lives in the submodules.

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import (
    ALLOWED_HOSTS,
    APP_TITLE,
    AUTH_COOKIE_SECURE,
    AUTH_SESSION_SECRET,
    CORS_ORIGINS,
    MAX_HTTP_REQUEST_BYTES,
)
from app.routes import auth, challenge, game, pvp
from app.security.request_size import RequestSizeLimitMiddleware
from app.simulator.pvp_engine import load_rooms_from_disk, room_cleanup_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_rooms_from_disk()
    cleanup_task = asyncio.create_task(room_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task

app = FastAPI(title=APP_TITLE, lifespan=lifespan)

if not AUTH_SESSION_SECRET:
    raise RuntimeError("AUTH_SESSION_SECRET or an OAuth client secret must be configured")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

app.add_middleware(
    SessionMiddleware,
    secret_key=AUTH_SESSION_SECRET,
    session_cookie="codetank_session",
    same_site="lax",
    https_only=AUTH_COOKIE_SECURE,
    max_age=60 * 60 * 24 * 7,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-Id"],
)

app.add_middleware(RequestSizeLimitMiddleware, max_body_bytes=MAX_HTTP_REQUEST_BYTES)

app.include_router(game.router)
app.include_router(pvp.router)
app.include_router(challenge.router)
app.include_router(auth.router)
