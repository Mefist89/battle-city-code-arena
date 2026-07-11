# ── Game Routes ───────────────────────────────────────────────────────────────
# REST endpoints for single-player missions.

from fastapi import APIRouter, Query, Header, HTTPException
from typing import Annotated, Optional
from app.schemas.game import Command, CommandResult, TankState
from app.simulator.mission_engine import execute_command
from app.config import APP_VERSION
from app.session_store import store

router = APIRouter()


def get_session(x_session_id: str | None):
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Missing X-Session-Id header")
    state = store.get(x_session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return state


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
    state = get_session(x_session_id)
    tank = state.tank.model_dump()
    tank['session_id'] = x_session_id
    return tank


@router.post("/api/game/reset")
def reset_state(
    mission_id: int = Query(default=1, ge=1, le=6),
    x_session_id: Annotated[Optional[str], Header()] = None
):
    """Reset the game state for a given mission. If no session is provided, creates a new one."""
    if x_session_id and store.get(x_session_id):
        # Reset existing session
        state = store.reset(x_session_id, mission_id)
        session_id = x_session_id
    else:
        # Create new session
        session_id, state = store.create(mission_id)
        
    tank = state.tank.model_dump()
    tank['session_id'] = session_id
    return tank


from pydantic import BaseModel
from app.simulator.python_runner import run_user_code

class RunCodeRequest(BaseModel):
    code: str

@router.post("/api/game/run")
def run_user_script(
    req: RunCodeRequest,
    x_session_id: Annotated[Optional[str], Header()] = None
):
    """Execute python code and return the replay ticks."""
    state = get_session(x_session_id)
    # The runner mutates the state and generates the replay
    result = run_user_code(req.code, state)
    result['session_id'] = x_session_id
    return result

from app.levels.missions import FULL_MISSIONS

@router.get("/api/missions")
def get_missions():
    """Return all missions configuration."""
    return FULL_MISSIONS
