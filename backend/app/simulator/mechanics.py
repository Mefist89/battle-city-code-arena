# ── Game Mechanics ────────────────────────────────────────────────────────────
# Pure utility functions for movement, ray-casting, and line-of-sight checks.
# These functions are stateless — they receive all data through parameters.

from typing import Generator
from app.schemas.game import MOVE_DELTA


def direction_between(x1: int, y1: int, x2: int, y2: int) -> str:
    """Determine the direction from (x1,y1) to (x2,y2)."""
    if x2 > x1: return "RIGHT"
    if x2 < x1: return "LEFT"
    if y2 > y1: return "DOWN"
    return "UP"


def ray_cells(x: int, y: int, direction: str) -> Generator[tuple[int, int], None, None]:
    """Yield cells along a ray starting from (x,y) in the given direction.

    The starting cell itself is NOT yielded — only the cells ahead of it.
    """
    dx, dy = MOVE_DELTA[direction]
    x, y = x + dx, y + dy
    while 0 <= x <= 9 and 0 <= y <= 7:
        yield x, y
        x, y = x + dx, y + dy


def clear_shot(
    x1: int, y1: int,
    x2: int, y2: int,
    walls: dict[tuple[int, int], str],
) -> bool:
    """Check if there is a clear line of fire from (x1,y1) to (x2,y2).

    Returns False if the two points are not on the same row/column,
    or if a wall blocks the path.
    """
    if x1 != x2 and y1 != y2:
        return False
    direction = direction_between(x1, y1, x2, y2)
    for cell in ray_cells(x1, y1, direction):
        if cell == (x2, y2):
            return True
        if cell in walls:
            return False
    return False
