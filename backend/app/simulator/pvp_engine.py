"""PvP room storage, ownership, cleanup, and battle simulation."""

from __future__ import annotations

import asyncio
import json
import random
import re
import string
import time
import uuid
from pathlib import Path

from fastapi import WebSocket
from pydantic import BaseModel, Field

from app.config import (
    PVP_ACTIVE_ROOM_TTL_SECONDS,
    PVP_FINISHED_ROOM_TTL_SECONDS,
    PVP_MAX_ACTIVE_ROOMS_PER_USER,
    PVP_MAX_ROOMS,
    PVP_READY_TIMEOUT_SECONDS,
    PVP_RECONNECT_GRACE_SECONDS,
    PVP_WAITING_ROOM_TTL_SECONDS,
)
from app.levels.missions import PVP_MAPS, PVP_MAP_WALLS
from app.schemas.game import MOVE_DELTA, ROTATE_CW
from app.simulator.mechanics import clear_shot, ray_cells
from app.simulator.strategy_parser import iter_strategy_actions
from app.profile_store import (
    ProfileStoreCorrupted,
    record_pvp_match,
)


rooms: dict[str, dict] = {}
DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "pvp_rooms.json"
ROOM_CODE_RE = re.compile(r"^[A-Z0-9]{6}$")


class RoomConflictError(ValueError):
    pass


class RoomCapacityError(ValueError):
    pass


class RoomPlayer(BaseModel):
    # Kept for API compatibility. The displayed name is always taken from the
    # authenticated session, never trusted from this field.
    name: str = Field(default="Player", min_length=1, max_length=32)
    map_id: int = Field(default=1, ge=1, le=3)
    private: bool = False


def generate_room_code() -> str:
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    while code in rooms:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return code


def _serializable_room(room: dict) -> dict:
    safe_room = {k: v for k, v in room.items() if k != "connections"}
    safe_room["ready"] = sorted(safe_room.get("ready", set()))
    safe_room["walls"] = [
        {"x": x, "y": y, "type": wall_type}
        for (x, y), wall_type in sorted(safe_room.get("walls", {}).items())
    ]
    return safe_room


def save_rooms_to_disk() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {code: _serializable_room(room) for code, room in rooms.items()}
    temp_file = DATA_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(payload), encoding="utf-8")
    temp_file.replace(DATA_FILE)


def _initial_tanks() -> dict[str, dict]:
    return {
        "1": {"x": 1, "y": 6, "direction": "UP", "hp": 100},
        "2": {"x": 8, "y": 1, "direction": "DOWN", "hp": 100},
    }


def _reset_interrupted_battle(room: dict) -> None:
    """Return an interrupted realtime battle to a clean preparation phase."""
    map_id = room["map_id"]
    room["walls"] = dict(PVP_MAP_WALLS[map_id])
    room["tanks"] = _initial_tanks()
    room["winner"] = None
    room["ready"] = set()
    room["programs"] = {}
    room["indexes"] = {"1": 0, "2": 0}
    room["phase"] = "prepare"
    room["tick"] = 0
    room["last_active"] = time.time()
    room["disconnected_at"] = {}
    room["ready_deadline"] = None


