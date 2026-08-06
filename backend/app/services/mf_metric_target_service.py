from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.mf_ingestion.sources.registry import get_source_by_code

PAGE_SIZE = 1000
MF_METRIC_HISTORY_MAX_AGE_DAYS = max(
    1,
    int(os.getenv("MF_METRIC_HISTORY_MAX_AGE_DAYS", "14")),
)
MF_METRIC_HISTORY_MINIMUM_POINTS = 31


def _fetch_candidate_pages(client: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        response = (
            client.table("mf_factsheet_candidates")
            .select(
                "amc_code,report_month,mapped_scheme_code,mapped_family_id,"
                "mapping_status,mapping_confidence,promotion_status"
            )
            .eq("mapping_status", "mapped")
            .order("report_month", desc=True)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = [row for row in (response.data or []) if isinstance(row, dict)]
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def supported_metric_targets(client: Any) -> list[dict[str, Any]]:
    """Return one latest, validated official-disclosure row per mapped scheme."""
    latest_by_code: dict[str, dict[str, Any]] = {}
    for row in _fetch_candidate_pages(client):
        scheme_code = str(row.get("mapped_scheme_code") or "").strip()
        family_id = str(row.get("mapped_family_id") or "").strip()
        if not scheme_code or not family_id:
            continue
        try:
            confidence = float(row.get("mapping_confidence") or 0)
        except (TypeError, ValueError):
            confidence = 0
        if confidence < 90 or str(row.get("promotion_status") or "").lower() == "rejected":
            continue
        try:
            source = get_source_by_code(str(row.get("amc_code") or ""))
        except ValueError:
            continue
        if not source.runtime_enabled:
            continue
        latest_by_code.setdefault(
            scheme_code,
            {
                "scheme_code": scheme_code,
                "family_id": family_id,
                "amc_code": source.amc_code,
                "report_month": row.get("report_month"),
                "promotion_status": row.get("promotion_status"),
            },
        )
    return [latest_by_code[code] for code in sorted(latest_by_code)]


def _cache_metadata(client: Any, scheme_codes: list[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for start in range(0, len(scheme_codes), 500):
        batch = scheme_codes[start : start + 500]
        if not batch:
            continue
        response = (
            client.table("nav_api_cache")
            .select("scheme_code,point_count,last_nav_date,fetched_at,expires_at,updated_at")
            .in_("scheme_code", batch)
            .execute()
        )
        for row in response.data or []:
            if isinstance(row, dict) and row.get("scheme_code") not in (None, ""):
                rows[str(row["scheme_code"])] = row
    return rows


def prioritized_metric_targets(client: Any) -> list[dict[str, Any]]:
    targets = supported_metric_targets(client)
    cache_by_code = _cache_metadata(client, [row["scheme_code"] for row in targets])
    now = datetime.now(timezone.utc)

    def key(row: dict[str, Any]) -> tuple[int, str, str]:
        cache = cache_by_code.get(row["scheme_code"])
        if not cache:
            return (0, "", row["scheme_code"])
        stale_rank = 2 if metric_history_is_ready(cache, now=now) else 1
        refreshed_at = str(cache.get("fetched_at") or cache.get("updated_at") or "")
        return (stale_rank, refreshed_at, row["scheme_code"])

    enriched = [{**row, "cache": cache_by_code.get(row["scheme_code"])} for row in targets]
    return sorted(enriched, key=key)


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def metric_history_is_ready(
    cache: dict[str, Any] | None,
    *,
    now: datetime | None = None,
    minimum_points: int = MF_METRIC_HISTORY_MINIMUM_POINTS,
    max_age_days: int = MF_METRIC_HISTORY_MAX_AGE_DAYS,
) -> bool:
    """Evaluate metric-history freshness independently of the serving-cache TTL."""
    if not cache or int(cache.get("point_count") or 0) < minimum_points:
        return False
    refreshed_at = _parse_timestamp(cache.get("fetched_at") or cache.get("updated_at"))
    if refreshed_at is None:
        return False
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return refreshed_at >= current - timedelta(days=max_age_days)
