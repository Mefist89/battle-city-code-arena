# ── Game Routes ───────────────────────────────────────────────────────────────
# REST endpoints for single-player missions.

import re

from fastapi import APIRouter, Query, Header, HTTPException, Request
from typing import Annotated, Optional
from app.schemas.game import Command, CommandResult, TankState
from app.simulator.mission_engine import execute_command
from app.config import (
    APP_VERSION,
    GAME_RESET_IP_LIMIT,
    GAME_RUN_IP_LIMIT,
    GAME_RUN_SESSION_LIMIT,
    MAX_USER_CODE_LENGTH,
)
from app.security.game_guard import enforce_game_rate_limit
from app.session_store import store
from app.profile_store import ProfileStoreCorrupted, save_last_code

router = APIRouter()
SESSION_ID_RE = re.compile(r"^[a-f0-9]{12}$")


def validate_session_id(x_session_id: str | None) -> str:
    if not x_session_id or not SESSION_ID_RE.fullmatch(x_session_id):
        raise HTTPException(status_code=400, detail="Invalid or missing X-Session-Id header")
    return x_session_id


@router.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Бэкенд танков готов к приему команд!",
        "version": APP_VERSION,
    }


@router.get("/api/game/state")
def get_state(x_session_id: Annotated[Optional[str], Header()] = None):
    """Return the current tank state."""
    session_id = validate_session_id(x_session_id)
    with store.locked(session_id) as state:
        if state is None:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        tank = state.tank.model_dump()
    tank['session_id'] = x_session_id
    return tank


@router.post("/api/game/reset")
def reset_state(
    request: Request,
    mission_id: int = Query(default=1, ge=1, le=9),
    x_session_id: Annotated[Optional[str], Header()] = None
):
    """Reset the game state for a given mission. If no session is provided, creates a new one."""
    enforce_game_rate_limit(
        request,
        "reset",
        ip_limit=GAME_RESET_IP_LIMIT,
        session_id=x_session_id,
        session_limit=GAME_RESET_IP_LIMIT,
    )
    tank = None
    session_id = x_session_id
    if x_session_id:
        with store.locked(x_session_id) as state:
            if state is not None:
                state.reset(mission_id)
                tank = state.tank.model_dump()
    if tank is None:
        # Create new session
        session_id, state = store.create(mission_id)
        tank = state.tank.model_dump()
    tank['session_id'] = session_id
    return tank


from pydantic import BaseModel, Field
from app.simulator.python_runner import run_user_code

class RunCodeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_USER_CODE_LENGTH)

@router.post("/api/game/run")
def run_user_script(
    request: Request,
    req: RunCodeRequest,
    x_session_id: Annotated[Optional[str], Header()] = None
):
    """Execute python code and return the replay ticks."""
    enforce_game_rate_limit(
        request,
        "run",
        ip_limit=GAME_RUN_IP_LIMIT,
        session_id=x_session_id,
        session_limit=GAME_RUN_SESSION_LIMIT,
    )
    session_id = validate_session_id(x_session_id)
    with store.locked(session_id) as state:
        if state is None:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        # Keep the per-session lock for the complete simulation.
        result = run_user_code(req.code, state)
    user = request.session.get("user")
    if user:
        try:
            save_last_code(str(user["id"]), "mission", req.code)
        except (OSError, ProfileStoreCorrupted, ValueError):
            # Saving code is optional and must not interrupt the simulation.
            pass
    result['session_id'] = x_session_id
    return result

from app.levels.missions import FULL_MISSIONS

@router.get("/api/missions")
def get_missions():
    """Return all missions configuration."""
    return FULL_MISSIONS