def load_rooms_from_disk() -> None:
    """Restore valid rooms and safely reset interrupted realtime battles."""
    rooms.clear()
    if not DATA_FILE.exists():
        return
    try:
        loaded = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return

    recovered_interrupted_battle = False
    for code, room in loaded.items():
        if not ROOM_CODE_RE.fullmatch(code) or not isinstance(room, dict):
            continue
        player_ids = room.get("player_ids")
        if not isinstance(player_ids, dict) or not player_ids.get("1"):
            # Legacy anonymous rooms are intentionally not trusted.
            continue
        map_id = room.get("map_id", 1)
        if map_id not in PVP_MAPS:
            continue
        room["connections"] = {}
        room["disconnected_at"] = {}
        room["ready_deadline"] = room.get("ready_deadline")
        room["ready"] = set(room.get("ready", []))
        raw_walls = room.get("walls")
        if isinstance(raw_walls, list) and all(isinstance(wall, dict) for wall in raw_walls):
            parsed_walls = {}
            for wall in raw_walls:
                try:
                    cell = (int(wall["x"]), int(wall["y"]))
                except (KeyError, TypeError, ValueError):
                    continue
                if wall.get("type") in {"brick", "steel"}:
                    parsed_walls[cell] = wall["type"]
            room["walls"] = parsed_walls
        elif isinstance(raw_walls, list):
            # Migrate the old coordinate-only persistence format.
            cells = {
                (int(cell[0]), int(cell[1]))
                for cell in raw_walls
                if isinstance(cell, list)
                and len(cell) == 2
                and all(isinstance(value, int) for value in cell)
            }
            room["walls"] = {
                cell: PVP_MAP_WALLS[map_id].get(cell, "brick") for cell in cells
            }
        else:
            room["walls"] = dict(PVP_MAP_WALLS[map_id])
        room["last_active"] = float(room.get("last_active", time.time()))
        room["created_at"] = float(room.get("created_at", room["last_active"]))
        room["private"] = bool(room.get("private", True))
        room["ratings"] = {
            slot: int(room.get("ratings", {}).get(slot, 1000))
            for slot in room.get("player_ids", {})
        }
        room["result_reason"] = room.get("result_reason")
        room["match_id"] = str(room.get("match_id") or uuid.uuid4().hex)
        # A battle task cannot survive a backend restart. This also repairs
        # rooms written by older versions as prepare + both players ready.
        programs = room.get("programs", {})
        has_legacy_program = any(not isinstance(program, str) for program in programs.values())
        if (
            room.get("phase") == "battle"
            or has_legacy_program
            or (room.get("phase") == "prepare" and room["ready"] == {"1", "2"})
        ):
            _reset_interrupted_battle(room)
            recovered_interrupted_battle = True
        rooms[code] = room

    if recovered_interrupted_battle:
        save_rooms_to_disk()


def room_for_user(user_id: str) -> dict | None:
    active = [
        room
        for room in rooms.values()
        if user_id in room.get("player_ids", {}).values() and room.get("phase") != "finished"
    ]
    return active[0] if active else None


def _ensure_room_quota(user_id: str) -> None:
    active_count = sum(
        user_id in room.get("player_ids", {}).values() and room.get("phase") != "finished"
        for room in rooms.values()
    )
    if active_count >= PVP_MAX_ACTIVE_ROOMS_PER_USER:
        raise RoomConflictError("Finish or leave your active PvP room first")
    if len(rooms) >= PVP_MAX_ROOMS:
        raise RoomCapacityError("PvP room capacity reached. Try again later")


def public_room(room: dict) -> dict:
    return {
        "code": room["code"],
        "players": room["players"],
        "tanks": room["tanks"],
        "walls": [
            {"x": x, "y": y, "type": wall_type}
            for (x, y), wall_type in sorted(room["walls"].items())
        ],
        "map_id": room["map_id"],
        "winner": room.get("winner"),
        "ready": sorted(room["ready"]),
        "phase": room["phase"],
        "seconds_left": max(0, 30 - int(room["tick"] * 0.42)),
        "private": bool(room.get("private", False)),
        "ratings": room.get("ratings", {}),
        "online": sorted(room.get("connections", {}).keys()),
        "reconnect_grace": PVP_RECONNECT_GRACE_SECONDS,
        "result_reason": room.get("result_reason"),
        "match_id": room.get("match_id"),
        "result_confirmed": bool(room.get("result_recorded", False)),
    }


def list_open_rooms() -> list[dict]:
    result = []
    for room in rooms.values():
        if room.get("private") or room.get("phase") != "prepare" or "2" in room["players"]:
            continue
        result.append(
            {
                "code": room["code"],
                "map_id": room["map_id"],
                "host": room["players"]["1"],
                "host_rating": int(room.get("ratings", {}).get("1", 1000)),
                "created_at": room.get("created_at", room.get("last_active", time.time())),
            }
        )
    return sorted(result, key=lambda item: item["created_at"], reverse=True)[:50]


async def broadcast_room(room: dict, event: dict | None = None) -> None:
    payload = {"type": "state", "room": public_room(room), "event": event}
    dead: list[WebSocket] = []
    for websocket in list(room["connections"].values()):
        try:
            await websocket.send_json(payload)
        except Exception:
            dead.append(websocket)
    for websocket in dead:
        for slot, connection in list(room["connections"].items()):
            if connection is websocket:
                del room["connections"][slot]


