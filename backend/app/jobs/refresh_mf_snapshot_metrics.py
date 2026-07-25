from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from collections.abc import Iterator
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.repositories.stock_repository import StockRepository
from app.services.mf_metrics_service import NAV_METRIC_SNAPSHOT_VERSION, compute_nav_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RISK_FREE_RATE = float(os.getenv("MF_METRIC_RISK_FREE_RATE", "0.06"))
PAGE_SIZE = max(1, min(int(os.getenv("MF_METRIC_REFRESH_PAGE_SIZE", "250")), 1000))


def _enabled(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _cache_row_pages(repo: StockRepository, limit: int) -> Iterator[list[dict[str, Any]]]:
    processed = 0
    offset = 0
    while limit <= 0 or processed < limit:
        batch_size = min(PAGE_SIZE, limit - processed) if limit > 0 else PAGE_SIZE
        response = (
            repo.supabase.table("nav_api_cache")
            .select("scheme_code,payload,point_count,last_nav_date,fetched_at,updated_at")
            .order("scheme_code")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        raw_batch = response.data or []
        batch = [row for row in raw_batch if isinstance(row, dict)]
        if batch:
            yield batch
        processed += len(raw_batch)
        if len(raw_batch) < batch_size:
            break
        offset += batch_size


def _core_rows(repo: StockRepository, scheme_codes: list[str]) -> dict[str, dict[str, Any]]:
    if not scheme_codes:
        return {}
    response = (
        repo.supabase.table("mutual_fund_core_snapshot")
        .select("scheme_code,provider_payload")
        .in_("scheme_code", scheme_codes)
        .execute()
    )
    return {
        str(row.get("scheme_code")): row
        for row in (response.data or [])
        if isinstance(row, dict) and row.get("scheme_code") not in (None, "")
    }


def _benchmark_rows(repo: StockRepository) -> list[dict[str, Any]]:
    response = (
        repo.supabase.table("stock_prices_daily")
        .select("date,close")
        .eq("symbol", "NIFTY")
        .order("date")
        .limit(2200)
        .execute()
    )
    return response.data or []


def _metric_row(
    cache_row: dict[str, Any],
    existing: dict[str, Any],
    benchmark_rows: list[dict[str, Any]],
    computed_at: str,
) -> dict[str, Any] | None:
    scheme_code = str(cache_row.get("scheme_code") or "").strip()
    history = cache_row.get("payload")
    if (
        not scheme_code
        or not existing.get("scheme_code")
        or not isinstance(history, list)
        or len(history) < 2
    ):
        return None

    metrics = compute_nav_metrics(
        history,
        risk_free_rate=RISK_FREE_RATE,
        benchmark_rows=benchmark_rows,
    )
    provider_payload = existing.get("provider_payload")
    provider_payload = dict(provider_payload) if isinstance(provider_payload, dict) else {}
    provider_payload["metric_snapshot"] = {
        "version": NAV_METRIC_SNAPSHOT_VERSION,
        "as_of_date": cache_row.get("last_nav_date") or history[-1].get("nav_date") or history[-1].get("date"),
        "computed_at": computed_at,
        "history_points": int(cache_row.get("point_count") or len(history)),
        "benchmark": "NIFTY",
        "risk_free_rate": RISK_FREE_RATE,
    }
    return {
        "scheme_code": scheme_code,
        **metrics,
        "provider_payload": provider_payload,
    }


def main() -> int:
    if not _enabled("ENABLE_MF_SNAPSHOT_METRICS_REFRESH", True):
        logger.info("ENABLE_MF_SNAPSHOT_METRICS_REFRESH is false. Skipping.")
        return 0

    repo = StockRepository()
    if not repo.supabase:
        logger.error("Supabase client is not configured.")
        return 1

    limit = max(int(os.getenv("MF_METRIC_REFRESH_SCHEME_LIMIT", "0")), 0)
    benchmark_rows = _benchmark_rows(repo)
    computed_at = datetime.now(timezone.utc).isoformat()
    cached = 0
    updated = 0
    skipped = 0

    for batch in _cache_row_pages(repo, limit):
        cached += len(batch)
        scheme_codes = [str(row.get("scheme_code")) for row in batch if row.get("scheme_code") not in (None, "")]
        existing = _core_rows(repo, scheme_codes)
        metric_rows = []
        for cache_row in batch:
            code = str(cache_row.get("scheme_code") or "")
            metric_row = _metric_row(cache_row, existing.get(code, {}), benchmark_rows, computed_at)
            if metric_row:
                metric_rows.append(metric_row)
            else:
                skipped += 1
        repo.upsert_mutual_fund_core_snapshot_rows(metric_rows)
        updated += len(metric_rows)

    if cached == 0:
        logger.warning("No cached NAV histories were available for metric refresh.")
        return 0

    logger.info(
        "MF snapshot metric refresh complete: cached=%s updated=%s skipped=%s version=%s",
        cached,
        updated,
        skipped,
        NAV_METRIC_SNAPSHOT_VERSION,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
