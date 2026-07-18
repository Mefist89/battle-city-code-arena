# ── Challenge Engine ────────────────────────────────────────────────────────────
# Simulates the Challenge mode battle entirely on the backend to avoid 
# logic duplication. Replaces frontend loop.

from app.schemas.game import ROTATE_CW, ROTATE_CCW, MOVE_DELTA
from app.levels.missions import PVP_WALLS

from collections import deque
import random
from app.simulator.strategy_parser import iter_strategy_actions

DEFAULT_TICK_MS = 420
EASY_TICK_MS = 500
EASY_AI_THINK_MS = 1_000
EASY_AI_FIRE_COOLDOWN_MS = 2_000
MEDIUM_AI_FIRE_COOLDOWN_MS = 840
HARD_AI_FIRE_COOLDOWN_MS = 1_260
BATTLE_DURATION_MS = 30_000

CHALLENGE_MAPS = {
    1: set(PVP_WALLS),
    2: {(2, 1), (2, 2), (2, 3), (7, 4), (7, 5), (7, 6), (4, 2), (5, 2), (4, 5), (5, 5)},
    3: {(3, 1), (4, 1), (5, 2), (6, 2), (2, 4), (3, 4), (6, 5), (7, 5), (4, 6), (5, 6)},
}

def direction_to_target(from_x: int, from_y: int, to_x: int, to_y: int) -> str:
    if from_x == to_x:
        return "UP" if to_y < from_y else "DOWN"
    else:
        return "LEFT" if to_x < from_x else "RIGHT"

def line_of_sight(from_tank: dict, to_tank: dict, walls: set) -> bool:
    if from_tank["x"] != to_tank["x"] and from_tank["y"] != to_tank["y"]:
        return False
    direction = direction_to_target(from_tank["x"], from_tank["y"], to_tank["x"], to_tank["y"])
    dx, dy = MOVE_DELTA[direction]
    x, y = from_tank["x"] + dx, from_tank["y"] + dy
    while 0 <= x <= 9 and 0 <= y <= 7:
        if (x, y) in walls:
            return False
        if x == to_tank["x"] and y == to_tank["y"]:
            return True
        x += dx
        y += dy
    return False

def fire_tank(shooter: dict, target: dict, walls: set, label: str) -> dict:
    path = []
    event = {"kind": "fire", "slot": label, "path": path}
    dx, dy = MOVE_DELTA[shooter["direction"]]
    x, y = shooter["x"] + dx, shooter["y"] + dy
    while 0 <= x <= 9 and 0 <= y <= 7:
        path.append({"x": x, "y": y})
        if (x, y) in walls:
            walls.remove((x, y))
            event["wall"] = {"x": x, "y": y, "destroyed": True}
            break
        if x == target["x"] and y == target["y"]:
            target["hp"] = max(0, target["hp"] - 25)
            event["hit"] = "AI" if label == "PLAYER" else "PLAYER"
            event["target_hp"] = target["hp"]
            break
        x += dx
        y += dy
    return event

def move_tank(tank: dict, other: dict, walls: set) -> bool:
    dx, dy = MOVE_DELTA[tank["direction"]]
    nx, ny = tank["x"] + dx, tank["y"] + dy
    if 0 <= nx <= 9 and 0 <= ny <= 7 and (nx, ny) not in walls and (nx, ny) != (other["x"], other["y"]):
        tank["x"], tank["y"] = nx, ny
        return True
    return False

def wall_in_direction(tank: dict, walls: set) -> bool:
    """Return True when the tank's shot will hit a destructible wall."""
    dx, dy = MOVE_DELTA[tank["direction"]]
    x, y = tank["x"] + dx, tank["y"] + dy
    while 0 <= x <= 9 and 0 <= y <= 7:
        if (x, y) in walls:
            return True
        x += dx
        y += dy
    return False


def tank_is_facing(shooter: dict, target: dict, walls: set) -> bool:
    """Return whether the target is in the shooter's unobstructed firing lane."""
    if not line_of_sight(shooter, target, walls):
        return False
    return shooter["direction"] == direction_to_target(
        shooter["x"], shooter["y"], target["x"], target["y"]
    )


def hard_dodge(ai: dict, player: dict, walls: set) -> dict | None:
    """Move out of the player's firing lane when a hard AI sees the shot coming."""
    if not tank_is_facing(player, ai, walls):
        return None

    if player["direction"] in ("LEFT", "RIGHT"):
        candidates = ("UP", "DOWN")
    else:
        candidates = ("LEFT", "RIGHT")

    valid: list[tuple[int, str]] = []
    for direction in candidates:
        dx, dy = MOVE_DELTA[direction]
        nx, ny = ai["x"] + dx, ai["y"] + dy
        if (
            0 <= nx <= 9
            and 0 <= ny <= 7
            and (nx, ny) not in walls
            and (nx, ny) != (player["x"], player["y"])
        ):
            distance = abs(nx - player["x"]) + abs(ny - player["y"])
            valid.append((distance, direction))

    if not valid:
        return None

    _, direction = max(valid)
    ai["direction"] = direction
    move_tank(ai, player, walls)
    return {"kind": "move", "slot": "AI", "dodged": True}