def create_room(
    user_id: str,
    player_name: str,
    map_id: int = 1,
    *,
    private: bool = False,
    rating: int = 1000,
) -> dict:
    _ensure_room_quota(user_id)
    code = generate_room_code()
    room = {
        "code": code,
        "map_id": map_id,
        "walls": dict(PVP_MAP_WALLS[map_id]),
        "players": {"1": player_name[:32]},
        "player_ids": {"1": user_id},
        "tanks": _initial_tanks(),
        "connections": {},
        "winner": None,
        "ready": set(),
        "programs": {},
        "indexes": {"1": 0, "2": 0},
        "phase": "prepare",
        "tick": 0,
        "last_active": time.time(),
        "created_at": time.time(),
        "private": private,
        "ratings": {"1": max(100, int(rating))},
        "disconnected_at": {},
        "ready_deadline": None,
        "result_reason": None,
        "match_id": uuid.uuid4().hex,
    }
    rooms[code] = room
    save_rooms_to_disk()
    return room


def join_room(
    code: str, user_id: str, player_name: str, *, rating: int = 1000
) -> dict:
    room = rooms.get(code)
    if not room:
        raise KeyError("Room not found")
    if room.get("phase") != "prepare":
        raise RoomConflictError("Battle has already started")
    if user_id in room.get("player_ids", {}).values():
        raise RoomConflictError("You already occupy a slot in this room")
    _ensure_room_quota(user_id)
    if "2" in room["players"]:
        raise RoomConflictError("Room is full")
    room["players"]["2"] = player_name[:32]
    room["player_ids"]["2"] = user_id
    room.setdefault("ratings", {})["2"] = max(100, int(rating))
    room["last_active"] = time.time()
    save_rooms_to_disk()
    return room


def _room_ttl(room: dict) -> int:
    if room.get("phase") == "finished":
        return PVP_FINISHED_ROOM_TTL_SECONDS
    if room.get("phase") == "battle":
        return PVP_ACTIVE_ROOM_TTL_SECONDS
    return PVP_WAITING_ROOM_TTL_SECONDS


async def cleanup_expired_rooms() -> int:
    now = time.time()
    expired = [
        code
        for code, room in rooms.items()
        if now - room.get("last_active", now) > _room_ttl(room)
    ]
    for code in expired:
        room = rooms.pop(code)
        for connection in list(room.get("connections", {}).values()):
            try:
                await connection.close(code=1001, reason="Room expired")
            except Exception:
                pass
    if expired:
        save_rooms_to_disk()
    for room in rooms.values():
        deadline = room.get("ready_deadline")
        if room.get("phase") == "prepare" and deadline and now >= deadline:
            room["ready"] = set()
            room["programs"] = {}
            room["ready_deadline"] = None
            await broadcast_room(room, {"kind": "ready_timeout"})
            save_rooms_to_disk()
    return len(expired)


async def room_cleanup_loop() -> None:
    while True:
        await asyncio.sleep(10)
        await cleanup_expired_rooms()


async def disconnect_user(user_id: str) -> None:
    for room in rooms.values():
        for slot, owner_id in list(room.get("player_ids", {}).items()):
            if owner_id != user_id:
                continue
            connection = room.get("connections", {}).pop(slot, None)
            if connection:
                try:
                    await connection.close(code=4401, reason="Signed out")
                except Exception:
                    pass


def _resolve_moves(
    room: dict,
    actions: dict[str, str],
    events: dict[str, dict],
    starting_positions: dict[str, tuple[int, int]],
) -> None:
    targets: dict[str, tuple[int, int]] = {}
    blocked: set[str] = set()

    for slot in ("1", "2"):
        if actions[slot] != "move":
            continue
        tank = room["tanks"][slot]
        dx, dy = MOVE_DELTA[tank["direction"]]
        target = (tank["x"] + dx, tank["y"] + dy)
        targets[slot] = target
        if not (0 <= target[0] <= 9 and 0 <= target[1] <= 7):
            blocked.add(slot)
            events[slot]["blocked"] = "boundary"
        elif target in room["walls"]:
            blocked.add(slot)
            events[slot]["blocked"] = "wall"

    if targets.get("1") == targets.get("2") and "1" in targets and "2" in targets:
        blocked.update(("1", "2"))
        events["1"]["blocked"] = events["2"]["blocked"] = "tank conflict"

    for slot in ("1", "2"):
        if slot not in targets or slot in blocked:
            continue
        opponent_slot = "2" if slot == "1" else "1"
        if targets[slot] == starting_positions[opponent_slot]:
            opponent_target = targets.get(opponent_slot)
            if opponent_target is None or opponent_target == starting_positions[slot]:
                blocked.add(slot)
                events[slot]["blocked"] = "tank conflict"

    for slot, target in targets.items():
        events[slot]["from"] = {
            "x": starting_positions[slot][0],
            "y": starting_positions[slot][1],
        }
        if slot not in blocked:
            room["tanks"][slot]["x"], room["tanks"][slot]["y"] = target
            events[slot]["to"] = {"x": target[0], "y": target[1]}


