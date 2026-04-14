from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "Trade News",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
