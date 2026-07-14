import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import BACKEND_DIR


DATA_FILE = BACKEND_DIR / "data" / "user_progress.json"
_lock = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATA_FILE)


def _summary(record: dict) -> dict:
    missions = record.get("missions", {})
    completed = sorted(int(mission_id) for mission_id in missions)
    return {
        "completed_missions": completed,
        "completed_count": len(completed),
        "total_missions": 9,
        "total_score": sum(int(item.get("best_score", 0)) for item in missions.values()),
        "missions": missions,
        "updated_at": record.get("updated_at"),
    }


def get_progress(user_id: str) -> dict:
    with _lock:
        data = _load()
        record = data.get(user_id, {"missions": {}})
        return _summary(record)


def complete_mission(user_id: str, mission_id: int, score: int) -> dict:
    with _lock:
        data = _load()
        record = data.setdefault(user_id, {"missions": {}, "created_at": _now()})
        missions = record.setdefault("missions", {})
        mission = missions.setdefault(
            str(mission_id),
            {"best_score": 0, "completions": 0, "completed_at": _now()},
        )
        mission["best_score"] = max(int(mission.get("best_score", 0)), max(0, score))
        mission["completions"] = int(mission.get("completions", 0)) + 1
        mission["last_completed_at"] = _now()
        record["updated_at"] = _now()
        _save(data)
        return _summary(record)