def _build_shot(room: dict, slot: str, event: dict) -> None:
    opponent_slot = "2" if slot == "1" else "1"
    tank = room["tanks"][slot]
    opponent = room["tanks"][opponent_slot]
    event["direction"] = tank["direction"]
    path = []
    for cell in ray_cells(tank["x"], tank["y"], tank["direction"]):
        path.append({"x": cell[0], "y": cell[1]})
        if cell in room["walls"]:
            event["_wall"] = cell
            break
        if cell == (opponent["x"], opponent["y"]):
            event["_target"] = opponent_slot
            break
    event["path"] = path


def _projectile_collision(
    events: dict[str, dict],
    starting_positions: dict[str, tuple[int, int]],
) -> int | None:
    first_path = events["1"].get("path", [])
    second_path = events["2"].get("path", [])
    for index in range(min(len(first_path), len(second_path))):
        first = (first_path[index]["x"], first_path[index]["y"])
        second = (second_path[index]["x"], second_path[index]["y"])
        first_previous = (
            starting_positions["1"]
            if index == 0
            else (first_path[index - 1]["x"], first_path[index - 1]["y"])
        )
        second_previous = (
            starting_positions["2"]
            if index == 0
            else (second_path[index - 1]["x"], second_path[index - 1]["y"])
        )
        if first == second or (
            first == second_previous and second == first_previous
        ):
            return index
    return None


def resolve_pvp_tick(room: dict, actions: dict[str, str]) -> list[dict]:
    """Resolve both players' intents simultaneously and apply one atomic tick."""
    actions = {slot: actions.get(slot, "scan") for slot in ("1", "2")}
    events = {
        slot: {"kind": actions[slot], "slot": slot}
        for slot in ("1", "2")
    }
    starting_positions = {
        slot: (room["tanks"][slot]["x"], room["tanks"][slot]["y"])
        for slot in ("1", "2")
    }

    # Rotations are independent intents and can be applied together.
    for slot in ("1", "2"):
        tank = room["tanks"][slot]
        if tank["hp"] <= 0:
            continue
        if actions[slot] == "left":
            tank["direction"] = ROTATE_CW[ROTATE_CW[ROTATE_CW[tank["direction"]]]]
        elif actions[slot] == "right":
            tank["direction"] = ROTATE_CW[tank["direction"]]
        if actions[slot] in {"left", "right"}:
            events[slot]["direction"] = tank["direction"]

    _resolve_moves(room, actions, events, starting_positions)

    for slot in ("1", "2"):
        if actions[slot] == "scan":
            opponent_slot = "2" if slot == "1" else "1"
            tank = room["tanks"][slot]
            opponent = room["tanks"][opponent_slot]
            events[slot]["visible"] = clear_shot(
                tank["x"], tank["y"], opponent["x"], opponent["y"], room["walls"]
            )
        elif actions[slot] == "fire" and room["tanks"][slot]["hp"] > 0:
            _build_shot(room, slot, events[slot])

    if actions["1"] == "fire" and actions["2"] == "fire":
        collision_index = _projectile_collision(events, starting_positions)
        if collision_index is not None:
            for slot in ("1", "2"):
                events[slot]["path"] = events[slot]["path"][: collision_index + 1]
                events[slot]["collision"] = True
                events[slot].pop("_target", None)
                events[slot].pop("_wall", None)

    pending_damage = {"1": 0, "2": 0}
    destroyed_bricks: set[tuple[int, int]] = set()
    for slot in ("1", "2"):
        event = events[slot]
        if event.get("collision"):
            continue
        target_slot = event.pop("_target", None)
        if target_slot:
            pending_damage[target_slot] += 25
            event["hit"] = target_slot
            event["damage"] = 25
        wall_cell = event.pop("_wall", None)
        if wall_cell:
            wall_type = room["walls"].get(wall_cell)
            event["wall"] = {
                "x": wall_cell[0],
                "y": wall_cell[1],
                "type": wall_type,
                "destroyed": wall_type == "brick",
            }
            if wall_type == "brick":
                destroyed_bricks.add(wall_cell)

    for cell in destroyed_bricks:
        room["walls"].pop(cell, None)
    for slot, damage in pending_damage.items():
        if damage:
            room["tanks"][slot]["hp"] = max(0, room["tanks"][slot]["hp"] - damage)
    for event in events.values():
        target_slot = event.get("hit")
        if target_slot:
            event["target_hp"] = room["tanks"][target_slot]["hp"]

    hp1, hp2 = room["tanks"]["1"]["hp"], room["tanks"]["2"]["hp"]
    if hp1 <= 0 or hp2 <= 0:
        room["winner"] = "draw" if hp1 <= 0 and hp2 <= 0 else ("2" if hp1 <= 0 else "1")

    return [events["1"], events["2"]]


