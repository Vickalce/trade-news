from __future__ import annotations

import secrets
import time
from base64 import b64encode
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from api.core.config import settings


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    expires_at_epoch: float | None


_state_expiry: dict[str, float] = {}
_tokens: OAuthTokens | None = None


def _require_oauth_client_settings() -> None:
    if not settings.schwab_client_id:
        raise ValueError("SCHWAB_CLIENT_ID is required")
    if not settings.schwab_client_secret:
        raise ValueError("SCHWAB_CLIENT_SECRET is required")
    if not settings.schwab_redirect_uri:
        raise ValueError("SCHWAB_REDIRECT_URI is required")


def create_oauth_state() -> str:
    state = secrets.token_urlsafe(32)
    _state_expiry[state] = time.time() + (10 * 60)
    return state


def validate_oauth_state(state: str) -> bool:
    expiry = _state_expiry.pop(state, None)
    if expiry is None:
        return False
    return time.time() <= expiry


def build_authorize_url(state: str) -> str:
    _require_oauth_client_settings()

    params = {
        "client_id": settings.schwab_client_id,
        "redirect_uri": settings.schwab_redirect_uri,
        "response_type": "code",
        "state": state,
    }
    if settings.schwab_oauth_scope:
        params["scope"] = settings.schwab_oauth_scope

    return f"{settings.schwab_oauth_authorize_url}?{urlencode(params)}"


def _build_basic_auth_header() -> dict[str, str]:
    creds = f"{settings.schwab_client_id}:{settings.schwab_client_secret}".encode("utf-8")
    return {"Authorization": f"Basic {b64encode(creds).decode('ascii')}"}


def _parse_tokens(payload: dict[str, Any]) -> OAuthTokens:
    access_token = str(payload.get("access_token", "")).strip()
    refresh_token = payload.get("refresh_token")
    expires_in = payload.get("expires_in")

    if not access_token:
        raise ValueError("Schwab token response did not include access_token")

    expires_at = None
    if isinstance(expires_in, (int, float)):
        expires_at = time.time() + float(expires_in)

    return OAuthTokens(
        access_token=access_token,
        refresh_token=str(refresh_token).strip() if refresh_token else None,
        expires_at_epoch=expires_at,
    )


def exchange_code_for_tokens(code: str) -> OAuthTokens:
    _require_oauth_client_settings()

    headers = {
        **_build_basic_auth_header(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.schwab_redirect_uri,
    }

    with httpx.Client(timeout=20) as client:
        response = client.post(settings.schwab_oauth_token_url, data=form, headers=headers)

    if response.status_code != 200:
        raise ValueError(f"OAuth token exchange failed ({response.status_code}): {response.text[:400]}")

    token_obj = _parse_tokens(response.json())
    set_tokens(token_obj)
    return token_obj


def refresh_access_token() -> OAuthTokens:
    _require_oauth_client_settings()
    if _tokens is None or not _tokens.refresh_token:
        raise ValueError("No Schwab refresh token is available; complete OAuth login first")

    headers = {
        **_build_basic_auth_header(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    form = {
        "grant_type": "refresh_token",
        "refresh_token": _tokens.refresh_token,
    }

    with httpx.Client(timeout=20) as client:
        response = client.post(settings.schwab_oauth_token_url, data=form, headers=headers)

    if response.status_code != 200:
        raise ValueError(f"OAuth refresh failed ({response.status_code}): {response.text[:400]}")

    refreshed = _parse_tokens(response.json())
    # Some providers do not return refresh_token on refresh.
    if not refreshed.refresh_token:
        refreshed.refresh_token = _tokens.refresh_token
    set_tokens(refreshed)
    return refreshed


def set_tokens(tokens: OAuthTokens) -> None:
    global _tokens
    _tokens = tokens
    settings.schwab_access_token = tokens.access_token


def get_valid_access_token() -> str:
    # Backward compatibility if operator still sets token manually in .env.
    if _tokens is None and settings.schwab_access_token:
        return settings.schwab_access_token

    if _tokens is None:
        raise ValueError("Schwab OAuth not initialized. Complete /auth/schwab/start first.")

    now = time.time()
    expires_at = _tokens.expires_at_epoch
    if expires_at is None or now < (expires_at - 60):
        return _tokens.access_token

    refreshed = refresh_access_token()
    return refreshed.access_token


def get_token_status() -> dict[str, Any]:
    if _tokens is None:
        return {
            "configured": bool(settings.schwab_client_id and settings.schwab_redirect_uri),
            "authenticated": bool(settings.schwab_access_token),
            "has_refresh_token": False,
            "expires_at_epoch": None,
        }

    return {
        "configured": bool(settings.schwab_client_id and settings.schwab_redirect_uri),
        "authenticated": True,
        "has_refresh_token": bool(_tokens.refresh_token),
        "expires_at_epoch": _tokens.expires_at_epoch,
    }
