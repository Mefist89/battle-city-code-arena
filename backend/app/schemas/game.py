from pydantic import BaseModel, Field
from typing import Literal, Optional

Direction = Literal["UP", "DOWN", "LEFT", "RIGHT"]

# Поворот по часовой: UP → RIGHT → DOWN → LEFT → UP
ROTATE_CW: dict[str, Direction] = {
    "UP":    "RIGHT",
    "RIGHT": "DOWN",
    "DOWN":  "LEFT",
    "LEFT":  "UP",
}
ROTATE_CCW: dict[str, Direction] = {value: key for key, value in ROTATE_CW.items()}

# Смещение при движении вперёд
MOVE_DELTA: dict[str, tuple[int, int]] = {
    "UP":    (0, -1),
    "DOWN":  (0,  1),
    "LEFT":  (-1, 0),
    "RIGHT": (1,  0),
}


class Command(BaseModel):
    name: Literal["move", "rotate", "scan", "fire"]
    turn: Optional[Literal["LEFT", "RIGHT"]] = None


class TankState(BaseModel):
    # The outer row/column of level 1 is a wall, so the tank must start
    # inside the playable area.
    x: int = 1
    y: int = 6
    direction: Direction = "UP"
    hp: int = 100
    score: int = 0
    session_id: Optional[str] = None


class EnemyState(BaseModel):
    x: int
    y: int
    direction: Direction = "DOWN"
    hp: int = 100
    alive: bool = True


class WallState(BaseModel):
    x: int
    y: int
    type: Literal["brick", "steel"]


class CommandResult(BaseModel):
    ok: bool
    command: str
    message: str
    state: TankState

    enemy: EnemyState
    enemies: list[EnemyState] = Field(default_factory=list)
    walls: list[WallState]
    events: list[str] = Field(default_factory=list)
    enemy_action: Literal["move", "fire", "idle", "destroyed"] = "idle"
    enemy_actions: list[Literal["move", "fire", "idle", "destroyed"]] = Field(default_factory=list)
    log: str
    session_id: Optional[str] = None
