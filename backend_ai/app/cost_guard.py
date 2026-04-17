"""
cost_guard.py — Monthly Budget Guard

Bảo vệ budget OpenAI API.
- Track spending per user per month
- $10/month per user (configurable)
- Block khi vượt budget → 402 Payment Required
- Reset đầu tháng

Note: In-memory implementation.
      Để persist qua restart → dùng Redis (TASK 4).
"""
import time
import logging
from dataclasses import dataclass, field
from fastapi import HTTPException, Depends

from app.core.config import settings
from app.auth import verify_api_key

logger = logging.getLogger(__name__)

# GPT-4o-mini pricing (USD per 1K tokens)
PRICE_PER_1K_INPUT = 0.00015   # $0.15/1M input tokens
PRICE_PER_1K_OUTPUT = 0.0006   # $0.60/1M output tokens


@dataclass
class MonthlyUsage:
    """Track usage cho 1 user trong 1 tháng."""
    user_id: str
    month: str = field(default_factory=lambda: time.strftime("%Y-%m"))
    input_tokens: int = 0
    output_tokens: int = 0
    request_count: int = 0

    @property
    def total_cost_usd(self) -> float:
        input_cost = (self.input_tokens / 1000) * PRICE_PER_1K_INPUT
        output_cost = (self.output_tokens / 1000) * PRICE_PER_1K_OUTPUT
        return round(input_cost + output_cost, 6)


class CostGuard:
    """
    Monthly budget guard per user.
    """

    def __init__(
        self,
        monthly_budget_usd: float = 10.0,
        warn_at_pct: float = 0.8,
    ):
        self.monthly_budget_usd = monthly_budget_usd
        self.warn_at_pct = warn_at_pct
        # user_id → MonthlyUsage
        self._records: dict[str, MonthlyUsage] = {}

    def _get_record(self, user_id: str) -> MonthlyUsage:
        """Lấy record hiện tại, reset nếu sang tháng mới."""
        current_month = time.strftime("%Y-%m")
        record = self._records.get(user_id)

        if not record or record.month != current_month:
            self._records[user_id] = MonthlyUsage(
                user_id=user_id,
                month=current_month,
            )
        return self._records[user_id]

    def check_budget(self, user_id: str) -> None:
        """
        Kiểm tra budget trước khi gọi LLM.

        Raises:
            HTTPException 402: nếu vượt monthly budget
        """
        record = self._get_record(user_id)
        used = record.total_cost_usd
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
    ) -> MonthlyUsage:
        """
        Ghi nhận usage sau khi gọi LLM.
        Gọi sau khi nhận response từ LLM.
        """
        record = self._get_record(user_id)
        record.input_tokens += input_tokens
        record.output_tokens += output_tokens
        record.request_count += 1

        logger.info(
            f"Usage recorded: user={user_id} "
            f"req={record.request_count} "
            f"cost=${record.total_cost_usd:.4f}/{self.monthly_budget_usd}"
        )
        return record

    def get_usage(self, user_id: str) -> dict:
        """Trả về usage summary cho user."""
        record = self._get_record(user_id)
        used = record.total_cost_usd
        budget = self.monthly_budget_usd

        return {
            "user_id": user_id,
            "month": record.month,
            "requests": record.request_count,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "cost_usd": round(used, 4),
            "budget_usd": budget,
            "remaining_usd": round(max(0, budget - used), 4),
            "used_pct": round(used / budget * 100, 1),
        }


# Singleton
_cost_guard = CostGuard(
    monthly_budget_usd=settings.monthly_budget_usd,
    warn_at_pct=0.8,
)


def check_budget(user_id: str = Depends(verify_api_key)) -> None:
    """
    FastAPI Dependency: check budget cho user.

    Dùng trong endpoint:
        @app.post("/chat")
        def chat(..., _: None = Depends(check_budget)):
            ...
    """
    if not settings.cost_guard_enabled:
        return

    _cost_guard.check_budget(user_id)


def record_usage(user_id: str, input_tokens: int = 0, output_tokens: int = 0) -> dict:
    """Helper để record usage sau khi gọi LLM."""
    if not settings.cost_guard_enabled:
        return {}
    record = _cost_guard.record_usage(user_id, input_tokens, output_tokens)
    return _cost_guard.get_usage(user_id)


def get_usage(user_id: str) -> dict:
    """Helper để lấy usage summary."""
    return _cost_guard.get_usage(user_id)
