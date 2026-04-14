from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..security import secure_endpoint
from ..services.validation import run_paper_validation

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("/paper")
def paper_validation(
    limit: int = Query(default=200, ge=10, le=2000),
    _: None = Depends(secure_endpoint),
    db: Session = Depends(get_db),
):
    summary = run_paper_validation(db=db, limit=limit)
    return {
        "total": summary.total,
        "wins": summary.wins,
        "losses": summary.losses,
        "win_rate": summary.win_rate,
        "avg_confidence": summary.avg_confidence,
    }
