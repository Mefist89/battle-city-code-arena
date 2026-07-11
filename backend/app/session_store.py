# ── Session Store ─────────────────────────────────────────────────────────────
# In-memory session manager: each player gets their own MissionState via UUID.

import time
import uuid

from app.config import SESSION_TTL_SECONDS, MAX_SESSIONS
from app.simulator.mission_engine import MissionState


class SessionStore:
    """Manages per-player game sessions with TTL-based cleanup."""

    def __init__(self) -> None:
        self._sessions: dict[str, MissionState] = {}
        self._timestamps: dict[str, float] = {}

    def create(self, mission_id: int = 1) -> tuple[str, MissionState]:
        """Create a new session, reset it to the given mission, return (id, state)."""
        self._cleanup()
        session_id = uuid.uuid4().hex[:12]
        state = MissionState()
        state.reset(mission_id)
        self._sessions[session_id] = state
        self._timestamps[session_id] = time.time()
        return session_id, state

    def get(self, session_id: str) -> MissionState | None:
        """Look up a session by ID. Returns None if expired or not found."""
        if session_id not in self._sessions:
            return None
        # Check TTL
        if time.time() - self._timestamps[session_id] > SESSION_TTL_SECONDS:
            self._remove(session_id)
            return None
        # Touch timestamp on access
        self._timestamps[session_id] = time.time()
        return self._sessions[session_id]

    def reset(self, session_id: str, mission_id: int) -> MissionState | None:
        """Reset an existing session to a new mission. Returns None if not found."""
        state = self.get(session_id)
        if state is None:
            return None
        state.reset(mission_id)
        return state

    def _remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._timestamps.pop(session_id, None)

    def _cleanup(self) -> None:
        """Remove expired sessions and enforce MAX_SESSIONS limit."""
        now = time.time()
        expired = [
            sid for sid, ts in self._timestamps.items()
            if now - ts > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            self._remove(sid)

        # If still over limit, remove oldest sessions
        if len(self._sessions) >= MAX_SESSIONS:
            sorted_by_age = sorted(self._timestamps.items(), key=lambda x: x[1])
            to_remove = len(self._sessions) - MAX_SESSIONS + 1
            for sid, _ in sorted_by_age[:to_remove]:
                self._remove(sid)

    @property
    def count(self) -> int:
        return len(self._sessions)


# ── Global store instance ────────────────────────────────────────────────────
store = SessionStore()
