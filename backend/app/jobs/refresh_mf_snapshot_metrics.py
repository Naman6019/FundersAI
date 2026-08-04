from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from collections.abc import Iterator
from pathlib import Path
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.models.stock_models import ProviderRun
from app.repositories.stock_repository import StockRepository
from app.services.mf_metric_target_service import supported_metric_targets
from app.services.mf_metrics_service import (
    NAV_METRIC_SNAPSHOT_VERSION,
    compute_nav_metrics_with_diagnostics,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RISK_FREE_RATE = float(os.getenv("MF_METRIC_RISK_FREE_RATE", "0.06"))
PAGE_SIZE = max(1, min(int(os.getenv("MF_METRIC_REFRESH_PAGE_SIZE", "50")), 250))
BENCHMARK_MAX_LAG_BUSINESS_DAYS = max(
    int(os.getenv("MF_METRIC_BENCHMARK_MAX_LAG_BUSINESS_DAYS", "3")),
    0,
)
MIN_ALPHA_BETA_COVERAGE = min(
    max(float(os.getenv("MF_METRIC_MIN_ALPHA_BETA_COVERAGE", "0.90")), 0.0),
    1.0,
)


def _enabled(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _cache_row_pages(
    repo: StockRepository,
    scheme_codes: list[str],
    limit: int,
) -> Iterator[list[dict[str, Any]]]:
    selected_codes = scheme_codes[:limit] if limit > 0 else scheme_codes
    for start in range(0, len(selected_codes), PAGE_SIZE):
        code_batch = selected_codes[start : start + PAGE_SIZE]
        if not code_batch:
            continue
        response = (
            repo.supabase.table("nav_api_cache")
            .select("scheme_code,payload,point_count,last_nav_date,fetched_at,updated_at")
            .in_("scheme_code", code_batch)
            .execute()
        )
        batch = sorted(
            (row for row in (response.data or []) if isinstance(row, dict)),
            key=lambda row: str(row.get("scheme_code") or ""),
        )
        if batch:
            yield batch


def _core_rows(repo: StockRepository, scheme_codes: list[str]) -> dict[str, dict[str, Any]]:
    if not scheme_codes:
        return {}
    response = (
        repo.supabase.table("mutual_fund_core_snapshot")
        .select("scheme_code,alpha,beta,provider_payload")
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
        .select("date,close,source")
        .eq("symbol", "NIFTY")
        .order("date", desc=True)
        .limit(2200)
        .execute()
    )
    by_date: dict[str, dict[str, Any]] = {}
    for row in response.data or []:
        if isinstance(row, dict) and row.get("date") and row.get("close") not in (None, ""):
            by_date[str(row["date"])] = row
    return [by_date[key] for key in sorted(by_date)]


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _business_day_lag(latest: date, current: date) -> int:
    if latest >= current:
        return 0
    lag = 0
    cursor = latest + timedelta(days=1)
    while cursor <= current:
        if cursor.weekday() < 5:
            lag += 1
        cursor += timedelta(days=1)
    return lag


def _benchmark_snapshot(
    benchmark_rows: list[dict[str, Any]],
    *,
    now: datetime,
) -> dict[str, Any]:
    dates = [parsed for parsed in (_parse_date(row.get("date")) for row in benchmark_rows) if parsed]
    latest = max(dates, default=None)
    earliest = min(dates, default=None)
    lag = _business_day_lag(latest, now.date()) if latest else None
    sources = sorted({str(row.get("source")) for row in benchmark_rows if row.get("source")})
    return {
        "identifier": "NIFTY",
        "mode": "proxy",
        "sources": sources,
        "start_date": earliest.isoformat() if earliest else None,
        "end_date": latest.isoformat() if latest else None,
        "point_count": len(dates),
        "business_day_lag": lag,
        "fresh": bool(latest and lag is not None and lag <= BENCHMARK_MAX_LAG_BUSINESS_DAYS),
    }


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

    metrics, diagnostics = compute_nav_metrics_with_diagnostics(
        history,
        risk_free_rate=RISK_FREE_RATE,
        benchmark_rows=benchmark_rows,
    )
    last_known_good_used = False
    if metrics.get("alpha") is None or metrics.get("beta") is None:
        previous_alpha = existing.get("alpha")
        previous_beta = existing.get("beta")
        if previous_alpha not in (None, "") and previous_beta not in (None, ""):
            metrics["alpha"] = previous_alpha
            metrics["beta"] = previous_beta
            last_known_good_used = True
    provider_payload = existing.get("provider_payload")
    provider_payload = (
        dict(provider_payload)
        if isinstance(provider_payload, dict)
        else {"legacy_provider_payload": provider_payload}
        if provider_payload not in (None, "")
        else {}
    )
    benchmark = _benchmark_snapshot(benchmark_rows, now=datetime.fromisoformat(computed_at))
    calculation_status = (
        "last_known_good"
        if last_known_good_used
        else diagnostics["calculation_status"]
    )
    provider_payload["metric_snapshot"] = {
        "version": NAV_METRIC_SNAPSHOT_VERSION,
        "as_of_date": cache_row.get("last_nav_date") or history[-1].get("nav_date") or history[-1].get("date"),
        "computed_at": computed_at,
        "history_points": int(cache_row.get("point_count") or len(history)),
        "benchmark": benchmark["identifier"],
        "benchmark_mode": benchmark["mode"],
        "benchmark_sources": benchmark["sources"],
        "benchmark_start_date": diagnostics["benchmark_start_date"],
        "benchmark_end_date": diagnostics["benchmark_end_date"],
        "fund_start_date": diagnostics["fund_start_date"],
        "fund_end_date": diagnostics["fund_end_date"],
        "overlap_points": diagnostics["overlap_points"],
        "minimum_overlap_points": diagnostics["minimum_overlap_points"],
        "calculation_status": calculation_status,
        "calculation_failure_reason": (
            None
            if diagnostics["calculation_status"] == "computed"
            else diagnostics["calculation_status"]
        ),
        "last_known_good_used": last_known_good_used,
        "risk_free_rate": RISK_FREE_RATE,
    }
    return {
        "scheme_code": scheme_code,
        **metrics,
        "provider_payload": provider_payload,
    }


def _write_output(path: str | None, payload: dict[str, Any]) -> None:
    if path:
        Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh NAV-derived mutual-fund metrics.")
    parser.add_argument("--output", default=os.getenv("MF_METRIC_REFRESH_OUTPUT", ""))
    args = parser.parse_args()
    if not _enabled("ENABLE_MF_SNAPSHOT_METRICS_REFRESH", True):
        logger.info("ENABLE_MF_SNAPSHOT_METRICS_REFRESH is false. Skipping.")
        return 0

    repo = StockRepository()
    if not repo.supabase:
        logger.error("Supabase client is not configured.")
        return 1

    limit = max(int(os.getenv("MF_METRIC_REFRESH_SCHEME_LIMIT", "0")), 0)
    benchmark_rows = _benchmark_rows(repo)
    now = datetime.now(timezone.utc)
    computed_at = now.isoformat()
    benchmark = _benchmark_snapshot(benchmark_rows, now=now)
    run = ProviderRun(
        provider="derived_metrics",
        job_name="refresh_mf_snapshot_metrics",
        status="running",
        started_at=now,
        finished_at=None,
        symbols_attempted=0,
        symbols_succeeded=0,
        symbols_failed=0,
        error_summary=None,
        metadata={"benchmark": benchmark},
    )
    run_id = repo.create_provider_run(run)
    if not benchmark["fresh"]:
        payload = {
            "status": "failed",
            "reason": "benchmark_stale_or_missing",
            "benchmark": benchmark,
        }
        _write_output(args.output, payload)
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.error_summary = payload["reason"]
        run.metadata = payload
        if run_id:
            repo.update_provider_run(run_id, run)
        logger.error("MF metric refresh blocked: %s", json.dumps(payload, default=str))
        return 1
    cached = 0
    updated = 0
    skipped = 0
    eligible = 0
    alpha_beta = 0
    last_known_good = 0
    target_codes = [row["scheme_code"] for row in supported_metric_targets(repo.supabase)]

    for batch in _cache_row_pages(repo, target_codes, limit):
        cached += len(batch)
        scheme_codes = [str(row.get("scheme_code")) for row in batch if row.get("scheme_code") not in (None, "")]
        existing = _core_rows(repo, scheme_codes)
        metric_rows = []
        for cache_row in batch:
            code = str(cache_row.get("scheme_code") or "")
            metric_row = _metric_row(cache_row, existing.get(code, {}), benchmark_rows, computed_at)
            if metric_row:
                metric_rows.append(metric_row)
                snapshot = metric_row.get("provider_payload", {}).get("metric_snapshot", {})
                if int(snapshot.get("overlap_points") or 0) >= int(snapshot.get("minimum_overlap_points") or 30):
                    eligible += 1
                    if metric_row.get("alpha") is not None and metric_row.get("beta") is not None:
                        alpha_beta += 1
                if snapshot.get("last_known_good_used"):
                    last_known_good += 1
            else:
                skipped += 1
        repo.upsert_mutual_fund_core_snapshot_rows(metric_rows)
        updated += len(metric_rows)

    if cached == 0:
        failure_reason = "no_cached_nav_histories"
    elif eligible == 0:
        failure_reason = "no_metric_eligible_histories"
    elif alpha_beta / eligible < MIN_ALPHA_BETA_COVERAGE:
        failure_reason = "alpha_beta_coverage_below_threshold"
    else:
        failure_reason = None

    payload = {
        "status": "success" if failure_reason is None else "failed",
        "reason": failure_reason,
        "cached": cached,
        "updated": updated,
        "skipped": skipped,
        "eligible": eligible,
        "alpha_beta_count": alpha_beta,
        "alpha_beta_coverage": round(alpha_beta / eligible, 4) if eligible else 0.0,
        "minimum_alpha_beta_coverage": MIN_ALPHA_BETA_COVERAGE,
        "last_known_good_used": last_known_good,
        "benchmark": benchmark,
        "version": NAV_METRIC_SNAPSHOT_VERSION,
    }
    _write_output(args.output, payload)
    run.status = payload["status"]
    run.finished_at = datetime.now(timezone.utc)
    run.symbols_attempted = cached
    run.symbols_succeeded = alpha_beta
    run.symbols_failed = max(eligible - alpha_beta, 0) + skipped
    run.error_summary = failure_reason
    run.metadata = payload
    if run_id:
        repo.update_provider_run(run_id, run)

    logger.info(
        "MF snapshot metric refresh complete: cached=%s updated=%s skipped=%s eligible=%s alpha_beta=%s version=%s",
        cached,
        updated,
        skipped,
        eligible,
        alpha_beta,
        NAV_METRIC_SNAPSHOT_VERSION,
    )
    return 0 if failure_reason is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
