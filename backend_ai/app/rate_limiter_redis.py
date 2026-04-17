"""
rate_limiter_redis.py — Redis-based Rate Limiter

Sliding window rate limiter với Redis backend.
Support horizontal scaling (multiple instances share state).

Fallback: Nếu Redis down, fallback về in-memory limiter.
"""
import time
import logging
from fastapi import HTTPException, Depends
from redis.exceptions import RedisError

from app.core.config import settings
from app.auth import verify_api_key
from app.redis_client import get_redis
from app.rate_limiter import SlidingWindowRateLimiter  # Fallback

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """
    Redis-based sliding window rate limiter.
    
    Algorithm: Sorted Set (ZSET)
    - Key: rate_limit:{user_id}
    - Score: timestamp
    - Member: request_id (timestamp + random)
    - TTL: window_seconds + buffer
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._fallback = SlidingWindowRateLimiter(max_requests, window_seconds)
    
    def check(self, user_id: str) -> dict:
        """
        Kiểm tra rate limit cho user.
        
        Returns:
            dict: thông tin limit còn lại
        
        Raises:
            HTTPException 429: nếu vượt rate limit
        """
        redis_client = get_redis()
        
        # Fallback to in-memory nếu Redis không available
        if redis_client is None:
            logger.debug("Redis not available, using in-memory rate limiter")
            return self._fallback.check(user_id)
        
        try:
            return self._check_redis(redis_client, user_id)
        except RedisError as e:
            logger.warning(f"Redis error in rate limiter, falling back to in-memory: {e}")
            return self._fallback.check(user_id)
    
    def _check_redis(self, redis_client, user_id: str) -> dict:
        """Check rate limit using Redis ZSET."""
        now = time.time()
        key = f"rate_limit:{user_id}"
        window_start = now - self.window_seconds
        
        # Pipeline để atomic operations
        pipe = redis_client.pipeline()
        
        # 1. Xóa timestamps cũ (ngoài window)
        pipe.zremrangebyscore(key, 0, window_start)
        
        # 2. Đếm số requests trong window
        pipe.zcard(key)
        
        # 3. Thêm request hiện tại
        pipe.zadd(key, {f"{now}": now})
        
        # 4. Set TTL cho key
        pipe.expire(key, self.window_seconds + 10)
        
        # Execute pipeline
        results = pipe.execute()
        current_count = results[1]  # Kết quả của ZCARD
        
        remaining = self.max_requests - current_count
        
        if current_count >= self.max_requests:
            # Lấy timestamp cũ nhất để tính retry_after
            oldest_timestamps = redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_timestamps:
                oldest = oldest_timestamps[0][1]
                retry_after = int(oldest + self.window_seconds - now) + 1
            else:
                retry_after = self.window_seconds
            
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
                    "X-RateLimit-Reset": str(int(now + retry_after)),
                    "Retry-After": str(retry_after),
                },
            )
        
        return {
            "limit": self.max_requests,
            "remaining": remaining - 1,
            "reset_at": int(now) + self.window_seconds,
        }
    
    def get_stats(self, user_id: str) -> dict:
        """Trả về stats hiện tại của user."""
        redis_client = get_redis()
        
        if redis_client is None:
            return self._fallback.get_stats(user_id)
        
        try:
            now = time.time()
            key = f"rate_limit:{user_id}"
            window_start = now - self.window_seconds
            
            # Đếm requests trong window
            active = redis_client.zcount(key, window_start, now)
            
            return {
                "user_id": user_id,
                "requests_in_window": active,
                "limit": self.max_requests,
                "remaining": max(0, self.max_requests - active),
                "window_seconds": self.window_seconds,
            }
        except RedisError as e:
            logger.warning(f"Redis error in get_stats: {e}")
            return self._fallback.get_stats(user_id)


# Singleton instance
_redis_limiter = RedisRateLimiter(
    max_requests=settings.rate_limit_per_minute,
    window_seconds=60,
)


def check_rate_limit_redis(user_id: str = Depends(verify_api_key)) -> dict:
    """
    FastAPI Dependency: check rate limit cho user (Redis version).
    
    Dùng trong endpoint:
        @app.post("/chat")
        def chat(..., _: dict = Depends(check_rate_limit_redis)):
            ...
    """
    if not settings.rate_limit_enabled:
        return {"limit": -1, "remaining": -1, "message": "rate limiting disabled"}
    
    return _redis_limiter.check(user_id)


def get_rate_limit_stats_redis(user_id: str) -> dict:
    """Helper để lấy stats (Redis version)."""
    return _redis_limiter.get_stats(user_id)
