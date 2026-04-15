from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from api.services.schwab_oauth import (
    build_authorize_url,
    create_oauth_state,
    exchange_code_for_tokens,
    get_token_status,
    validate_oauth_state,
)

router = APIRouter(prefix="/auth/schwab", tags=["auth"])


@router.get("/start")
def start_schwab_oauth() -> RedirectResponse:
    try:
        state = create_oauth_state()
        url = build_authorize_url(state)
        return RedirectResponse(url=url, status_code=302)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/callback")
def schwab_oauth_callback(
    code: str = Query(..., description="Authorization code returned by Schwab"),
    state: str = Query(..., description="CSRF state value"),
):
    if not validate_oauth_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        tokens = exchange_code_for_tokens(code)
        return {
            "status": "ok",
            "provider": "schwab",
            "authenticated": True,
            "has_refresh_token": bool(tokens.refresh_token),
            "expires_at_epoch": tokens.expires_at_epoch,
            "message": "Schwab OAuth completed. You can now submit orders.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status")
def schwab_oauth_status():
    return get_token_status()
