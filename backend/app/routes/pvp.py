"""Authenticated REST and WebSocket endpoints for PvP rooms."""

from __future__ import annotations

import asyncio
import json
import re
import time

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from app.config import (
    CORS_ORIGINS,
    PVP_CREATE_LIMIT,
    PVP_JOIN_LIMIT,
    PVP_RATE_WINDOW_SECONDS,
    PVP_WS_CONNECT_LIMIT,
    PVP_WS_IDLE_TIMEOUT_SECONDS,
    PVP_WS_MAX_MESSAGE_BYTES,
    PVP_WS_MESSAGE_LIMIT,
    PVP_WS_MESSAGE_WINDOW_SECONDS,
)
from app.security.rate_limit import pvp_rate_limiter
from app.simulator.pvp_engine import (
    ROOM_CODE_RE,
    RoomCapacityError,
    RoomConflictError,
    RoomPlayer,
    broadcast_room,
    create_room,
    join_room,
    pvp_battle_loop,
    room_for_user,
    rooms,
    save_rooms_to_disk,
)


router = APIRouter()
VALID_ACTIONS = {"move", "left", "right", "fire", "scan"}
SLOT_RE = re.compile(r"^[12]$")


def _session_user(connection: Request | WebSocket) -> dict | None:
    user = connection.session.get("user")
    if not isinstance(user, dict) or not user.get("id"):
        return None
    return user


def _client_ip(connection: Request | WebSocket) -> str:
    return connection.client.host if connection.client else "unknown"


def _consume_or_raise(key: str, limit: int, window: int) -> None:
    allowed, retry_after = pvp_rate_limiter.consume(key, limit, window)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again later",
            headers={"Retry-After": str(retry_after)},
        )


def _protect_http(request: Request, user_id: str, action: str, limit: int) -> None:
    _consume_or_raise(f"pvp:{action}:user:{user_id}", limit, PVP_RATE_WINDOW_SECONDS)
    _consume_or_raise(f"pvp:{action}:ip:{_client_ip(request)}", limit * 3, PVP_RATE_WINDOW_SECONDS)


@router.get("/api/rooms/current")
async def api_current_room(request: Request):
    user = _session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    room = room_for_user(str(user["id"]))
    if not room:
        return {"room": None}
    slot = next(
        key for key, owner_id in room["player_ids"].items() if owner_id == str(user["id"])
    )
    return {
        "room": {
            "code": room["code"],
            "slot": slot,
            "map_id": room["map_id"],
            "phase": room["phase"],
        }
    }


@router.post("/api/rooms")
async def api_create_room(player: RoomPlayer, request: Request):
    user = _session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    _protect_http(request, str(user["id"]), "create", PVP_CREATE_LIMIT)
    try:
        room = create_room(str(user["id"]), str(user.get("name") or user.get("email") or "Player"), player.map_id)
    except RoomConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RoomCapacityError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"code": room["code"], "slot": "1", "map_id": room["map_id"]}


@router.post("/api/rooms/{code}/join")
async def api_join_room(code: str, player: RoomPlayer, request: Request):
    user = _session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    code = code.upper()
    if not ROOM_CODE_RE.fullmatch(code):
        raise HTTPException(status_code=422, detail="Room code must contain 6 letters or digits")
    _protect_http(request, str(user["id"]), "join", PVP_JOIN_LIMIT)
    try:
        room = join_room(code, str(user["id"]), str(user.get("name") or user.get("email") or "Player"))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Room not found") from exc
    except RoomConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RoomCapacityError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"code": code, "slot": "2", "map_id": room["map_id"]}


async def _reject(websocket: WebSocket, code: int) -> None:
    await websocket.close(code=code)


@router.websocket("/ws/rooms/{code}/{slot}")
async def room_socket(websocket: WebSocket, code: str, slot: str):
    code = code.upper()
    origin = websocket.headers.get("origin")
    if origin not in CORS_ORIGINS:
        await _reject(websocket, 4403)
        return
    user = _session_user(websocket)
    if not user:
        await _reject(websocket, 4401)
        return
    user_id = str(user["id"])
    if not ROOM_CODE_RE.fullmatch(code) or not SLOT_RE.fullmatch(slot):
        await _reject(websocket, 4404)
        return

    connection_limits = (
        (f"pvp:ws-connect:user:{user_id}", PVP_WS_CONNECT_LIMIT),
        (f"pvp:ws-connect:ip:{_client_ip(websocket)}", PVP_WS_CONNECT_LIMIT * 3),
    )
    for limit_key, limit_value in connection_limits:
        allowed, _ = pvp_rate_limiter.consume(
            limit_key, limit_value, PVP_RATE_WINDOW_SECONDS
        )
        if not allowed:
            await _reject(websocket, 4429)
            return
    room = rooms.get(code)
    if not room or slot not in room.get("players", {}):
        await _reject(websocket, 4404)
        return
    if room.get("player_ids", {}).get(slot) != user_id:
        await _reject(websocket, 4403)
        return
    if slot in room.get("connections", {}):
        await _reject(websocket, 4409)
        return

    await websocket.accept()
    room["connections"][slot] = websocket
    room["last_active"] = time.time()
    await broadcast_room(room, {"kind": "joined", "slot": slot})
    try:
        while True:
            try:
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(), timeout=PVP_WS_IDLE_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                await websocket.close(code=4408)
                break
            if len(raw_message.encode("utf-8")) > PVP_WS_MAX_MESSAGE_BYTES:
                await websocket.close(code=4400)
                break
            allowed, _ = pvp_rate_limiter.consume(
                f"pvp:ws-message:user:{user_id}",
                PVP_WS_MESSAGE_LIMIT,
                PVP_WS_MESSAGE_WINDOW_SECONDS,
            )
            if not allowed:
                await websocket.close(code=4429)
                break
            allowed, _ = pvp_rate_limiter.consume(
                f"pvp:ws-message:ip:{_client_ip(websocket)}",
                PVP_WS_MESSAGE_LIMIT * 3,
                PVP_WS_MESSAGE_WINDOW_SECONDS,
            )
            if not allowed:
                await websocket.close(code=4429)
                break
            try:
                message = json.loads(raw_message)
            except (json.JSONDecodeError, TypeError):
                await websocket.close(code=4400)
                break
            if not isinstance(message, dict) or set(message) != {"type", "actions"}:
                await websocket.close(code=4400)
                break
            actions = message.get("actions")
            if (
                message.get("type") != "ready"
                or not isinstance(actions, list)
                or not 1 <= len(actions) <= 40
                or any(not isinstance(action, str) or action not in VALID_ACTIONS for action in actions)
            ):
                await websocket.close(code=4400)
                break
            if room.get("winner") or room.get("phase") != "prepare" or slot in room["ready"]:
                continue

            room["programs"][slot] = actions
            room["ready"].add(slot)
            room["last_active"] = time.time()
            save_rooms_to_disk()
            await broadcast_room(room, {"kind": "ready", "slot": slot})
            if room["ready"] == {"1", "2"} and room["phase"] == "prepare":
                room["phase"] = "battle"
                asyncio.create_task(pvp_battle_loop(room))
    except WebSocketDisconnect:
        pass
    finally:
        if room.get("connections", {}).get(slot) is websocket:
            room["connections"].pop(slot, None)
            await broadcast_room(room, {"kind": "left", "slot": slot})