def strategy_stream(room: dict, slot: str):
    """Repeat one validated Python strategy for the duration of a PvP battle."""
    opponent_slot = "2" if slot == "1" else "1"
    tank = room["tanks"][slot]
    opponent = room["tanks"][opponent_slot]
    code = room["programs"][slot]

    def scan_visible() -> bool:
        return clear_shot(
            tank["x"], tank["y"], opponent["x"], opponent["y"], room["walls"]
        )

    while True:
        yielded = False
        for action in iter_strategy_actions(code, scan_visible):
            yielded = True
            yield {"rotate_left": "left", "rotate_right": "right"}.get(action, action)
        if not yielded:
            raise ValueError("Strategy must contain at least one tank command")


def validate_pvp_strategy(room: dict, slot: str, code: str) -> None:
    """Validate syntax and ensure a PvP strategy produces an action."""
    opponent_slot = "2" if slot == "1" else "1"
    tank = room["tanks"][slot]
    opponent = room["tanks"][opponent_slot]
    actions = iter_strategy_actions(
        code,
        lambda: clear_shot(
            tank["x"], tank["y"], opponent["x"], opponent["y"], room["walls"]
        ),
    )
    if next(actions, None) is None:
        raise ValueError("Strategy must contain at least one tank command")


async def pvp_battle_loop(room: dict) -> None:
    streams = {slot: strategy_stream(room, slot) for slot in ("1", "2")}
    await broadcast_room(room, {"kind": "start"})
    while room["tick"] < 72 and not room.get("winner"):
        now = time.time()
        for slot in ("1", "2"):
            disconnected_at = room.get("disconnected_at", {}).get(slot)
            if disconnected_at and now - disconnected_at >= PVP_RECONNECT_GRACE_SECONDS:
                room["winner"] = "2" if slot == "1" else "1"
                room["result_reason"] = "disconnect"
                break
        if room.get("winner"):
            break
        actions = {slot: next(streams[slot]) for slot in ("1", "2")}
        events = resolve_pvp_tick(room, actions)
        for slot in ("1", "2"):
            room["indexes"][slot] += 1
        room["tick"] += 1
        room["last_active"] = time.time()
        await broadcast_room(room, {"kind": "tick", "actions": events})
        await asyncio.sleep(0.42)
    if not room.get("winner"):
        hp1, hp2 = room["tanks"]["1"]["hp"], room["tanks"]["2"]["hp"]
        room["winner"] = "draw" if hp1 == hp2 else ("1" if hp1 > hp2 else "2")
        room["result_reason"] = "time"
    elif not room.get("result_reason"):
        room["result_reason"] = "destroyed"
    room["phase"] = "finished"
    room["last_active"] = time.time()
    if not room.get("result_recorded"):
        try:
            record_pvp_match(
                match_id=room["match_id"],
                room_code=room["code"],
                map_id=room["map_id"],
                player_ids=room["player_ids"],
                player_names=room["players"],
                winner=room["winner"],
                hp={slot: room["tanks"][slot]["hp"] for slot in ("1", "2")},
                reason=room["result_reason"],
            )
            room["result_recorded"] = True
        except (OSError, ProfileStoreCorrupted, ValueError):
            pass
    save_rooms_to_disk()
    await broadcast_room(room, {"kind": "finished"})
