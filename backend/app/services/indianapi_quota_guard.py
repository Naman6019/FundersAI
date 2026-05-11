from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.provider_usage import get_daily_request_cost, get_monthly_request_cost

PROVIDER = "indianapi"
SCHEDULED_MONTHLY_BUDGET = 4000


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class QuotaDecision:
    allowed: bool
    reason: str | None
    monthly_limit: int
    monthly_reserve: int
    scheduled_budget: int
    month_used: int
    day_used: int
    remaining_total: int
    remaining_safe: int
    live_calls_enabled: bool
    scheduled_sync_enabled: bool


def evaluate(*, scheduled: bool, now: datetime | None = None) -> QuotaDecision:
    current = now or datetime.now(timezone.utc)
    monthly_limit = _env_int("INDIANAPI_MONTHLY_LIMIT", 5000)
    monthly_reserve = _env_int("INDIANAPI_MONTHLY_RESERVE", 500)
    daily_soft_limit = _env_int("INDIANAPI_DAILY_SOFT_LIMIT", 120)
    live_calls_enabled = _env_bool("INDIANAPI_ENABLE_LIVE_CALLS", False)
    scheduled_sync_enabled = _env_bool("INDIANAPI_ENABLE_SCHEDULED_SYNC", True)

    month_used = get_monthly_request_cost(PROVIDER, current)
    day_used = get_daily_request_cost(PROVIDER, current)
    remaining_total = max(monthly_limit - month_used, 0)
    remaining_safe = max((monthly_limit - monthly_reserve) - month_used, 0)
    scheduled_budget = min(max(monthly_limit - monthly_reserve, 0), SCHEDULED_MONTHLY_BUDGET)

    allowed = True
    reason = None

    if scheduled and not scheduled_sync_enabled:
        allowed = False
        reason = "scheduled_sync_disabled"
    elif (not scheduled) and not live_calls_enabled:
        allowed = False
        reason = "live_calls_disabled"
    elif month_used >= monthly_limit:
        allowed = False
        reason = "monthly_limit_reached"
    elif remaining_safe <= 0:
        allowed = False
        reason = "reserve_protected"
    elif day_used >= daily_soft_limit:
        allowed = False
        reason = "daily_soft_limit_reached"
    elif scheduled and month_used >= scheduled_budget:
        allowed = False
        reason = "scheduled_budget_reached"

    return QuotaDecision(
        allowed=allowed,
        reason=reason,
        monthly_limit=monthly_limit,
        monthly_reserve=monthly_reserve,
        scheduled_budget=scheduled_budget,
        month_used=month_used,
        day_used=day_used,
        remaining_total=remaining_total,
        remaining_safe=remaining_safe,
        live_calls_enabled=live_calls_enabled,
        scheduled_sync_enabled=scheduled_sync_enabled,
    )


def remaining_safe_budget(now: datetime | None = None) -> int:
    return evaluate(scheduled=False, now=now).remaining_safe
