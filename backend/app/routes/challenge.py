# ── Challenge Routes ──────────────────────────────────────────────────────────
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Literal
from app.config import CHALLENGE_IP_LIMIT, MAX_CHALLENGE_ACTIONS, MAX_USER_CODE_LENGTH
from app.security.game_guard import enforce_game_rate_limit
from app.simulator.challenge_engine import simulate_challenge
from app.profile_store import ProfileStoreCorrupted, record_challenge_result

router = APIRouter()

class ChallengeRequest(BaseModel):
    actions: list[
        Literal["move", "rotate", "rotate_left", "rotate_right", "fire", "scan"]
    ] = Field(max_length=MAX_CHALLENGE_ACTIONS)
    code: str | None = Field(default=None, max_length=MAX_USER_CODE_LENGTH)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    map_id: Literal[1, 2, 3] = 1

@router.post("/api/challenge/simulate")
def api_simulate_challenge(request: Request, req: ChallengeRequest):
    """Run the challenge simulation on the backend."""
    enforce_game_rate_limit(request, "challenge", ip_limit=CHALLENGE_IP_LIMIT)
    try:
        result = simulate_challenge(req.actions, req.difficulty, req.map_id, req.code)
    except SyntaxError as error:
        location = f" at line {error.lineno}" if error.lineno else ""
        raise HTTPException(
            status_code=422,
            detail=f"Invalid strategy syntax{location}: {error.msg}",
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=f"Invalid strategy: {error}") from error

    user = request.session.get("user")
    if user and result.get("ticks"):
        player_events = [
            event
            for tick in result["ticks"]
            for event in tick.get("events", [])
            if event.get("slot") == "PLAYER"
        ]
        final_tick = result["ticks"][-1]
        player_hp = max(0, int(final_tick["player"]["hp"]))
        initial_ai_hp = {"easy": 50, "medium": 100, "hard": 150}[req.difficulty]
        ai_damage = max(0, initial_ai_hp - int(final_tick["ai"]["hp"]))
        score = player_hp * 10 + ai_damage * 20
        if result.get("winner") == "PLAYER":
            score += 1_000
        try:
            record_challenge_result(
                str(user["id"]),
                difficulty=req.difficulty,
                map_id=req.map_id,
                winner=str(result.get("winner", "draw")),
                score=score,
                shots=sum(event.get("kind") == "fire" for event in player_events),
                hits=sum(bool(event.get("hit")) for event in player_events),
                walls_destroyed=sum(
                    bool(event.get("wall", {}).get("destroyed")) for event in player_events
                ),
                code=req.code,
            )
            result["progress_saved"] = True
        except (OSError, ProfileStoreCorrupted, ValueError):
            # Profile persistence is optional and must never abort a valid battle.
            result["progress_saved"] = False
    return result
