# ── Mission Engine ────────────────────────────────────────────────────────────
# Single-player mission logic: tank commands, enemy AI, state management.
# Replaces the global mutable state from main.py with MissionState class.

from app.schemas.game import (
    Command, CommandResult, EnemyState, TankState, WallState,
    ROTATE_CW, MOVE_DELTA,
)
from app.levels.missions import MISSION_WALLS, MISSION_ENEMIES
from app.simulator.mechanics import ray_cells, direction_between, clear_shot


class MissionState:
    """Holds the mutable state for a single-player mission session."""

    def __init__(self) -> None:
        self.tank = TankState()
        self.enemy = EnemyState(x=8, y=5)
        self.walls: dict[tuple[int, int], str] = dict(MISSION_WALLS[1])
        self.active_mission: int = 1

    def reset(self, mission_id: int) -> TankState:
        """Reset the game state for a given mission."""
        self.active_mission = mission_id
        self.tank = TankState()
        ex, ey, hp = MISSION_ENEMIES[mission_id]
        self.enemy = EnemyState(x=ex, y=ey, hp=hp)
        self.walls = dict(MISSION_WALLS[mission_id])
        return self.tank


def enemy_turn(state: MissionState, events: list[str]) -> str:
    """Execute one AI turn for the enemy tank."""
    tank = state.tank
    enemy = state.enemy
    walls = state.walls

    if not enemy.alive or tank.hp <= 0:
        return "destroyed" if not enemy.alive else "idle"

    if clear_shot(enemy.x, enemy.y, tank.x, tank.y, walls):
        enemy.direction = direction_between(enemy.x, enemy.y, tank.x, tank.y)
        tank.hp = max(0, tank.hp - 25)
        events.append(f"Enemy fired {enemy.direction}: player HP={tank.hp}")
        if tank.hp == 0:
            events.append("PLAYER DESTROYED")
        return "fire"

    candidates = []
    if abs(tank.x - enemy.x) >= abs(tank.y - enemy.y):
        candidates.extend([
            (tank.x > enemy.x, "RIGHT"),
            (tank.x < enemy.x, "LEFT"),
            (tank.y > enemy.y, "DOWN"),
            (tank.y < enemy.y, "UP"),
        ])
    else:
        candidates.extend([
            (tank.y > enemy.y, "DOWN"),
            (tank.y < enemy.y, "UP"),
            (tank.x > enemy.x, "RIGHT"),
            (tank.x < enemy.x, "LEFT"),
        ])

    for enabled, direction in candidates:
        if not enabled:
            continue
        dx, dy = MOVE_DELTA[direction]
        target = (enemy.x + dx, enemy.y + dy)
        if (
            0 <= target[0] <= 9
            and 0 <= target[1] <= 7
            and target not in walls
            and target != (tank.x, tank.y)
        ):
            enemy.direction = direction
            enemy.x, enemy.y = target
            events.append(f"Enemy moved {direction} to {target}")
            return "move"

    events.append("Enemy holds position")
    return "idle"


def execute_command(state: MissionState, cmd: Command) -> CommandResult:
    """Execute a single tank command and return the result."""
    tank = state.tank
    enemy = state.enemy
    walls = state.walls
    events: list[str] = []

    if tank.hp <= 0:
        return CommandResult(
            ok=False, command=cmd.name, message="Player destroyed",
            state=tank, enemy=enemy,
            walls=[WallState(x=x, y=y, type=t) for (x, y), t in walls.items()],
            events=["Reset the mission to continue"],
            enemy_action="idle", log="ERROR: player destroyed",
        )

    if cmd.name == "move":
        dx, dy = MOVE_DELTA[tank.direction]
        new_x = tank.x + dx
        new_y = tank.y + dy
        # Простая граница карты 10x8 (X: 0..9, Y: 0..7)
        if (new_x, new_y) in walls or (enemy.alive and (new_x, new_y) == (enemy.x, enemy.y)):
            msg = f"Cannot move {tank.direction}: obstacle!"
            log = "move() → BLOCKED: obstacle hit"
            ok = False
        elif 0 <= new_x <= 9 and 0 <= new_y <= 7:
            tank.x, tank.y = new_x, new_y
            msg = f"Tank moved {tank.direction} → ({tank.x}, {tank.y})"
            log = f"move() → OK: pos=({tank.x},{tank.y})"
            ok = True
        else:
            msg = f"Cannot move {tank.direction}: wall!"
            log = "move() → BLOCKED: boundary hit"
            ok = False

    elif cmd.name == "rotate":
        old_dir = tank.direction
        tank.direction = ROTATE_CW[tank.direction]
        msg = f"Tank rotated {old_dir} → {tank.direction}"
        log = f"rotate() → direction={tank.direction}"
        ok = True

    elif cmd.name == "scan":
        distance = abs(enemy.x - tank.x) + abs(enemy.y - tank.y) if enemy.alive else None
        msg = (
            f"Enemy detected at ({enemy.x},{enemy.y}), distance={distance}"
            if enemy.alive
            else "No enemies remain"
        )
        log = f"scan() → {msg}"
        ok = True

    elif cmd.name == "fire":
        hit = "miss"
        for cell in ray_cells(tank.x, tank.y, tank.direction):
            if cell in walls:
                if walls[cell] == "brick":
                    del walls[cell]
                    events.append(f"Brick wall destroyed at {cell}")
                    hit = "brick wall destroyed"
                else:
                    events.append(f"Shot blocked by steel at {cell}")
                    hit = "steel blocked"
                break
            if enemy.alive and cell == (enemy.x, enemy.y):
                enemy.hp = max(0, enemy.hp - 50)
                events.append(f"Enemy hit: HP={enemy.hp}")
                hit = "enemy hit"
                if enemy.hp == 0:
                    enemy.alive = False
                    tank.score += 500
                    events.append("ENEMY DESTROYED: +500 score")
                break
        msg = f"Fired {tank.direction}: {hit}"
        log = f"fire() → {hit}"
        ok = True

    else:
        msg = "Unknown command"
        log = "ERROR: unknown command"
        ok = False

    action = enemy_turn(state, events)
    return CommandResult(
        ok=ok,
        command=cmd.name,
        message=msg,
        state=tank,
        enemy=enemy,
        walls=[WallState(x=x, y=y, type=t) for (x, y), t in walls.items()],
        events=events,
        enemy_action=action,
        log=log,
    )
