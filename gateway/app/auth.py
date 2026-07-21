"""
gateway/app/auth.py
───────────────────
IBM App ID JWT validation middleware.

Flow:
  1. Extract Bearer token from Authorization header.
  2. Fetch JWKS from App ID (cached in-process with 5-minute TTL).
  3. Verify JWT signature, expiry, issuer, and audience.
  4. Return decoded claims dict on success.

All validation failures raise HTTP 401 so FastAPI returns a clean JSON error
before the request ever reaches an upstream route handler.
"""

import time
from typing import Any

import requests
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from gateway.app.config import GatewaySettings, get_settings

# ── JWKS in-process cache ─────────────────────────────────────────────────────
_jwks_cache: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 300   # re-fetch every 5 minutes

_bearer = HTTPBearer(auto_error=True)


def _get_jwks(settings: GatewaySettings) -> list[dict]:
    """Return JWKS keys, refreshing cache when TTL has elapsed."""
    now = time.monotonic()
    if _jwks_cache["keys"] is None or (now - _jwks_cache["fetched_at"]) > _JWKS_TTL_SECONDS:
        response = requests.get(settings.appid_jwks_url, timeout=10)
        response.raise_for_status()
        _jwks_cache["keys"] = response.json().get("keys", [])
        _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]   # type: ignore[return-value]


def _decode_token(token: str, settings: GatewaySettings) -> dict[str, Any]:
    """
    Validate and decode a JWT issued by IBM App ID.

    Raises:
        HTTPException(401) for any validation failure.
    """
    try:
        keys = _get_jwks(settings)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch JWKS from App ID: {exc}",
        ) from exc

    # Build a dict that python-jose can use directly
    jwks = {"keys": keys}

    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.appid_audience,
            issuer=settings.appid_issuer_url,
            options={"verify_at_hash": False},
        )
        return claims
    except JWTError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {exc}",
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: GatewaySettings = Depends(get_settings),
) -> dict[str, Any]:
    """
    FastAPI dependency — validates the Bearer JWT and returns the claims dict.

    Usage in a route:
        @router.post("/...")
        async def handler(user: dict = Depends(get_current_user)):
            subject = user["sub"]
    """
    return _decode_token(credentials.credentials, settings)


def require_scope(required_scope: str):
    """
    Returns a FastAPI dependency that checks for a specific scope in the token.

    Usage:
        @router.post("/design", dependencies=[Depends(require_scope("design:write"))])
    """
    def _check(user: dict = Depends(get_current_user)) -> dict:
        scopes: list[str] = user.get("scope", "").split()
        if required_scope not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Required scope '{required_scope}' not present in token.",
            )
        return user

    return _check
