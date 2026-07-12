# ── PvP Engine ────────────────────────────────────────────────────────────────
# PvP room management, battle loop, and WebSocket broadcasting.
# Extracted from main.py lines 35-181.

import random
import string
import asyncio
import json
import os
import time
from fastapi import WebSocket
from pydantic import BaseModel, Field

from app.schemas.game import ROTATE_CW, MOVE_DELTA
from app.levels.missions import PVP_MAPS
from app.simulator.mechanics import ray_cells


# ── In-memory room storage ───────────────────────────────────────────────────
rooms: dict[str, dict] = {}
DATA_FILE = "data/pvp_rooms.json"
ROOM_TTL = 7200  # 2 hours


class RoomPlayer(BaseModel):
    name: str
    map_id: int = Field(default=1, ge=1, le=3)


# ── Room Helpers ─────────────────────────────────────────────────────────────

def generate_room_code() -> str:
    """Generate a unique 6-character room code."""
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    while code in rooms:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return code


def save_rooms_to_disk():
    safe_rooms = {}
    for code, room in rooms.items():
        safe_room = {k: v for k, v in room.items() if k != "connections"}
        safe_room["ready"] = list(safe_room.get("ready", []))
        safe_room["walls"] = [list(cell) for cell in safe_room.get("walls", set())]
        safe_rooms[code] = safe_room
    
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(safe_rooms, f)


def load_rooms_from_disk():
    global rooms
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                loaded = json.load(f)
            for code, room in loaded.items():
                room["connections"] = {}
                room["ready"] = set(room.get("ready", []))
                room["map_id"] = room.get("map_id", 1)
                room["walls"] = {tuple(cell) for cell in room.get("walls", PVP_MAPS[room["map_id"]])}
                rooms[code] = room
        except Exception:
            pass


def cleanup_expired_rooms():
    now = time.time()
    expired = [code for code, room in rooms.items() if now - room.get("last_active", now) > ROOM_TTL]
    for code in expired:
        del rooms[code]
    if expired:
        save_rooms_to_disk()


def public_room(room: dict) -> dict:
    """Return the public-facing view of a room (safe for JSON serialization)."""
    return {
        "code": room["code"],
        "players": room["players"],
        "tanks": room["tanks"],
        "walls": [{"x": x, "y": y} for x, y in room["walls"]],
        "map_id": room["map_id"],
        "winner": room.get("winner"),
        "ready": list(room["ready"]),
        "phase": room["phase"],
        "seconds_left": max(0, 30 - int(room["tick"] * 0.42)),
    }


async def broadcast_room(room: dict, event: dict | None = None) -> None:
    """Send the current room state to all connected WebSocket clients."""
    payload = {"type": "state", "room": public_room(room), "event": event}
    dead = []
    for websocket in room["connections"].values():
        try:
            await websocket.send_json(payload)
        except Exception:
            dead.append(websocket)
    for websocket in dead:
        for slot, connection in list(room["connections"].items()):
            if connection is websocket:
                del room["connections"][slot]


def create_room(player_name: str, map_id: int = 1) -> dict:
    """Create a new PvP room and return it."""
    code = generate_room_code()
    room = {
        "code": code,
        "map_id": map_id,
        "walls": set(PVP_MAPS[map_id]),
        "players": {"1": player_name},
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
    cleanup_expired_rooms()
    save_rooms_to_disk()
    return room


# ── PvP Battle Logic ─────────────────────────────────────────────────────────

def pvp_action(room: dict, slot: str, action: str) -> dict:
    """Execute one PvP action for a player's tank."""
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
    """Run the PvP battle loop — executes programs tick by tick."""
    await broadcast_room(room, {"kind": "start"})
    while room["tick"] < 72 and not room.get("winner"):
        events = []
        for slot in ("1", "2"):
            program = room["programs"][slot]
            index = room["indexes"][slot]
            events.append(pvp_action(room, slot, program[index % len(program)]))
            room["indexes"][slot] += 1
        room["tick"] += 1
        await broadcast_room(room, {"kind": "tick", "actions": events})
        await asyncio.sleep(0.42)
    if not room.get("winner"):
        hp1, hp2 = room["tanks"]["1"]["hp"], room["tanks"]["2"]["hp"]
        room["winner"] = "draw" if hp1 == hp2 else ("1" if hp1 > hp2 else "2")
    room["phase"] = "finished"
    room["last_active"] = time.time()
    save_rooms_to_disk()
    await broadcast_room(room, {"kind": "finished"})
