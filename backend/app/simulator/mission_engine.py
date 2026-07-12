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
        self.enemies = [EnemyState(x=8, y=5)]
        self.walls: dict[tuple[int, int], str] = dict(MISSION_WALLS[1])
        self.active_mission: int = 1

    def reset(self, mission_id: int) -> TankState:
        """Reset the game state for a given mission."""
        self.active_mission = mission_id
        self.tank = TankState()
        self.enemies = [EnemyState(x=x, y=y, hp=hp) for x, y, hp in MISSION_ENEMIES[mission_id]]
        self.walls = dict(MISSION_WALLS[mission_id])
        return self.tank

    @property
    def enemy(self) -> EnemyState:
        return next((enemy for enemy in self.enemies if enemy.alive), self.enemies[0])


def enemy_single_turn(state: MissionState, enemy: EnemyState, events: list[str]) -> str:
    """Execute one AI turn for the enemy tank."""
    tank = state.tank
    walls = state.walls

    if not enemy.alive or tank.hp <= 0:
        return "destroyed" if not enemy.alive else "idle"

    # Every enemy can destroy the first brick blocking a direct line to the player.
    # Steel remains indestructible and forces the AI to find another route.
    if enemy.x == tank.x or enemy.y == tank.y:
        shot_direction = direction_between(enemy.x, enemy.y, tank.x, tank.y)
        for cell in ray_cells(enemy.x, enemy.y, shot_direction):
            if cell in walls:
                if walls[cell] == "brick":
                    enemy.direction = shot_direction
                    del walls[cell]
                    events.append(f"Enemy destroyed brick wall at {cell}")
                    return "fire"
                break
            if cell == (tank.x, tank.y):
                break

    teammate_blocks_shot = False
    if enemy.x == tank.x or enemy.y == tank.y:
        shot_direction = direction_between(enemy.x, enemy.y, tank.x, tank.y)
        for cell in ray_cells(enemy.x, enemy.y, shot_direction):
            if any(other.alive and other is not enemy and cell == (other.x, other.y) for other in state.enemies):
                teammate_blocks_shot = True
                break
            if cell == (tank.x, tank.y) or cell in walls:
                break

    if clear_shot(enemy.x, enemy.y, tank.x, tank.y, walls) and not teammate_blocks_shot:
        enemy.direction = direction_between(enemy.x, enemy.y, tank.x, tank.y)
        if id(enemy) in getattr(state, "cancelled_enemy_shots", set()):
            events.append("Enemy shot cancelled by bullet collision")
            return "fire"
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
            and all(not other.alive or other is enemy or target != (other.x, other.y) for other in state.enemies)
        ):
            enemy.direction = direction
            enemy.x, enemy.y = target
            events.append(f"Enemy moved {direction} to {target}")
            return "move"

    events.append("Enemy holds position")
    return "idle"


def enemy_turn(state: MissionState, events: list[str]) -> str:
    actions = [
        enemy_single_turn(state, enemy, events) if enemy.alive else "destroyed"
        for enemy in state.enemies
    ]
    state.enemy_actions = actions
    if "fire" in actions:
        return "fire"
    if "move" in actions:
        return "move"
    return "destroyed" if not any(enemy.alive for enemy in state.enemies) else "idle"


def execute_command(state: MissionState, cmd: Command) -> CommandResult:
    """Execute a single tank command and return the result."""
    tank = state.tank
    enemy = state.enemy
    walls = state.walls
    events: list[str] = []
    state.cancelled_enemy_shots = set()

    if tank.hp <= 0:
        return CommandResult(
            ok=False, command=cmd.name, message="Player destroyed",
            state=tank, enemy=enemy,
            enemies=state.enemies,
            walls=[WallState(x=x, y=y, type=t) for (x, y), t in walls.items()],
            events=["Reset the mission to continue"],
            enemy_action="idle", log="ERROR: player destroyed",
        )

    if cmd.name == "move":
        dx, dy = MOVE_DELTA[tank.direction]
        new_x = tank.x + dx
        new_y = tank.y + dy
        # Простая граница карты 10x8 (X: 0..9, Y: 0..7)
        if (new_x, new_y) in walls or any(e.alive and (new_x, new_y) == (e.x, e.y) for e in state.enemies):
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
        from app.schemas.game import ROTATE_CCW
        tank.direction = ROTATE_CCW[tank.direction] if cmd.turn == "LEFT" else ROTATE_CW[tank.direction]
        msg = f"Tank rotated {old_dir} → {tank.direction}"
        log = f"rotate('{cmd.turn or 'RIGHT'}') → direction={tank.direction}"
        ok = True

    elif cmd.name == "scan":
        living = [e for e in state.enemies if e.alive]
        enemy = min(living, key=lambda e: abs(e.x - tank.x) + abs(e.y - tank.y)) if living else enemy
        distance = abs(enemy.x - tank.x) + abs(enemy.y - tank.y) if living else None
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
            target_enemy = next((e for e in state.enemies if e.alive and cell == (e.x, e.y)), None)
            if target_enemy:
                # Opposing shots meet between tanks and cancel each other.
                return_direction = direction_between(target_enemy.x, target_enemy.y, tank.x, tank.y)
                teammate_in_return_path = any(
                    other.alive
                    and other is not target_enemy
                    and (other.x, other.y) in ray_cells(target_enemy.x, target_enemy.y, return_direction)
                    for other in state.enemies
                )
                if (
                    clear_shot(target_enemy.x, target_enemy.y, tank.x, tank.y, walls)
                    and not teammate_in_return_path
                ):
                    target_enemy.direction = direction_between(
                        target_enemy.x, target_enemy.y, tank.x, tank.y
                    )
                    state.cancelled_enemy_shots.add(id(target_enemy))
                    events.append("Bullets collided: no damage")
                    hit = "bullet collision"
                else:
                    target_enemy.hp = max(0, target_enemy.hp - 50)
                    events.append(f"Enemy hit: HP={target_enemy.hp}")
                    hit = "enemy hit"
                    if target_enemy.hp == 0:
                        target_enemy.alive = False
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
        enemies=state.enemies,
        walls=[WallState(x=x, y=y, type=t) for (x, y), t in walls.items()],
        events=events,
        enemy_action=action,
        enemy_actions=state.enemy_actions,
        log=log,
    )


def execute_enemy_wait(state: MissionState) -> CommandResult:
    """Advance enemies while the player has no commands left."""
    events: list[str] = []
    state.cancelled_enemy_shots = set()
    action = enemy_turn(state, events)
    enemy = state.enemy
    return CommandResult(
        ok=True,
        command="wait",
        message="Player program finished; enemies continue battle",
        state=state.tank,
        enemy=enemy,
        enemies=state.enemies,
        walls=[WallState(x=x, y=y, type=t) for (x, y), t in state.walls.items()],
        events=events,
        enemy_action=action,
        enemy_actions=state.enemy_actions,
        log="wait → enemy turn",
    )
