# ── Challenge Engine ────────────────────────────────────────────────────────────
# Simulates the Challenge mode battle entirely on the backend to avoid 
# logic duplication. Replaces frontend loop.

from app.schemas.game import ROTATE_CW, ROTATE_CCW, MOVE_DELTA
from app.levels.missions import PVP_WALLS

import random

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
    dx, dy = MOVE_DELTA[shooter["direction"]]
    x, y = shooter["x"] + dx, shooter["y"] + dy
    while 0 <= x <= 9 and 0 <= y <= 7:
        path.append({"x": x, "y": y})
        if (x, y) in walls:
            walls.remove((x, y))
            break
        if x == target["x"] and y == target["y"]:
            target["hp"] = max(0, target["hp"] - 25)
            break
        x += dx
        y += dy
    return {"kind": "fire", "slot": label, "path": path}

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

def ai_turn(ai: dict, player: dict, walls: set, difficulty: str) -> dict:
    if line_of_sight(ai, player, walls):
        ai["direction"] = direction_to_target(ai["x"], ai["y"], player["x"], player["y"])
        return fire_tank(ai, player, walls, "AI")

    if difficulty == "easy":
        choice = random.random()
        if choice < 0.3:
            return {"kind": "scan", "slot": "AI"}
        elif choice < 0.6:
            ai["direction"] = ROTATE_CW[ai["direction"]]
            return {"kind": "rotate", "slot": "AI"}
    
    wanted = "LEFT" if player["x"] < ai["x"] else "RIGHT"
    if abs(player["x"] - ai["x"]) >= abs(player["y"] - ai["y"]):
        wanted = "LEFT" if player["x"] < ai["x"] else "RIGHT"
    else:
        wanted = "UP" if player["y"] < ai["y"] else "DOWN"
        
    if ai["direction"] != wanted:
        ai["direction"] = wanted
        return {"kind": "rotate", "slot": "AI"}
    else:
        # Medium and Hard AI clear brick walls that obstruct their chosen route.
        # Easy AI deliberately keeps the simpler movement-only behaviour.
        if difficulty in ("medium", "hard") and wall_in_direction(ai, walls):
            return fire_tank(ai, player, walls, "AI")
        if not move_tank(ai, player, walls):
            ai["direction"] = ROTATE_CW[ai["direction"]]
            return {"kind": "rotate", "slot": "AI"}
        return {"kind": "move", "slot": "AI"}

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

def simulate_challenge(actions: list[str], difficulty: str = "medium", map_id: int = 1) -> dict:
    hp_map = {"easy": 50, "medium": 100, "hard": 150}
    ai_hp = hp_map.get(difficulty, 100)
    
    player = {"x": 1, "y": 6, "direction": "UP", "hp": 100}
    ai = {"x": 8, "y": 1, "direction": "DOWN", "hp": ai_hp}
    walls = set(CHALLENGE_MAPS.get(map_id, CHALLENGE_MAPS[1]))
    
    ticks = []
    
    for _ in range(72):
        if player["hp"] <= 0 or ai["hp"] <= 0:
            break
            
        hp_before_turn = (player["hp"], ai["hp"])
        walls_before_turn = walls.copy()
        action = actions[_] if _ < len(actions) else None
        p_event = player_turn(player, ai, walls, action) if action else None
        
        a_event = None
        if ai["hp"] > 0:
            a_event = ai_turn(ai, player, walls, difficulty)

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
        
    return {"ticks": ticks, "winner": winner}
