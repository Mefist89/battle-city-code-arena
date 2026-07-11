# ── Battle City: Code Arena — API Entry Point ─────────────────────────────────
# This file only creates the FastAPI app, configures middleware,
# and includes the routers. All logic lives in the submodules.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_TITLE, CORS_ORIGINS
from app.routes import game, pvp, challenge
from contextlib import asynccontextmanager
from app.simulator.pvp_engine import load_rooms_from_disk

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_rooms_from_disk()
    yield

app = FastAPI(title=APP_TITLE, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game.router)
app.include_router(pvp.router)
app.include_router(challenge.router)
