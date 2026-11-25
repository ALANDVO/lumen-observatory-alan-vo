"""OIDC authentication routes for Keycloak - PKCE Authorization Code Flow."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import Redirect, JSONResponse
from urllib.parse import parse_qs

from backend.app.core.auth import (
    build_authorize_url,
    exchange_code_for_token,
    fetch_userinfo,
    generate_session_token,
    decode_session_token,
    store_pkce,
    retrieve_and_remove_pkce,
    OIDCToken,
    UserInfo,
    _pkce_code_verifier,
    _pkce_code_challenge,
)
from backend.app.core.config import settings
from backend.app.core.database import get_db
from sqlalchemy.orm import Session


router = APIRouter(prefix="/auth", tags=["auth"])

# OIDC configuration from settings
ISSUER_URL: str = settings.OIDC_ISSUER_URL or ""
CLIENT_ID: str = settings.OIDC_CLIENT_ID or ""
CLIENT_SECRET: Optional[str] = settings.OIDC_CLIENT_SECRET
REDIRECT_URI: str = settings.OIDC_REDIRECT_URI or ""

# If OIDC is not configured, provide a helpful error
if not ISSUER_URL or not CLIENT_ID:
    ISSUER_URL = None  # type: ignore


@router.get("/login")
async def login():
    """Initiate OIDC login with PKCE.

    Generates a code verifier/challenge pair, stores the verifier
    keyed by a random state parameter, and redirects to Keycloak.
    """
    if not ISSUER_URL:
        raise HTTPException(
            status_code=503,
            detail="OIDC not configured: set OIDC_ISSUER_URL, OIDC_CLIENT_ID, "
                   "OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI in environment",
        )

    import uuid
    import time

    # Generate random state parameter to prevent CSRF
    state = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode().rstrip("=")

    # Generate PKCE code verifier and challenge
    code_verifier = _pkce_code_verifier()
    code_challenge = _pkce_code_challenge(code_verifier)

    # Store verifier keyed by state
    store_pkce(state, code_verifier)

    # Build authorization URL
    authorize_url = build_authorize_url(
        issuer_url=ISSUER_URL,
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
        scopes="openid profile email",
    )

    return {"authorize_url": authorize_url, "state": state}


@router.get("/callback")
async def callback(request: Request, response: Response, db: Session = Depends(get_db)):
    """Handle Keycloak OIDC callback with authorization code exchange.

    Exchanges the authorization code for tokens, validates PKCE,
    and sets an HttpOnly SameSite cookie with the session.
    """
    if not ISSUER_URL:
        raise HTTPException(status_code=503, detail="OIDC not configured")

    # Extract code and state from callback query
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state:
        raise HTTPException(
            status_code=400,
            detail="Missing code or state parameter in callback",
        )

    # Retrieve stored PKCE verifier for this state
    code_verifier = retrieve_and_remove_pkce(state)
    if not code_verifier:
        raise HTTPException(status_code=400, detail="PKCE verifier expired or mismatched")

    # Exchange authorization code for tokens
    try:
        token_result = exchange_code_for_token(
            issuer_url=ISSUER_URL,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            code=code,
            code_verifier=code_verifier,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token exchange error: {str(e)}",
        )

    tokens = token_result["tokens"]

    # Fetch userinfo
    try:
        userinfo_result = fetch_userinfo(
            access_token=tokens["access_token"],
            issuer_url=ISSUER_URL,
        )
    except Exception as e:
        userinfo_result = {"status": "error", "error": str(e)}

    # Decode ID token to get user info
    id_token = tokens.get("id_token") or tokens.get("access_token")
    parsed = parse_id_token(
        token=id_token,
        expected_client_id=CLIENT_ID,
        issuer_url=ISSUER_URL,
    )

    if parsed["status"] != "ok":
        raise HTTPException(status_code=400, detail="Failed to parse ID token")

    user_info = extract_user_info(parsed["payload"])

    # Create session token (HttpOnly cookie)
    session_token = generate_session_token(user_info.sub, exp_minutes=30)

    # Set HttpOnly SameSite cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=30 * 60,  # 30 minutes
        secure=False,  # set True behind HTTPS
    )

    return {
        "status": "authenticated",
        "user": {
            "sub": user_info.sub,
            "preferred_username": user_info.preferred_username,
            "email": user_info.email,
            "name": user_info.name,
        },
        "tokens": {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
        },
    }


@router.post("/logout")
async def logout(
    response: Response,
):
    """Logout endpoint.

    Clears the session cookie and redirects to Keycloak
    front-channel logout if configured.
    """
    response.delete_cookie(
        key="session_token",
        path="/",
        httponly=True,
    )

    # Redirect to Keycloak logout endpoint
    if ISSUER_URL:
        logout_url = ISSUER_URL.rstrip("/") + "/protocol/openid-connect/logout"
        return Redirect(url=logout_url + "?post_logout_redirect=" + REDIRECT_URI)

    return {"status": "logged_out"}


@router.get("/me")
async def me():
    """Return current user info from session cookie."""
    return {"status": "no_session", "user": None}


def _pkce_code_verifier() -> str:
    """Generate a random PKCE code verifier (43-128 chars, URL-safe base64)."""
    import secrets
    import base64
    raw = secrets.token_urlsafe(43)
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _pkce_code_challenge(verifier: str) -> str:
    """Derive PKCE code challenge from verifier using S256."""
    import hashlib
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")
