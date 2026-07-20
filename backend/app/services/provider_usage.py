from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.database import supabase

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _month_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    current = now or _utc_now()
    start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def log_provider_usage(
    *,
    provider: str,
    endpoint: str,
    symbol: str | None = None,
    scheme_code: str | None = None,
    user_id: str | None = None,
    cache_hit: bool = False,
    status_code: int | None = None,
    success: bool = True,
    error_message: str | None = None,
    request_cost: int = 1,
    created_at: datetime | None = None,
) -> None:
    if not supabase:
        return
    row = {
        "provider": provider,
        "endpoint": endpoint,
        "symbol": symbol,
        "scheme_code": scheme_code,
        "user_id": user_id,
        "cache_hit": cache_hit,
        "status_code": status_code,
        "success": success,
        "error_message": (error_message or None),
        "request_cost": max(request_cost, 0),
        "created_at": (created_at or _utc_now()).isoformat(),
    }
    try:
        supabase.table("provider_usage_logs").insert(row).execute()
    except Exception as exc:
        logger.warning("Provider usage logging failed for %s/%s: %s", provider, endpoint, exc)


def get_usage_rows(provider: str, start: datetime, end: datetime, limit: int = 10000) -> list[dict[str, Any]]:
    if not supabase:
        return []
    try:
        response = (
            supabase.table("provider_usage_logs")
            .select("*")
            .eq("provider", provider)
            .gte("created_at", start.isoformat())
            .lt("created_at", end.isoformat())
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as exc:
        logger.warning("Provider usage query failed for %s: %s", provider, exc)
        return []


def get_first_usage_row(
    provider: str,
    start: datetime,
    end: datetime,
    *,
    endpoint_prefix: str | None = None,
) -> dict[str, Any] | None:
    if not supabase:
        return None
    try:
        query = (
            supabase.table("provider_usage_logs")
            .select("endpoint,created_at")
            .eq("provider", provider)
            .gte("created_at", start.isoformat())
            .lt("created_at", end.isoformat())
        )
        if endpoint_prefix:
            query = query.like("endpoint", f"{endpoint_prefix}%")
        rows = query.order("created_at", desc=False).limit(1).execute().data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.warning("Provider first usage query failed for %s: %s", provider, exc)
        return None


def get_monthly_request_cost(provider: str, now: datetime | None = None) -> int:
    start, end = _month_bounds(now)
    rows = get_usage_rows(provider, start, end)
    return int(sum(int(row.get("request_cost") or 0) for row in rows))


def get_daily_request_cost(provider: str, now: datetime | None = None) -> int:
    current = now or _utc_now()
    day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    rows = get_usage_rows(provider, day_start, day_end)
    return int(sum(int(row.get("request_cost") or 0) for row in rows))


def build_usage_dashboard(provider: str, now: datetime | None = None) -> dict[str, Any]:
    current = now or _utc_now()
    month_start, month_end = _month_bounds(current)
    month_rows = get_usage_rows(provider, month_start, month_end)
    day_rows = get_usage_rows(
        provider,
        current.replace(hour=0, minute=0, second=0, microsecond=0),
        current.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
    )

    month_cost = int(sum(int(row.get("request_cost") or 0) for row in month_rows))
    day_cost = int(sum(int(row.get("request_cost") or 0) for row in day_rows))

    by_endpoint: dict[str, dict[str, Any]] = {}
    for row in month_rows:
        endpoint = str(row.get("endpoint") or "unknown")
        bucket = by_endpoint.setdefault(endpoint, {"calls": 0, "cost": 0, "failures": 0, "cache_hits": 0})
        bucket["calls"] += 1
        bucket["cost"] += int(row.get("request_cost") or 0)
        if not bool(row.get("success", True)):
            bucket["failures"] += 1
        if bool(row.get("cache_hit", False)):
            bucket["cache_hits"] += 1

    cache_hits = sum(1 for row in month_rows if bool(row.get("cache_hit", False)))
    total_attempts = len(month_rows)
    cache_hit_ratio = (cache_hits / total_attempts) if total_attempts else 0.0

    recent_failures = [
        {
            "endpoint": row.get("endpoint"),
            "status_code": row.get("status_code"),
            "error_message": row.get("error_message"),
            "created_at": row.get("created_at"),
        }
        for row in month_rows
        if not bool(row.get("success", True))
    ][:15]

    return {
        "provider": provider,
        "month_window": {"start": month_start.isoformat(), "end": month_end.isoformat()},
        "month_request_cost": month_cost,
        "daily_request_cost": day_cost,
        "usage_by_endpoint": by_endpoint,
        "cache_hit_ratio": round(cache_hit_ratio, 4),
        "recent_failures": recent_failures,
    }
