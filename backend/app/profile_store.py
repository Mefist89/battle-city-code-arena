import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import BACKEND_DIR


DATA_FILE = BACKEND_DIR / "data" / "user_progress.json"
_lock = threading.RLock()
CODE_MODES = {"mission", "challenge", "pvp"}
MAX_SAVED_CODE_LENGTH = 20_000


class ProfileStoreCorrupted(RuntimeError):
    """Raised when persisted progress cannot be decoded safely."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if not DATA_FILE.exists():
        return {}
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        # Never treat damaged persisted data as an empty database: doing so would
        # allow the next successful mission to overwrite every user's progress.
        raise ProfileStoreCorrupted(
            f"Progress file is corrupted; restore or repair {DATA_FILE}"
        ) from exc
    except OSError as exc:
        raise ProfileStoreCorrupted(f"Progress file cannot be read: {DATA_FILE}") from exc
    if not isinstance(data, dict):
        raise ProfileStoreCorrupted(f"Progress file must contain a JSON object: {DATA_FILE}")
    return data


def _save(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATA_FILE)


def _default_stats() -> dict:
    return {"matches": 0, "wins": 0, "losses": 0, "draws": 0, "rating": 1000}


def _ensure_record(data: dict, user_id: str) -> dict:
    record = data.setdefault(user_id, {"missions": {}, "created_at": _now()})
    record.setdefault("missions", {})
    record.setdefault("challenge", _default_stats())
    record.setdefault("pvp", _default_stats())
    record.setdefault("last_code", {})
    record.setdefault("achievements", {})
    record.setdefault("strategies", {})
    return record


def _unlock(record: dict, achievement_id: str) -> None:
    achievements = record.setdefault("achievements", {})
    achievements.setdefault(achievement_id, _now())


def _refresh_achievements(record: dict) -> None:
    missions = record.get("missions", {})
    challenge = record.get("challenge", {})
    pvp = record.get("pvp", {})
    total_score = sum(int(item.get("best_score", 0)) for item in missions.values())

    if missions:
        _unlock(record, "first_mission")
    if len(missions) >= 9:
        _unlock(record, "campaign_complete")
    if total_score >= 1_000:
        _unlock(record, "score_1000")
    if int(challenge.get("wins", 0)) >= 1:
        _unlock(record, "ai_first_win")
    if int(challenge.get("matches", 0)) >= 10:
        _unlock(record, "ai_veteran")
    if int(challenge.get("walls_destroyed", 0)) >= 10:
        _unlock(record, "brick_breaker")
    if int(challenge.get("hits", 0)) >= 10:
        _unlock(record, "sharpshooter")
    hard = challenge.get("difficulties", {}).get("hard", {})
    if int(hard.get("wins", 0)) >= 1:
        _unlock(record, "ai_hard_win")
    if int(pvp.get("wins", 0)) >= 1:
        _unlock(record, "pvp_first_win")
    if int(pvp.get("matches", 0)) >= 10:
        _unlock(record, "pvp_veteran")


def _summary(record: dict) -> dict:
    missions = record.get("missions", {})
    completed = sorted(int(mission_id) for mission_id in missions)
    challenge = {**_default_stats(), **record.get("challenge", {})}
    pvp = {**_default_stats(), **record.get("pvp", {})}
    mission_best = max(
        (int(item.get("best_score", 0)) for item in missions.values()), default=0
    )
    return {
        "completed_missions": completed,
        "completed_count": len(completed),
        "total_missions": 9,
        "total_score": sum(int(item.get("best_score", 0)) for item in missions.values()),
        "best_result": max(mission_best, int(challenge.get("best_score", 0))),
        "missions": missions,
        "challenge": challenge,
        "pvp": pvp,
        "pvp_history": record.get("pvp_history", []),
        "last_code": record.get("last_code", {}),
        "achievements": [
            {"id": achievement_id, "unlocked_at": unlocked_at}
            for achievement_id, unlocked_at in sorted(
                record.get("achievements", {}).items(), key=lambda item: item[1]
            )
        ],
        "strategies": record.get("strategies", {}),
        "updated_at": record.get("updated_at"),
    }


def get_progress(user_id: str) -> dict:
    with _lock:
        data = _load()
        existed = user_id in data
        record = _ensure_record(data, user_id)
        before = dict(record.get("achievements", {}))
        _refresh_achievements(record)
        if not existed or before != record.get("achievements", {}):
            _save(data)
        return _summary(record)


def complete_mission(user_id: str, mission_id: int, score: int) -> dict:
    with _lock:
        data = _load()
        record = _ensure_record(data, user_id)
        missions = record.setdefault("missions", {})
        mission = missions.setdefault(
            str(mission_id),
            {"best_score": 0, "completions": 0, "completed_at": _now()},
        )
        mission["best_score"] = max(int(mission.get("best_score", 0)), max(0, score))
        mission["completions"] = int(mission.get("completions", 0)) + 1
        mission["last_completed_at"] = _now()
        _refresh_achievements(record)
        record["updated_at"] = _now()
        _save(data)
        return _summary(record)


def save_last_code(user_id: str, mode: str, code: str) -> dict:
    if mode not in CODE_MODES:
        raise ValueError(f"Unsupported code mode: {mode}")
    if not code.strip() or len(code) > MAX_SAVED_CODE_LENGTH:
        raise ValueError("Saved code must contain 1 to 20000 characters")
    with _lock:
        data = _load()
        record = _ensure_record(data, user_id)
        record["last_code"][mode] = {"code": code, "updated_at": _now()}
        record["updated_at"] = _now()
        _save(data)
        return _summary(record)


def record_challenge_result(
    user_id: str,
    *,
    difficulty: str,
    map_id: int,
    winner: str,
    score: int,
    shots: int,
    hits: int,
    walls_destroyed: int,
    code: str | None = None,
) -> dict:
    if difficulty not in {"easy", "medium", "hard"} or map_id not in {1, 2, 3}:
        raise ValueError("Invalid challenge result")
    with _lock:
        data = _load()
        record = _ensure_record(data, user_id)
        challenge = record["challenge"]
        challenge["matches"] = int(challenge.get("matches", 0)) + 1
        result_key = "wins" if winner == "PLAYER" else "losses" if winner == "AI" else "draws"
        challenge[result_key] = int(challenge.get(result_key, 0)) + 1
        challenge["best_score"] = max(int(challenge.get("best_score", 0)), max(0, score))
        challenge["shots"] = int(challenge.get("shots", 0)) + max(0, shots)
        challenge["hits"] = int(challenge.get("hits", 0)) + max(0, hits)
        challenge["walls_destroyed"] = int(challenge.get("walls_destroyed", 0)) + max(
            0, walls_destroyed
        )
        difficulties = challenge.setdefault("difficulties", {})
        difficulty_stats = difficulties.setdefault(difficulty, _default_stats())
        difficulty_stats["matches"] = int(difficulty_stats.get("matches", 0)) + 1
        difficulty_stats[result_key] = int(difficulty_stats.get(result_key, 0)) + 1
        maps = challenge.setdefault("maps", {})
        map_stats = maps.setdefault(str(map_id), _default_stats())
        map_stats["matches"] = int(map_stats.get("matches", 0)) + 1
        map_stats[result_key] = int(map_stats.get(result_key, 0)) + 1
        if code and code.strip():
            if len(code) > MAX_SAVED_CODE_LENGTH:
                raise ValueError("Saved code must contain at most 20000 characters")
            record["last_code"]["challenge"] = {"code": code, "updated_at": _now()}
        _refresh_achievements(record)
        record["updated_at"] = _now()
        _save(data)
        return _summary(record)


def record_pvp_result(user_id: str, result: str) -> dict:
    if result not in {"win", "loss", "draw"}:
        raise ValueError("Invalid PvP result")
    with _lock:
        data = _load()
        record = _ensure_record(data, user_id)
        pvp = record["pvp"]
        pvp["matches"] = int(pvp.get("matches", 0)) + 1
        result_key = {"win": "wins", "loss": "losses", "draw": "draws"}[result]
        pvp[result_key] = int(pvp.get(result_key, 0)) + 1
        _refresh_achievements(record)
        record["updated_at"] = _now()
        _save(data)
        return _summary(record)


def get_pvp_rating(user_id: str) -> int:
    """Return the durable server rating, creating a profile when necessary."""
    with _lock:
        data = _load()
        record = _ensure_record(data, user_id)
        rating = max(100, int(record["pvp"].get("rating", 1000)))
        record["pvp"]["rating"] = rating
        _save(data)
        return rating


def get_pvp_leaderboard(limit: int = 50) -> list[dict]:
    with _lock:
        data = _load()
        entries = []
        for user_id, raw_record in data.items():
            if not isinstance(raw_record, dict):
                continue
            record = _ensure_record(data, str(user_id))
            pvp = {**_default_stats(), **record.get("pvp", {})}
            entries.append(
                {
                    "user_id": str(user_id),
                    "name": record.get("pvp_display_name") or "Commander",
                    "rating": max(100, int(pvp.get("rating", 1000))),
                    "matches": int(pvp.get("matches", 0)),
                    "wins": int(pvp.get("wins", 0)),
                    "losses": int(pvp.get("losses", 0)),
                    "draws": int(pvp.get("draws", 0)),
                }
            )
        entries.sort(key=lambda item: (-item["rating"], -item["wins"], item["name"]))
        return entries[: max(1, min(100, limit))]


def record_pvp_match(
    *,
    match_id: str,
    room_code: str,
    map_id: int,
    player_ids: dict[str, str],
    player_names: dict[str, str],
    winner: str,
    hp: dict[str, int],
    reason: str,
) -> dict[str, dict]:
    """Atomically record one backend-confirmed match for both participants."""
    if winner not in {"1", "2", "draw"} or set(player_ids) != {"1", "2"}:
        raise ValueError("Invalid PvP match result")
    if map_id not in {1, 2, 3}:
        raise ValueError("Invalid PvP map")
    with _lock:
        data = _load()
        records = {slot: _ensure_record(data, str(player_ids[slot])) for slot in ("1", "2")}
        already_recorded = any(
            match_id in record.setdefault("pvp_recorded_matches", [])
            for record in records.values()
        )
        if already_recorded:
            return {slot: _summary(record) for slot, record in records.items()}

        ratings = {
            slot: max(100, int(records[slot]["pvp"].get("rating", 1000)))
            for slot in ("1", "2")
        }
        expected_one = 1 / (1 + 10 ** ((ratings["2"] - ratings["1"]) / 400))
        score_one = 0.5 if winner == "draw" else 1.0 if winner == "1" else 0.0
        delta_one = round(24 * (score_one - expected_one))
        deltas = {"1": delta_one, "2": -delta_one}
        finished_at = _now()

        for slot in ("1", "2"):
            opponent = "2" if slot == "1" else "1"
            record = records[slot]
            pvp = record["pvp"]
            result = "draw" if winner == "draw" else "win" if winner == slot else "loss"
            result_key = {"win": "wins", "loss": "losses", "draw": "draws"}[result]
            pvp["matches"] = int(pvp.get("matches", 0)) + 1
            pvp[result_key] = int(pvp.get(result_key, 0)) + 1
            pvp["rating"] = max(100, ratings[slot] + deltas[slot])
            record["pvp_display_name"] = str(player_names.get(slot) or "Commander")[:32]
            history = record.setdefault("pvp_history", [])
            history.insert(
                0,
                {
                    "match_id": match_id,
                    "room_code": room_code,
                    "map_id": map_id,
                    "opponent": str(player_names.get(opponent) or "Commander")[:32],
                    "result": result,
                    "rating_delta": deltas[slot],
                    "rating_after": pvp["rating"],
                    "hp": max(0, int(hp.get(slot, 0))),
                    "opponent_hp": max(0, int(hp.get(opponent, 0))),
                    "reason": reason,
                    "finished_at": finished_at,
                    "server_confirmed": True,
                },
            )
            del history[30:]
            recorded = record.setdefault("pvp_recorded_matches", [])
            recorded.append(match_id)
            del recorded[:-100]
            _refresh_achievements(record)
            record["updated_at"] = finished_at
        _save(data)
        return {slot: _summary(record) for slot, record in records.items()}


def save_named_strategy(
    user_id: str, *, mode: str, name: str, code: str, strategy_id: str | None = None
) -> dict:
    if mode not in CODE_MODES:
        raise ValueError(f"Unsupported code mode: {mode}")
    clean_name = name.strip()
    if not clean_name or len(clean_name) > 24:
        raise ValueError("Strategy name must contain 1 to 24 characters")
    if not code.strip() or len(code) > MAX_SAVED_CODE_LENGTH:
        raise ValueError("Strategy code must contain 1 to 20000 characters")
    with _lock:
        data = _load()
        record = _ensure_record(data, user_id)
        strategies = record["strategies"].setdefault(mode, [])
        existing = next(
            (
                item
                for item in strategies
                if (strategy_id and item.get("id") == strategy_id)
                or item.get("name", "").casefold() == clean_name.casefold()
            ),
            None,
        )
        if existing is None and len(strategies) >= 8:
            raise ValueError("A maximum of 8 strategies can be saved per mode")
        item = existing or {"id": uuid.uuid4().hex[:12], "created_at": _now()}
        item.update({"name": clean_name, "code": code, "updated_at": _now()})
        if existing is None:
            strategies.insert(0, item)
        else:
            strategies.remove(existing)
            strategies.insert(0, item)
        record["updated_at"] = _now()
        _save(data)
        return item


def delete_named_strategy(user_id: str, strategy_id: str) -> bool:
    with _lock:
        data = _load()
        record = _ensure_record(data, user_id)
        for strategies in record["strategies"].values():
            for item in list(strategies):
                if item.get("id") == strategy_id:
                    strategies.remove(item)
                    record["updated_at"] = _now()
                    _save(data)
                    return True
        return False
