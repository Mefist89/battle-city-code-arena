import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

# ── App Configuration ─────────────────────────────────────────────────────────

APP_TITLE = "CODETANK ARENA API"
APP_VERSION = "0.1.0"

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://localhost:5174,http://localhost:3000"
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]

# PvP abuse protection. For multi-worker production deployments, use Redis for
# shared rate-limit counters and room ownership state.
PVP_CREATE_LIMIT = int(os.getenv("PVP_CREATE_LIMIT", "3"))
PVP_JOIN_LIMIT = int(os.getenv("PVP_JOIN_LIMIT", "10"))
PVP_WS_CONNECT_LIMIT = int(os.getenv("PVP_WS_CONNECT_LIMIT", "5"))
PVP_WS_MESSAGE_LIMIT = int(os.getenv("PVP_WS_MESSAGE_LIMIT", "30"))
PVP_RATE_WINDOW_SECONDS = int(os.getenv("PVP_RATE_WINDOW_SECONDS", "60"))
PVP_WS_MESSAGE_WINDOW_SECONDS = int(os.getenv("PVP_WS_MESSAGE_WINDOW_SECONDS", "10"))
PVP_MAX_ROOMS = int(os.getenv("PVP_MAX_ROOMS", "200"))
PVP_MAX_ACTIVE_ROOMS_PER_USER = int(os.getenv("PVP_MAX_ACTIVE_ROOMS_PER_USER", "1"))
PVP_WAITING_ROOM_TTL_SECONDS = int(os.getenv("PVP_WAITING_ROOM_TTL_SECONDS", "900"))
PVP_FINISHED_ROOM_TTL_SECONDS = int(os.getenv("PVP_FINISHED_ROOM_TTL_SECONDS", "300"))
PVP_ACTIVE_ROOM_TTL_SECONDS = int(os.getenv("PVP_ACTIVE_ROOM_TTL_SECONDS", "3600"))
PVP_WS_IDLE_TIMEOUT_SECONDS = int(os.getenv("PVP_WS_IDLE_TIMEOUT_SECONDS", "300"))
PVP_WS_MAX_MESSAGE_BYTES = int(os.getenv("PVP_WS_MAX_MESSAGE_BYTES", "32768"))

# ── Authentication ────────────────────────────────────────────────────────────

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
).strip()
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "").strip()
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
GITHUB_REDIRECT_URI = os.getenv(
    "GITHUB_REDIRECT_URI", "http://localhost:8000/auth/github/callback"
).strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5174").rstrip("/")

# Use a dedicated value in production. An OAuth client secret is an acceptable
# high-entropy fallback for local development and never leaves the backend.
AUTH_SESSION_SECRET = (
    os.getenv("AUTH_SESSION_SECRET", "").strip()
    or GOOGLE_CLIENT_SECRET
    or GITHUB_CLIENT_SECRET
)
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"

# ── Session Settings ──────────────────────────────────────────────────────────

SESSION_TTL_SECONDS = 1800  # 30 minutes of inactivity before cleanup
MAX_SESSIONS = 200          # Maximum concurrent sessions

# ── Map Constants ─────────────────────────────────────────────────────────────

MAP_WIDTH = 10   # X: 0..9
MAP_HEIGHT = 8   # Y: 0..7
