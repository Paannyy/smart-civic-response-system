import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List

from fastapi import HTTPException, Request, status

from app.db.database import settings


class InMemoryRateLimiter:
    def __init__(self):
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> None:
        if not settings.RATE_LIMIT_ENABLED or limit <= 0:
            return

        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            # Clean old timestamps
            self._requests[key] = [
                ts for ts in self._requests[key] if ts > window_start
            ]

            if len(self._requests[key]) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                )

            self._requests[key].append(now)

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


limiter = InMemoryRateLimiter()


def rate_limit_auth(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    limiter.check_rate_limit(
        key=f"auth:{client_ip}",
        limit=settings.RATE_LIMIT_AUTH_PER_MINUTE,
        window_seconds=60,
    )
