from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, Request, status

from api.core.config import settings

_REQUEST_WINDOWS: dict[str, deque[datetime]] = defaultdict(deque)



def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")



def enforce_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    key = f"{client}:{request.url.path}"
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=settings.rate_limit_window_seconds)
    bucket = _REQUEST_WINDOWS[key]

    while bucket and bucket[0] < window_start:
        bucket.popleft()

    if len(bucket) >= settings.rate_limit_max_requests:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    bucket.append(now)



def secure_endpoint(
    _: None = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
) -> None:
    return None