def hard_route_direction(ai: dict, player: dict, walls: set) -> str | None:
    """Find the first step towards a safe cell with a clear shot at the player."""
    start = (ai["x"], ai["y"])
    occupied = (player["x"], player["y"])
    queue = deque([(start[0], start[1], None, 0)])
    visited = {start}
    current_depth = 0
    goals: list[tuple[bool, str]] = []
    directions = ("UP", "RIGHT", "DOWN", "LEFT")

    while queue:
        x, y, first_direction, depth = queue.popleft()
        if depth > current_depth and goals:
            break
        current_depth = depth

        if first_direction is not None:
            candidate = {"x": x, "y": y, "direction": "UP", "hp": ai["hp"]}
            if line_of_sight(candidate, player, walls):
                exposed = tank_is_facing(player, candidate, walls)
                goals.append((exposed, first_direction))
                continue

        for direction in directions:
            dx, dy = MOVE_DELTA[direction]
            nx, ny = x + dx, y + dy
            position = (nx, ny)
            if (
                not (0 <= nx <= 9 and 0 <= ny <= 7)
                or position in visited
                or position in walls
                or position == occupied
            ):
                continue
            visited.add(position)
            queue.append((nx, ny, first_direction or direction, depth + 1))

    if not goals:
        return None
    safe_goals = [direction for exposed, direction in goals if not exposed]
    return safe_goals[0] if safe_goals else goals[0][1]


def move_or_turn(ai: dict, player: dict, walls: set, wanted: str) -> dict:
    if ai["direction"] != wanted:
        ai["direction"] = wanted
        return {"kind": "rotate", "slot": "AI"}
    if move_tank(ai, player, walls):
        return {"kind": "move", "slot": "AI"}
    ai["direction"] = ROTATE_CW[ai["direction"]]
    return {"kind": "rotate", "slot": "AI"}

def ai_turn(
    ai: dict,
    player: dict,
    walls: set,
    difficulty: str,
    can_fire: bool = True,
) -> dict:
    if line_of_sight(ai, player, walls):
        ai["direction"] = direction_to_target(ai["x"], ai["y"], player["x"], player["y"])
        if can_fire:
            return fire_tank(ai, player, walls, "AI")
        return {"kind": "scan", "slot": "AI"}

    if difficulty == "easy":
        choice = random.random()
        if choice < 0.3:
            return {"kind": "scan", "slot": "AI"}
        elif choice < 0.6:
            ai["direction"] = ROTATE_CW[ai["direction"]]
            return {"kind": "rotate", "slot": "AI"}
    
    if difficulty == "hard":
        route_direction = hard_route_direction(ai, player, walls)
        if route_direction:
            return move_or_turn(ai, player, walls, route_direction)

    wanted = "LEFT" if player["x"] < ai["x"] else "RIGHT"
    if abs(player["x"] - ai["x"]) >= abs(player["y"] - ai["y"]):
        wanted = "LEFT" if player["x"] < ai["x"] else "RIGHT"
    else:
        wanted = "UP" if player["y"] < ai["y"] else "DOWN"
        
    if ai["direction"] != wanted:
        ai["direction"] = wanted
        return {"kind": "rotate", "slot": "AI"}

    # Medium clears walls aggressively; Hard only spends a shot when no open
    # route to a firing position exists. Easy keeps movement-only behaviour.
    if difficulty in ("medium", "hard") and wall_in_direction(ai, walls) and can_fire:
        return fire_tank(ai, player, walls, "AI")
    return move_or_turn(ai, player, walls, wanted)

def player_turn(player: dict, ai: dict, walls: set, action: str) -> dict:
    if action == "move":
        move_tank(player, ai, walls)
    elif action in ("rotate", "rotate_right"):
        player["direction"] = ROTATE_CW[player["direction"]]
    elif action == "rotate_left":
        player["direction"] = ROTATE_CCW[player["direction"]]
    elif action == "fire":
        return fire_tank(player, ai, walls, "PLAYER")
    elif action == "scan":
        hit = line_of_sight(player, ai, walls)
        return {"kind": action, "slot": "PLAYER", "hit": hit}
    return {"kind": action, "slot": "PLAYER"}


