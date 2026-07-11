# ── PvP Routes ────────────────────────────────────────────────────────────────
# REST + WebSocket endpoints for PvP rooms.

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.simulator.pvp_engine import (
    rooms, RoomPlayer,
    create_room, broadcast_room, pvp_battle_loop,
    save_rooms_to_disk,
)
import time

router = APIRouter()


@router.post("/api/rooms")
def api_create_room(player: RoomPlayer):
    """Create a new PvP room."""
    room = create_room(player.name)
    return {"code": room["code"], "slot": "1"}


@router.post("/api/rooms/{code}/join")
def api_join_room(code: str, player: RoomPlayer):
    """Join an existing PvP room."""
    code = code.upper()
    room = rooms.get(code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if "2" in room["players"]:
        raise HTTPException(status_code=409, detail="Room is full")
    room["players"]["2"] = player.name
    room["last_active"] = time.time()
    save_rooms_to_disk()
    return {"code": code, "slot": "2"}


@router.websocket("/ws/rooms/{code}/{slot}")
async def room_socket(websocket: WebSocket, code: str, slot: str):
    """WebSocket endpoint for real-time PvP battle."""
    code = code.upper()
    room = rooms.get(code)
    if not room or slot not in room["players"]:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    room["connections"][slot] = websocket
    await broadcast_room(room, {"kind": "joined", "slot": slot})
    try:
        while True:
            message = await websocket.receive_json()
            if room.get("winner"):
                continue
            if message.get("type") == "ready" and room["phase"] == "prepare":
                actions = [
                    action
                    for action in message.get("actions", [])
                    if action in {"move", "left", "right", "fire", "scan"}
                ][:40]
                room["programs"][slot] = actions or ["scan"]
                room["ready"].add(slot)
                room["last_active"] = time.time()
                save_rooms_to_disk()
                await broadcast_room(room, {"kind": "ready", "slot": slot})
                if room["ready"] == {"1", "2"}:
                    room["phase"] = "battle"
                    asyncio.create_task(pvp_battle_loop(room))
    except WebSocketDisconnect:
        room["connections"].pop(slot, None)
        await broadcast_room(room, {"kind": "left", "slot": slot})
