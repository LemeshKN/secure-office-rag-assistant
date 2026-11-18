import math
import threading
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, HTTPException

from app.auth.security import get_current_user
from app.config import get_settings
from app.models import User


class RateLimiter:
    """Counts requests per key in a sliding window. Kept in memory, so it resets on restart."""

    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> int:
        """Record a request. Returns 0 if allowed, else the seconds to wait. A limit of 0 turns it off."""
        if limit <= 0:
            return 0
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, math.ceil(window_seconds - (now - hits[0])))
            hits.append(now)
            return 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def rate_limit(bucket: str, setting_name: str, window_seconds: int):
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> None:
        limit = getattr(get_settings(), setting_name)
        wait = limiter.check(f"{bucket}:{user.id}", limit, window_seconds)
        if wait:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Please try again in {wait} seconds.",
                headers={"Retry-After": str(wait)},
            )

    return dependency


rate_limit_chat = rate_limit("chat", "rate_limit_chat_per_minute", 60)
rate_limit_estimate = rate_limit("estimate", "rate_limit_estimate_per_minute", 60)
rate_limit_upload = rate_limit("upload", "rate_limit_upload_per_hour", 3600)