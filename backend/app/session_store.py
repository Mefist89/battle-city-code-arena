# ── Session Store ─────────────────────────────────────────────────────────────
# In-memory session manager: each player gets their own MissionState via UUID.

import time
import uuid
from contextlib import contextmanager
from threading import RLock
from typing import Iterator

from app.config import SESSION_TTL_SECONDS, MAX_SESSIONS
from app.simulator.mission_engine import MissionState


class SessionStore:
    """Manages per-player game sessions with TTL-based cleanup."""

    def __init__(self) -> None:
        self._sessions: dict[str, MissionState] = {}
        self._timestamps: dict[str, float] = {}
        self._session_locks: dict[str, RLock] = {}
        self._active_sessions: set[str] = set()
        self._lock = RLock()

    def create(self, mission_id: int = 1) -> tuple[str, MissionState]:
        """Create a new session, reset it to the given mission, return (id, state)."""
        with self._lock:
            self._cleanup_unlocked()
            session_id = uuid.uuid4().hex[:12]
            state = MissionState()
            state.reset(mission_id)
            self._sessions[session_id] = state
            self._timestamps[session_id] = time.time()
            self._session_locks[session_id] = RLock()
            return session_id, state

    def get(self, session_id: str) -> MissionState | None:
        """Look up a session by ID. Returns None if expired or not found."""
        with self._lock:
            return self._get_unlocked(session_id)

    def _get_unlocked(self, session_id: str) -> MissionState | None:
        if session_id not in self._sessions:
            return None
        if time.time() - self._timestamps[session_id] > SESSION_TTL_SECONDS:
            if session_id not in self._active_sessions:
                self._remove_unlocked(session_id)
            return None
        self._timestamps[session_id] = time.time()
        return self._sessions[session_id]

    @contextmanager
    def locked(self, session_id: str) -> Iterator[MissionState | None]:
        """Serialize all reads and mutations for one game session."""
        with self._lock:
            session_lock = self._session_locks.get(session_id)
        if session_lock is None:
            yield None
            return

        with session_lock:
            with self._lock:
                state = self._get_unlocked(session_id)
                if state is not None:
                    self._active_sessions.add(session_id)
            try:
                yield state
            finally:
                if state is not None:
                    with self._lock:
                        self._active_sessions.discard(session_id)

    def reset(self, session_id: str, mission_id: int) -> MissionState | None:
        """Reset an existing session to a new mission. Returns None if not found."""
        with self.locked(session_id) as state:
            if state is None:
                return None
            state.reset(mission_id)
            return state

    def _remove_unlocked(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._timestamps.pop(session_id, None)
        self._session_locks.pop(session_id, None)
        self._active_sessions.discard(session_id)

    def _cleanup(self) -> None:
        """Remove expired sessions and enforce MAX_SESSIONS limit."""
        with self._lock:
            self._cleanup_unlocked()

    def _cleanup_unlocked(self) -> None:
        now = time.time()
        expired = [
            sid for sid, ts in self._timestamps.items()
            if now - ts > SESSION_TTL_SECONDS and sid not in self._active_sessions
        ]
        for sid in expired:
            self._remove_unlocked(sid)

        # If still over limit, remove oldest sessions
        if len(self._sessions) >= MAX_SESSIONS:
            sorted_by_age = sorted(
                (
                    item
                    for item in self._timestamps.items()
                    if item[0] not in self._active_sessions
                ),
                key=lambda x: x[1],
            )
            to_remove = len(self._sessions) - MAX_SESSIONS + 1
            for sid, _ in sorted_by_age[:to_remove]:
                self._remove_unlocked(sid)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._sessions)


# ── Global store instance ────────────────────────────────────────────────────
store = SessionStore()
