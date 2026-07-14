from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from httpx import HTTPError
from pydantic import BaseModel, Field

from app.config import (
    FRONTEND_URL,
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GITHUB_REDIRECT_URI,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)
from app.profile_store import complete_mission, get_progress
from app.simulator.pvp_engine import disconnect_user


router = APIRouter(prefix="/auth", tags=["auth"])
oauth = OAuth()


class MissionProgressRequest(BaseModel):
    score: int = Field(default=0, ge=0, le=10_000_000)

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    oauth.register(
        name="github",
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )


def _google_client():
    client = oauth.create_client("google")
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured on the server",
        )
    return client


def _github_client():
    client = oauth.create_client("github")
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="GitHub OAuth is not configured on the server",
        )
    return client


def _session_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _safe_next_path(value: str | None) -> str:
    if not value or len(value) > 500 or not value.startswith("/") or value.startswith("//"):
        return "/auth?oauth=success"
    return value


def _oauth_success_redirect(request: Request) -> str:
    next_path = _safe_next_path(request.session.pop("oauth_next", None))
    return f"{FRONTEND_URL}{next_path}"


@router.get("/status")
async def auth_status():
    return {
        "google": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "github": bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET),
    }


@router.get("/google", name="google_login")
async def google_login(request: Request, next: str | None = None):
    google = _google_client()
    request.session["oauth_next"] = _safe_next_path(next)
    return await google.authorize_redirect(
        request,
        GOOGLE_REDIRECT_URI,
        prompt="select_account",
    )


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request):
    google = _google_client()
    try:
        token = await google.authorize_access_token(request)
    except OAuthError:
        return RedirectResponse(f"{FRONTEND_URL}/auth?oauth=error", status_code=303)

    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        return RedirectResponse(f"{FRONTEND_URL}/auth?oauth=error", status_code=303)
    if userinfo.get("email_verified") is False:
        return RedirectResponse(f"{FRONTEND_URL}/auth?oauth=unverified", status_code=303)

    request.session["user"] = {
        "id": userinfo.get("sub"),
        "email": userinfo.get("email"),
        "name": userinfo.get("name") or userinfo.get("email"),
        "picture": userinfo.get("picture"),
        "provider": "google",
    }
    return RedirectResponse(_oauth_success_redirect(request), status_code=303)


@router.get("/github", name="github_login")
async def github_login(request: Request, next: str | None = None):
    github = _github_client()
    request.session["oauth_next"] = _safe_next_path(next)
    return await github.authorize_redirect(request, GITHUB_REDIRECT_URI)


@router.get("/github/callback", name="github_callback")
async def github_callback(request: Request):
    github = _github_client()
    try:
        token = await github.authorize_access_token(request)
        profile_response = await github.get("user", token=token)
        profile_response.raise_for_status()
        userinfo = profile_response.json()

        email = userinfo.get("email")
        if not email:
            emails_response = await github.get("user/emails", token=token)
            emails_response.raise_for_status()
            emails = emails_response.json()
            primary = next(
                (item for item in emails if item.get("primary") and item.get("verified")),
                None,
            )
            verified = next((item for item in emails if item.get("verified")), None)
            selected = primary or verified
            email = selected.get("email") if selected else None
    except (OAuthError, HTTPError, TypeError, ValueError):
        return RedirectResponse(f"{FRONTEND_URL}/auth?oauth=error", status_code=303)

    if not userinfo.get("id") or not email:
        return RedirectResponse(f"{FRONTEND_URL}/auth?oauth=error", status_code=303)

    request.session["user"] = {
        "id": f"github:{userinfo['id']}",
        "email": email,
        "name": userinfo.get("name") or userinfo.get("login") or email,
        "picture": userinfo.get("avatar_url"),
        "provider": "github",
    }
    return RedirectResponse(_oauth_success_redirect(request), status_code=303)


@router.get("/me")
async def current_user(request: Request):
    user = request.session.get("user")
    return {"authenticated": bool(user), "user": user}


@router.get("/profile")
async def profile(request: Request):
    user = _session_user(request)
    return {"user": user, "progress": get_progress(user["id"])}


@router.post("/progress/missions/{mission_id}")
async def save_mission_progress(
    mission_id: int,
    payload: MissionProgressRequest,
    request: Request,
):
    if mission_id < 1 or mission_id > 9:
        raise HTTPException(status_code=400, detail="Mission ID must be between 1 and 9")
    user = _session_user(request)
    return {"progress": complete_mission(user["id"], mission_id, payload.score)}


@router.post("/logout")
async def logout(request: Request):
    user = request.session.get("user")
    if user and user.get("id"):
        await disconnect_user(str(user["id"]))
    request.session.clear()
    return {"ok": True}
