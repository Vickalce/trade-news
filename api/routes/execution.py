from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.session import get_db
from ..schemas import ExecutionPreviewRequest, ExecutionSubmitRequest
from ..security import secure_endpoint
from ..services.execution import (
    build_order_from_recommendation,
    get_recommendation_or_raise,
    submit_order,
)

router = APIRouter(prefix="/execution", tags=["execution"])


@router.post("/preview")
def preview_order(
    payload: ExecutionPreviewRequest,
    _: None = Depends(secure_endpoint),
    db: Session = Depends(get_db),
):
    try:
        recommendation = get_recommendation_or_raise(db, payload.recommendation_id)
        order = build_order_from_recommendation(recommendation, payload.account_id, payload.price_hint)
        return {
            "status": "preview",
            "provider": settings.broker_provider,
            "mode": "dry-run" if settings.broker_dry_run else "live",
            "order": order.model_dump(),
            "guardrails": {
                "kill_switch_enabled": settings.broker_kill_switch_enabled,
                "max_notional_usd": settings.order_max_notional_usd,
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/submit")
def submit_order_endpoint(
    payload: ExecutionSubmitRequest,
    _: None = Depends(secure_endpoint),
    db: Session = Depends(get_db),
):
    if payload.confirm_token != settings.trade_confirm_token:
        raise HTTPException(status_code=400, detail="Invalid confirm token")

    try:
        recommendation = get_recommendation_or_raise(db, payload.recommendation_id)
        order = build_order_from_recommendation(recommendation, payload.account_id, payload.price_hint)
        result = submit_order(order)
        return {"result": result.model_dump(), "order": order.model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
