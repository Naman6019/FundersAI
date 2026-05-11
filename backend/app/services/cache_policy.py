from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

DEFAULT_TTL_SECONDS: dict[str, int] = {
    "stock_profile": 30 * 24 * 60 * 60,
    "stock_fundamentals": 7 * 24 * 60 * 60,
    "stock_market_cap": 24 * 60 * 60,
    "stock_price_history": 24 * 60 * 60,
    "mutual_fund_nav": 24 * 60 * 60,
    "mutual_fund_enrichment": 30 * 24 * 60 * 60,
}


def ttl_seconds(policy_name: str, fallback_seconds: int | None = None) -> int:
    key = f"CACHE_TTL_{policy_name.upper()}"
    raw = os.getenv(key)
    if raw:
        try:
            parsed = int(raw)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    if policy_name in DEFAULT_TTL_SECONDS:
        return DEFAULT_TTL_SECONDS[policy_name]
    return fallback_seconds or 0


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def is_fresh(updated_at: Any, policy_name: str, now: datetime | None = None) -> bool:
    dt = parse_dt(updated_at)
    if not dt:
        return False
    ttl = ttl_seconds(policy_name)
    if ttl <= 0:
        return False
    current = now or datetime.now(timezone.utc)
    return dt + timedelta(seconds=ttl) >= current