def resolve_challenge_turn(
    player: dict,
    ai: dict,
    walls: set[tuple[int, int]],
    action: str | None,
    difficulty: str,
    ai_can_act: bool = True,
    ai_can_fire: bool = True,
) -> tuple[dict | None, dict | None, set[tuple[int, int]], tuple[int, int], set[tuple[int, int]]]:
    """Resolve both intentions against the walls visible at tick start."""
    hp_before_turn = (player["hp"], ai["hp"])
    walls_before_turn = walls.copy()

    # Hard AI can read the player's turret direction and leave a clear firing
    # lane before a projectile reaches its previous cell.
    a_event = None
    ai_walls = walls_before_turn.copy()
    if ai_can_act and difficulty == "hard" and action == "fire":
        a_event = hard_dodge(ai, player, ai_walls)

    p_event = player_turn(player, ai, walls, action) if action else None
    walls_after_player = walls.copy()

    if ai_can_act and ai["hp"] > 0 and a_event is None:
        a_event = ai_turn(ai, player, ai_walls, difficulty, ai_can_fire)

    # Apply wall destruction from either intent only after both were calculated.
    merged_walls = walls_after_player & ai_walls
    return p_event, a_event, merged_walls, hp_before_turn, walls_before_turn

def simulate_challenge(actions: list[str], difficulty: str = "medium", map_id: int = 1, code: str | None = None) -> dict:
    hp_map = {"easy": 50, "medium": 100, "hard": 150}
    ai_hp = hp_map.get(difficulty, 100)
    
    player = {"x": 1, "y": 6, "direction": "UP", "hp": 100}
    ai = {"x": 8, "y": 1, "direction": "DOWN", "hp": ai_hp}
    walls = set(CHALLENGE_MAPS.get(map_id, CHALLENGE_MAPS[1]))
    action_stream = (
        iter_strategy_actions(code, lambda: line_of_sight(player, ai, walls))
        if code
        else iter(actions)
    )
    
    tick_ms = EASY_TICK_MS if difficulty == "easy" else DEFAULT_TICK_MS
    max_ticks = (BATTLE_DURATION_MS + tick_ms - 1) // tick_ms
    ticks = []
    easy_ai_elapsed_ms = 0
    ai_last_fire_ms: int | None = None
    
    for tick_index in range(max_ticks):
        if player["hp"] <= 0 or ai["hp"] <= 0:
            break
            
        action = next(action_stream, None)
        ai_can_act = True
        if difficulty == "easy":
            easy_ai_elapsed_ms += tick_ms
            ai_can_act = easy_ai_elapsed_ms >= EASY_AI_THINK_MS
            if ai_can_act:
                easy_ai_elapsed_ms -= EASY_AI_THINK_MS
        elapsed_battle_ms = (tick_index + 1) * tick_ms
        fire_cooldown_ms = {
            "easy": EASY_AI_FIRE_COOLDOWN_MS,
            "medium": MEDIUM_AI_FIRE_COOLDOWN_MS,
            "hard": HARD_AI_FIRE_COOLDOWN_MS,
        }.get(difficulty, MEDIUM_AI_FIRE_COOLDOWN_MS)
        ai_can_fire = (
            ai_last_fire_ms is None
            or elapsed_battle_ms - ai_last_fire_ms >= fire_cooldown_ms
        )
        p_event, a_event, walls, hp_before_turn, walls_before_turn = resolve_challenge_turn(
            player, ai, walls, action, difficulty, ai_can_act, ai_can_fire
        )
        if a_event and a_event.get("kind") == "fire":
            ai_last_fire_ms = elapsed_battle_ms

        # Resolve simultaneous projectiles before applying tank or wall damage.
        if (
            p_event
            and a_event
            and p_event.get("kind") == "fire"
            and a_event.get("kind") == "fire"
        ):
            player_path = p_event.get("path", [])
            ai_path = a_event.get("path", [])
            common_cells = {
                (cell["x"], cell["y"]) for cell in player_path
            } & {
                (cell["x"], cell["y"]) for cell in ai_path
            }
            if common_cells:
                collision = min(
                    common_cells,
                    key=lambda cell: abs(
                        next(i for i, p in enumerate(player_path) if (p["x"], p["y"]) == cell)
                        - next(i for i, p in enumerate(ai_path) if (p["x"], p["y"]) == cell)
                    ),
                )
                player_index = next(
                    i for i, p in enumerate(player_path) if (p["x"], p["y"]) == collision
                )
                ai_index = next(
                    i for i, p in enumerate(ai_path) if (p["x"], p["y"]) == collision
                )
                p_event["path"] = player_path[: player_index + 1]
                a_event["path"] = ai_path[: ai_index + 1]
                p_event["collision"] = True
                a_event["collision"] = True
                for event in (p_event, a_event):
                    event.pop("hit", None)
                    event.pop("target_hp", None)
                    event.pop("wall", None)
                player["hp"], ai["hp"] = hp_before_turn
                walls = walls_before_turn
            
        ticks.append({
            "player": player.copy(),
            "ai": ai.copy(),
            "walls": [{"x": x, "y": y} for x, y in walls],
            "events": [e for e in (p_event, a_event) if e]
        })
        
    winner = "draw"
    if player["hp"] > ai["hp"]: winner = "PLAYER"
    elif ai["hp"] > player["hp"]: winner = "AI"
        
    return {"ticks": ticks, "winner": winner, "tick_ms": tick_ms}
