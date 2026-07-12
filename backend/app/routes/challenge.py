# ── Challenge Routes ──────────────────────────────────────────────────────────
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal
from app.simulator.challenge_engine import simulate_challenge

router = APIRouter()

class ChallengeRequest(BaseModel):
    actions: list[Literal["move", "rotate", "rotate_left", "rotate_right", "fire", "scan"]]
    code: str | None = None
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    map_id: Literal[1, 2, 3] = 1

@router.post("/api/challenge/simulate")
def api_simulate_challenge(req: ChallengeRequest):
    """Run the challenge simulation on the backend."""
    return simulate_challenge(req.actions, req.difficulty, req.map_id, req.code)
