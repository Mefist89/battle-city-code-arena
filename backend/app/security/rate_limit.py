from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from threading import Lock


class SlidingWindowRateLimiter:
    """Small in-memory limiter for the single-process MVP backend.

    Production deployments with multiple backend workers should replace this
    storage with Redis so every worker shares the same counters.
    """

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def consume(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        *,
        now: float | None = None,
    ) -> tuple[bool, int]:
        current = time.monotonic() if now is None else now
        cutoff = current - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, math.ceil(window_seconds - (current - events[0])))
                return False, retry_after
            events.append(current)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


pvp_rate_limiter = SlidingWindowRateLimiter()
game_rate_limiter = SlidingWindowRateLimiter()
