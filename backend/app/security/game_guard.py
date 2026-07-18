from fastapi import HTTPException, Request

from app.config import GAME_RATE_WINDOW_SECONDS
from app.security.rate_limit import game_rate_limiter


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def enforce_game_rate_limit(
    request: Request,
    action: str,
    *,
    ip_limit: int,
    session_id: str | None = None,
    session_limit: int | None = None,
) -> None:
    """Apply an IP limit and, when available, a separate session limit."""
    ip_allowed, ip_retry = game_rate_limiter.consume(
        f"game:{action}:ip:{client_ip(request)}",
        ip_limit,
        GAME_RATE_WINDOW_SECONDS,
    )
    if not ip_allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many game requests. Try again later",
            headers={"Retry-After": str(ip_retry)},
        )

    if session_id and session_limit:
        # Session identifiers are short, but cap the key defensively before
        # validation so oversized attacker-controlled headers cannot grow it.
        safe_session_id = session_id[:64]
        session_allowed, session_retry = game_rate_limiter.consume(
            f"game:{action}:session:{safe_session_id}",
            session_limit,
            GAME_RATE_WINDOW_SECONDS,
        )
        if not session_allowed:
            raise HTTPException(
                status_code=429,
                detail="Too many requests for this game session. Try again later",
                headers={"Retry-After": str(session_retry)},
            )
