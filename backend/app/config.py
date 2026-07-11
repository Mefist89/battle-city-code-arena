# ── App Configuration ─────────────────────────────────────────────────────────

APP_TITLE = "Battle City: Code Arena API"
APP_VERSION = "0.1.0"

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
]

# ── Session Settings ──────────────────────────────────────────────────────────

SESSION_TTL_SECONDS = 1800  # 30 minutes of inactivity before cleanup
MAX_SESSIONS = 200          # Maximum concurrent sessions

# ── Map Constants ─────────────────────────────────────────────────────────────

MAP_WIDTH = 10   # X: 0..9
MAP_HEIGHT = 8   # Y: 0..7
