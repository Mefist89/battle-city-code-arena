"""PvP room storage, ownership, cleanup, and battle simulation."""

from __future__ import annotations

import asyncio
import json
import random
import re
import string
import time
from pathlib import Path

from fastapi import WebSocket
from pydantic import BaseModel, Field

from app.config import (
    PVP_ACTIVE_ROOM_TTL_SECONDS,
    PVP_FINISHED_ROOM_TTL_SECONDS,
    PVP_MAX_ACTIVE_ROOMS_PER_USER,
    PVP_MAX_ROOMS,
    PVP_WAITING_ROOM_TTL_SECONDS,
)
from app.levels.missions import PVP_MAPS
from app.schemas.game import MOVE_DELTA, ROTATE_CW
from app.simulator.mechanics import ray_cells


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


def generate_room_code() -> str:
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    while code in rooms:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return code


def _serializable_room(room: dict) -> dict:
    safe_room = {k: v for k, v in room.items() if k != "connections"}
    safe_room["ready"] = sorted(safe_room.get("ready", set()))
    safe_room["walls"] = [list(cell) for cell in sorted(safe_room.get("walls", set()))]
    return safe_room


def save_rooms_to_disk() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {code: _serializable_room(room) for code, room in rooms.items()}
    temp_file = DATA_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(payload), encoding="utf-8")
    temp_file.replace(DATA_FILE)


def load_rooms_from_disk() -> None:
    """Restore only rooms created with ownership-aware server versions."""
    rooms.clear()
    if not DATA_FILE.exists():
        return
    try:
        loaded = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return

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
        room["ready"] = set(room.get("ready", []))
        room["walls"] = {tuple(cell) for cell in room.get("walls", PVP_MAPS[map_id])}
        room["last_active"] = float(room.get("last_active", time.time()))
        rooms[code] = room


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
        "walls": [{"x": x, "y": y} for x, y in sorted(room["walls"])],
        "map_id": room["map_id"],
        "winner": room.get("winner"),
        "ready": sorted(room["ready"]),
        "phase": room["phase"],
        "seconds_left": max(0, 30 - int(room["tick"] * 0.42)),
    }


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


def create_room(user_id: str, player_name: str, map_id: int = 1) -> dict:
    _ensure_room_quota(user_id)
    code = generate_room_code()
    room = {
        "code": code,
        "map_id": map_id,
        "walls": set(PVP_MAPS[map_id]),
        "players": {"1": player_name[:32]},
        "player_ids": {"1": user_id},
        "tanks": {
            "1": {"x": 1, "y": 6, "direction": "UP", "hp": 100},
            "2": {"x": 8, "y": 1, "direction": "DOWN", "hp": 100},
        },
        "connections": {},
        "winner": None,
        "ready": set(),
        "programs": {},
        "indexes": {"1": 0, "2": 0},
        "phase": "prepare",
        "tick": 0,
        "last_active": time.time(),
    }
    rooms[code] = room
    save_rooms_to_disk()
    return room


def join_room(code: str, user_id: str, player_name: str) -> dict:
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
    return len(expired)


async def room_cleanup_loop() -> None:
    while True:
        await asyncio.sleep(60)
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


def pvp_action(room: dict, slot: str, action: str) -> dict:
    tank = room["tanks"][slot]
    opponent_slot = "2" if slot == "1" else "1"
    opponent = room["tanks"][opponent_slot]
    event = {"kind": action, "slot": slot}
    walls = room["walls"]

    if tank["hp"] <= 0:
        return event
    if action == "left":
        tank["direction"] = ROTATE_CW[ROTATE_CW[ROTATE_CW[tank["direction"]]]]
    elif action == "right":
        tank["direction"] = ROTATE_CW[tank["direction"]]
    elif action == "move":
        dx, dy = MOVE_DELTA[tank["direction"]]
        target = (tank["x"] + dx, tank["y"] + dy)
        if (
            0 <= target[0] <= 9
            and 0 <= target[1] <= 7
            and target not in walls
            and target != (opponent["x"], opponent["y"])
        ):
            tank["x"], tank["y"] = target
    elif action == "fire":
        path = []
        for cell in ray_cells(tank["x"], tank["y"], tank["direction"]):
            path.append({"x": cell[0], "y": cell[1]})
            if cell in walls:
                break
            if cell == (opponent["x"], opponent["y"]):
                opponent["hp"] = max(0, opponent["hp"] - 25)
                if opponent["hp"] == 0:
                    room["winner"] = slot
                break
        event["path"] = path
    return event


async def pvp_battle_loop(room: dict) -> None:
    await broadcast_room(room, {"kind": "start"})
    while room["tick"] < 72 and not room.get("winner"):
        events = []
        for slot in ("1", "2"):
            program = room["programs"][slot]
            index = room["indexes"][slot]
            events.append(pvp_action(room, slot, program[index % len(program)]))
            room["indexes"][slot] += 1
        room["tick"] += 1
        room["last_active"] = time.time()
        await broadcast_room(room, {"kind": "tick", "actions": events})
        await asyncio.sleep(0.42)
    if not room.get("winner"):
        hp1, hp2 = room["tanks"]["1"]["hp"], room["tanks"]["2"]["hp"]
        room["winner"] = "draw" if hp1 == hp2 else ("1" if hp1 > hp2 else "2")
    room["phase"] = "finished"
    room["last_active"] = time.time()
    save_rooms_to_disk()
    await broadcast_room(room, {"kind": "finished"})
