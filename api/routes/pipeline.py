from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import Recommendation
from ..db.session import get_db
from ..security import secure_endpoint
from ..services.pipeline import run_ingestion_only, run_signal_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/ingest")
def ingest(_: None = Depends(secure_endpoint), db: Session = Depends(get_db)) -> dict[str, int]:
    return run_ingestion_only(db)


@router.post("/run")
def run_pipeline(
    limit: int = Query(default=settings.pipeline_default_limit, ge=1, le=200),
    _: None = Depends(secure_endpoint),
    db: Session = Depends(get_db),
):
    results = run_signal_pipeline(db=db, limit=limit)
    return {"count": len(results), "results": [item.model_dump() for item in results]}


@router.get("/recommendations")
def recommendations(
    limit: int = Query(default=50, ge=1, le=500),
    _: None = Depends(secure_endpoint),
    db: Session = Depends(get_db),
):
    rows = db.query(Recommendation).order_by(Recommendation.created_at_utc.desc()).limit(limit).all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "event_id": row.event_id,
                "symbol": row.symbol,
                "recommendation": row.recommendation,
                "confidence": row.confidence,
                "rationale": row.rationale,
                "invalidation_conditions": row.invalidation_conditions,
                "created_at_utc": row.created_at_utc.isoformat(),
            }
            for row in rows
        ],
    }
