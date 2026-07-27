from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def assess_nav_freshness(nav_date: object, *, now: datetime | None = None) -> dict[str, object]:
    """Classify NAV against the last expected Indian business-day publication."""
    expected_date = latest_expected_nav_date(now=now)
    observed_date = _to_date(nav_date)
    if observed_date is None:
        return {
            "status": "missing",
            "nav_date": None,
            "expected_nav_date": expected_date.isoformat(),
            "missed_business_days": None,
        }

    missed_business_days = _business_days_between(observed_date, expected_date)
    status = "fresh" if missed_business_days == 0 else "lagging" if missed_business_days == 1 else "stale"
    return {
        "status": status,
        "nav_date": observed_date.isoformat(),
        "expected_nav_date": expected_date.isoformat(),
        "missed_business_days": missed_business_days,
    }


def latest_expected_nav_date(*, now: datetime | None = None) -> date:
    """NAV for the previous business day is the latest expected during the current day."""
    current = now or datetime.now(timezone.utc)
    current_ist = current.astimezone(IST)
    return _previous_business_day(current_ist.date())


def _business_days_between(observed_date: date, expected_date: date) -> int:
    if observed_date >= expected_date:
        return 0
    missed = 0
    cursor = observed_date
    while cursor < expected_date:
        cursor += timedelta(days=1)
        if _is_business_day(cursor):
            missed += 1
    return missed


def _previous_business_day(start_date: date) -> date:
    cursor = start_date - timedelta(days=1)
    while not _is_business_day(cursor):
        cursor -= timedelta(days=1)
    return cursor


def _is_business_day(value: date) -> bool:
    return value.weekday() < 5 and value not in _market_holidays()


def _market_holidays() -> set[date]:
    values: set[date] = set()
    for raw in os.getenv("MF_NAV_MARKET_HOLIDAYS", "").split(","):
        try:
            values.add(date.fromisoformat(raw.strip()))
        except ValueError:
            continue
    return values


def _to_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
