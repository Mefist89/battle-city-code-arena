# CODETANK ARENA security

## PvP protections

- Creating or joining a room and opening a room WebSocket require a valid Google or GitHub session.
- Each room slot is bound to the OAuth provider account ID. Browser-supplied names and slot numbers are not trusted.
- The backend validates WebSocket Origin, message shape, allowed actions, message size, duplicate connections, and idle time.
- Per-account and per-IP limits apply to room creation, joining, WebSocket connections, and messages.
- A user may occupy one active room. Global room count and room lifetimes are limited, and expired rooms are removed automatically.
- Signing out closes the user's active PvP socket.

## Production checklist

1. Set a unique high-entropy `AUTH_SESSION_SECRET` and use `AUTH_COOKIE_SECURE=true`.
2. Set `CORS_ORIGINS` and `ALLOWED_HOSTS` to the real HTTPS hostnames. See `backend/.env.example`.
3. Keep OAuth callback URLs restricted to the real backend domain.
4. Run behind an HTTPS reverse proxy with WebSocket support and a WAF, such as Cloudflare.
5. Add proxy-level IP limits for `/api/rooms*`, `/auth/*`, and `/ws/rooms/*`.
6. The current in-memory limiter and room store support one backend process. Move both to Redis before using multiple backend workers.
7. Do not commit `backend/.env`, OAuth client secrets, session secrets, runtime room files, or user progress files.
