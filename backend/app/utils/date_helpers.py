from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def to_utc_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            raw = f"{raw}T00:00:00+00:00"
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def age_days(dt: datetime | None, now_utc: datetime) -> float | None:
    if not dt:
        return None
    return max((now_utc - dt).total_seconds() / 86400.0, 0.0)


def fmt_age(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value:.1f}d"


def iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
