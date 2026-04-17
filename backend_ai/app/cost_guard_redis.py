"""
cost_guard_redis.py — Redis-based Cost Guard

Monthly budget tracking với Redis backend.
Support horizontal scaling (multiple instances share state).

Fallback: Nếu Redis down, fallback về in-memory cost guard.
"""
import time
import logging
import json
from fastapi import HTTPException, Depends
from redis.exceptions import RedisError

from app.core.config import settings
from app.auth import verify_api_key
from app.redis_client import get_redis
from app.cost_guard import CostGuard, PRICE_PER_1K_INPUT, PRICE_PER_1K_OUTPUT  # Fallback

logger = logging.getLogger(__name__)


class RedisCostGuard:
    """
    Redis-based monthly budget guard.
    
    Data structure:
    - Key: cost_guard:{user_id}:{month}
    - Value: JSON {input_tokens, output_tokens, request_count}
    - TTL: 35 days (để giữ data qua tháng)
    """
    
    def __init__(
        self,
        monthly_budget_usd: float = 10.0,
        warn_at_pct: float = 0.8,
    ):
        self.monthly_budget_usd = monthly_budget_usd
        self.warn_at_pct = warn_at_pct
        self._fallback = CostGuard(monthly_budget_usd, warn_at_pct)
    
    def _get_key(self, user_id: str) -> str:
        """Generate Redis key cho user + month."""
        month = time.strftime("%Y-%m")
        return f"cost_guard:{user_id}:{month}"
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost từ token counts."""
        input_cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT
        output_cost = (output_tokens / 1000) * PRICE_PER_1K_OUTPUT
        return round(input_cost + output_cost, 6)
    
    def check_budget(self, user_id: str) -> None:
        """
        Kiểm tra budget trước khi gọi LLM.
        
        Raises:
            HTTPException 402: nếu vượt monthly budget
        """
        redis_client = get_redis()
        
        # Fallback to in-memory nếu Redis không available
        if redis_client is None:
            logger.debug("Redis not available, using in-memory cost guard")
            return self._fallback.check_budget(user_id)
        
        try:
            return self._check_budget_redis(redis_client, user_id)
        except RedisError as e:
            logger.warning(f"Redis error in cost guard, falling back to in-memory: {e}")
            return self._fallback.check_budget(user_id)
    
    def _check_budget_redis(self, redis_client, user_id: str) -> None:
        """Check budget using Redis."""
        key = self._get_key(user_id)
        data_str = redis_client.get(key)
        
        if data_str:
            data = json.loads(data_str)
            input_tokens = data.get("input_tokens", 0)
            output_tokens = data.get("output_tokens", 0)
            used = self._calculate_cost(input_tokens, output_tokens)
        else:
            used = 0.0
        
        budget = self.monthly_budget_usd
        
        # Vượt budget
        if used >= budget:
            logger.warning(f"Budget exceeded for user {user_id}: ${used:.4f}/${budget}")
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Monthly budget exceeded",
                    "used_usd": round(used, 4),
                    "budget_usd": budget,
                    "resets_at": "1st of next month (UTC)",
                    "message": f"Đã vượt ngân sách ${budget}/tháng. Reset vào đầu tháng sau.",
                },
            )
        
        # Cảnh báo khi gần hết budget
        if used >= budget * self.warn_at_pct:
            pct = round(used / budget * 100, 1)
            logger.warning(f"User {user_id} at {pct}% monthly budget (${used:.4f}/${budget})")
    
    def record_usage(
        self,
        user_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> dict:
        """
        Ghi nhận usage sau khi gọi LLM.
        
        Returns:
            dict: usage summary
        """
        redis_client = get_redis()
        
        if redis_client is None:
            logger.debug("Redis not available, using in-memory cost guard")
            self._fallback.record_usage(user_id, input_tokens, output_tokens)
            return self.get_usage(user_id)
        
        try:
            return self._record_usage_redis(redis_client, user_id, input_tokens, output_tokens)
        except RedisError as e:
            logger.warning(f"Redis error in record_usage: {e}")
            self._fallback.record_usage(user_id, input_tokens, output_tokens)
            return self.get_usage(user_id)
    
    def _record_usage_redis(
        self,
        redis_client,
        user_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> dict:
        """Record usage using Redis."""
        key = self._get_key(user_id)
        
        # Lấy data hiện tại
        data_str = redis_client.get(key)
        if data_str:
            data = json.loads(data_str)
        else:
            data = {"input_tokens": 0, "output_tokens": 0, "request_count": 0}
        
        # Update
        data["input_tokens"] += input_tokens
        data["output_tokens"] += output_tokens
        data["request_count"] += 1
        
        # Save back
        redis_client.set(key, json.dumps(data), ex=35 * 24 * 3600)  # TTL 35 days
        
        cost = self._calculate_cost(data["input_tokens"], data["output_tokens"])
        
        logger.info(
            f"Usage recorded: user={user_id} "
            f"req={data['request_count']} "
            f"cost=${cost:.4f}/{self.monthly_budget_usd}"
        )
        
        return self.get_usage(user_id)
    
    def get_usage(self, user_id: str) -> dict:
        """Trả về usage summary cho user."""
        redis_client = get_redis()
        
        if redis_client is None:
            return self._fallback.get_usage(user_id)
        
        try:
            return self._get_usage_redis(redis_client, user_id)
        except RedisError as e:
            logger.warning(f"Redis error in get_usage: {e}")
            return self._fallback.get_usage(user_id)
    
    def _get_usage_redis(self, redis_client, user_id: str) -> dict:
        """Get usage using Redis."""
        key = self._get_key(user_id)
        month = time.strftime("%Y-%m")
        
        data_str = redis_client.get(key)
        if data_str:
            data = json.loads(data_str)
            input_tokens = data.get("input_tokens", 0)
            output_tokens = data.get("output_tokens", 0)
            request_count = data.get("request_count", 0)
        else:
            input_tokens = 0
            output_tokens = 0
            request_count = 0
        
        used = self._calculate_cost(input_tokens, output_tokens)
        budget = self.monthly_budget_usd
        
        return {
            "user_id": user_id,
            "month": month,
            "requests": request_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(used, 4),
            "budget_usd": budget,
            "remaining_usd": round(max(0, budget - used), 4),
            "used_pct": round(used / budget * 100, 1) if budget > 0 else 0,
        }


# Singleton
_redis_cost_guard = RedisCostGuard(
    monthly_budget_usd=settings.monthly_budget_usd,
    warn_at_pct=0.8,
)


def check_budget_redis(user_id: str = Depends(verify_api_key)) -> None:
    """
    FastAPI Dependency: check budget cho user (Redis version).
    """
    if not settings.cost_guard_enabled:
        return
    
    _redis_cost_guard.check_budget(user_id)


def record_usage_redis(user_id: str, input_tokens: int = 0, output_tokens: int = 0) -> dict:
    """Helper để record usage (Redis version)."""
    if not settings.cost_guard_enabled:
        return {}
    return _redis_cost_guard.record_usage(user_id, input_tokens, output_tokens)


def get_usage_redis(user_id: str) -> dict:
    """Helper để lấy usage summary (Redis version)."""
    return _redis_cost_guard.get_usage(user_id)
