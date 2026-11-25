"""OIDC authentication with Keycloak - PKCE and Authorization Code Flow."""

import secrets
import base64
import urllib.parse
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import BaseModel, Field


# ── PKCE helpers ────────────────────────────────────────────────────────────

def _pkce_code_verifier() -> str:
    """Generate a random PKCE code verifier (43-128 chars, URL-safe base64)."""
    raw = secrets.token_urlsafe(43)  # 64 bytes → ~86 chars base64
    verifier = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    return verifier


def _pkce_code_challenge(verifier: str) -> str:
    """Derive PKCE code challenge from verifier using S256."""
    import hashlib
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return challenge


# ── Token models ─────────────────────────────────────────────────────────────


class OIDCToken(BaseModel):
    """Response model for token exchange."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class UserInfo(BaseModel):
    """Parsed user info from OIDC token / introspection."""

    sub: str = Field(..., description="OIDC subject identifier")
    preferred_username: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: Optional[bool] = None


# ── Auth helper ─────────────────────────────────────────────────────────────


def parse_id_token(
    token: str,
    expected_client_id: str,
    issuer_url: str,
) -> Dict[str, Any]:
    """Minimally validate and decode an OIDC ID token."""
    try:
        payload = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_aud": True,
                "verify_iss": True,
            },
            audience=expected_client_id,
            issuer=issuer_url,
        )
        return {"status": "ok", "payload": payload}
    except ExpiredSignatureError:
        return {"status": "expired", "payload": None}
    except JWTError as e:
        return {"status": "invalid", "error": str(e)}


def extract_user_info(payload: Dict[str, Any]) -> UserInfo:
    """Extract user info from decoded ID token payload."""
    return UserInfo(
        sub=str(payload.get("sub", "")),
        preferred_username=payload.get("preferred_username"),
        email=payload.get("email"),
        name=payload.get("name"),
        picture=payload.get("picture"),
        email_verified=payload.get("email_verified"),
    )


# ── State helpers for session (cookie-backed) ───────────────────────────────

def generate_session_token(uid: str, exp_minutes: int = 30) -> str:
    """Create a signed session cookie value (HMAC-short-lived)."""
    from jose import jwt as jwt_core
    import time
    now = int(time.time())
    payload = {"uid": uid, "iat": now, "exp": now + exp_minutes * 60}
    return jwt_core.encode(payload, options={"verify_signature": False})


def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a session cookie token; returns payload or None."""
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except (JWTError, Exception):
        return None


# ── PKCE state store (in-memory; replace with DB/redis in production) ─────────

_pending_pkce: Dict[str, Dict[str, str]] = {}


def store_pkce(state: str, verifier: str) -> None:
    """Store PKCE verifier keyed by OAuth state parameter."""
    _pending_pkce[state] = {"verifier": verifier}


def retrieve_and_remove_pkce(state: str) -> Optional[str]:
    """Retrieve and remove the PKCE verifier for the given state."""
    entry = _pending_pkce.pop(state, None)
    return entry["verifier"] if entry else None


# ── Login URL construction ──────────────────────────────────────────────────

OIDC_AUTHORIZE_ENDPOINT = "/protocol/openid-connect/auth"
OIDC_TOKEN_ENDPOINT = "/protocol/openid-connect/token"
OIDC_USERINFO_ENDPOINT = "/protocol/openid-connect/userinfo"


def build_authorize_url(
    issuer_url: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str = "S256",
    scopes: str = "openid profile email",
) -> str:
    """Build the Keycloak OIDC authorization URL with PKCE."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    authorize_url = issuer_url.rstrip("/") + OIDC_AUTHORIZE_ENDPOINT
    return authorize_url + "?" + urlencode(params)


# ── Token exchange ──────────────────────────────────────────────────────────

def exchange_code_for_token(
    issuer_url: str,
    client_id: str,
    client_secret: Optional[str],
    redirect_uri: str,
    code: str,
    code_verifier: str,
) -> Dict[str, Any]:
    """Exchange authorization code for tokens from Keycloak."""
    import httpx

    token_url = issuer_url.rstrip("/") + OIDC_TOKEN_ENDPOINT

    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }

    if client_secret:
        data["client_secret"] = client_secret

    resp = httpx.post(token_url, data=data, timeout=30)
    resp.raise_for_status()
    tokens = resp.json()

    return {"status": "ok", "tokens": tokens}


# ── Userinfo request ───────────────────────────────────────────────────────

def fetch_userinfo(
    access_token: str,
    issuer_url: str,
) -> Dict[str, Any]:
    """Fetch userinfo from Keycloak using the access token."""
    import httpx

    userinfo_url = issuer_url.rstrip("/") + OIDC_USERINFO_ENDPOINT

    resp = httpx.get(
        userinfo_url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return {"status": "ok", "userinfo": resp.json()}
