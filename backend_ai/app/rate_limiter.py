"""
rate_limiter.py — Sliding Window Rate Limiter

Giới hạn số request mỗi user trong 1 phút.
Default: 10 requests/minute per user (configurable).

Algorithm: Sliding Window Counter
- Mỗi user có 1 deque chứa timestamps
- Loại bỏ timestamps cũ (ngoài window)
- Vượt quá limit → 429 Too Many Requests

Note: In-memory implementation.
      Để scale nhiều instances → dùng Redis (TASK 4).
"""
import time
import logging
from collections import defaultdict, deque
from fastapi import HTTPException, Depends

from app.core.config import settings
from app.auth import verify_api_key

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """
    Sliding Window Rate Limiter.
    Thread-safe cho single-process deployment.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # user_id → deque of timestamps
        self._windows: dict[str, deque] = defaultdict(deque)

    def check(self, user_id: str) -> dict:
        """
        Kiểm tra rate limit cho user.

        Returns:
            dict: thông tin limit còn lại

        Raises:
            HTTPException 429: nếu vượt rate limit
        """
        now = time.time()
        window = self._windows[user_id]

        # Loại bỏ timestamps cũ (ngoài window)
        while window and window[0] < now - self.window_seconds:
            window.popleft()

        current_count = len(window)
        remaining = self.max_requests - current_count

        if current_count >= self.max_requests:
            oldest = window[0]
            retry_after = int(oldest + self.window_seconds - now) + 1

            logger.warning(f"Rate limit exceeded for user: {user_id}")

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": self.max_requests,
                    "window_seconds": self.window_seconds,
                    "retry_after_seconds": retry_after,
                    "message": f"Vượt quá {self.max_requests} requests/{self.window_seconds}s. Thử lại sau {retry_after}s.",
                },
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(oldest + self.window_seconds)),
                    "Retry-After": str(retry_after),
                },
            )

        # Record request timestamp
        window.append(now)

        return {
            "limit": self.max_requests,
            "remaining": remaining - 1,
            "reset_at": int(now) + self.window_seconds,
        }

    def get_stats(self, user_id: str) -> dict:
        """Trả về stats hiện tại của user (không check limit)."""
        now = time.time()
        window = self._windows[user_id]
        active = sum(1 for t in window if t >= now - self.window_seconds)
        return {
            "user_id": user_id,
            "requests_in_window": active,
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - active),
            "window_seconds": self.window_seconds,
        }


# Singleton instance
_limiter = SlidingWindowRateLimiter(
    max_requests=settings.rate_limit_per_minute,
    window_seconds=60,
)


def check_rate_limit(user_id: str = Depends(verify_api_key)) -> dict:
    """
    FastAPI Dependency: check rate limit cho user.

    Dùng trong endpoint:
        @app.post("/chat")
        def chat(..., _: dict = Depends(check_rate_limit)):
            ...
    """
    if not settings.rate_limit_enabled:
        return {"limit": -1, "remaining": -1, "message": "rate limiting disabled"}

    return _limiter.check(user_id)


def get_rate_limit_stats(user_id: str) -> dict:
    """Helper để lấy stats (dùng trong /usage endpoint)."""
    return _limiter.get_stats(user_id)
