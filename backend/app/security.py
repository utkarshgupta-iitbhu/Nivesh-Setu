"""Lightweight in-memory sliding-window rate limiter & upload guards.

Protects AI and voice endpoints from accidental loops or public traffic abuse
without requiring Redis or external infrastructure.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

MAX_AUDIO_UPLOAD_BYTES: int = 4 * 1024 * 1024  # 4 MB cap (under Vercel 4.5 MB body limit)


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, client_key: str) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        bucket = self._hits[client_key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "RATE_LIMITED",
                    "en": "Too many AI requests. Please wait a moment and try again.",
                    "hi": "बहुत अधिक AI अनुरोध। कृपया थोड़ा रुककर फिर कोशिश करें।",
                },
            )
        bucket.append(now)

    def reset(self) -> None:
        self._hits.clear()


ai_rate_limiter = SlidingWindowRateLimiter(max_requests=30, window_seconds=60)


def enforce_ai_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    ai_rate_limiter.check(client_ip)
