from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.models.stock_models import ProviderRun
from app.repositories.stock_repository import StockRepository
from app.services.mf_metric_target_service import prioritized_metric_targets
from app.services.mfapi_service import get_cached_nav_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _write_output(path: str | None, payload: dict[str, Any]) -> None:
    if path:
        Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh bounded NAV histories for mapped official MF schemes.")
    parser.add_argument("--limit", type=int, default=int(os.getenv("MF_METRIC_INPUT_BATCH_SIZE", "100")))
    parser.add_argument("--retries", type=int, default=int(os.getenv("MF_METRIC_INPUT_RETRIES", "2")))
    parser.add_argument("--minimum-history-points", type=int, default=31)
    parser.add_argument("--minimum-success-ratio", type=float, default=float(os.getenv("MF_METRIC_INPUT_MIN_SUCCESS_RATIO", "0.90")))
    parser.add_argument("--output", default=os.getenv("MF_METRIC_INPUT_OUTPUT", ""))
    args = parser.parse_args()
    if args.limit < 1 or args.retries < 0 or args.minimum_history_points < 2:
        parser.error("limit must be positive, retries non-negative, and minimum-history-points at least two")

    repo = StockRepository()
    if not repo.supabase:
        logger.error("Supabase client is not configured.")
        return 1

    started_at = datetime.now(timezone.utc)
    targets = prioritized_metric_targets(repo.supabase)
    selected = targets[: args.limit]
    run = ProviderRun(
        provider="mfapi",
        job_name="refresh_mf_metric_inputs",
        status="running",
        started_at=started_at,
        finished_at=None,
        symbols_attempted=len(selected),
        symbols_succeeded=0,
        symbols_failed=0,
        error_summary=None,
        metadata={"target_count": len(targets), "batch_limit": args.limit},
    )
    run_id = repo.create_provider_run(run)

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    last_known_good_count = 0
    for target in selected:
        scheme_code = target["scheme_code"]
        result: dict[str, Any] = {}
        for attempt in range(args.retries + 1):
            result = get_cached_nav_history(scheme_code, force_refresh=True)
            if result.get("cache_status") in {"refreshed", "hit"}:
                break
            if attempt < args.retries:
                time.sleep(0.5 * (2**attempt))

        point_count = int(result.get("point_count") or 0)
        refreshed = result.get("cache_status") in {"refreshed", "hit"}
        if refreshed and point_count >= args.minimum_history_points:
            successes.append(
                {
                    "scheme_code": scheme_code,
                    "family_id": target["family_id"],
                    "amc_code": target["amc_code"],
                    "point_count": point_count,
                    "cache_status": result.get("cache_status"),
                }
            )
            continue

        if result.get("cache_status") == "stale_fallback":
            last_known_good_count += 1
        error = result.get("error")
        failures.append(
            {
                "scheme_code": scheme_code,
                "family_id": target["family_id"],
                "amc_code": target["amc_code"],
                "point_count": point_count,
                "cache_status": result.get("cache_status"),
                "error": error,
                "reason": (
                    "insufficient_history"
                    if refreshed and point_count < args.minimum_history_points
                    else "refresh_failed"
                ),
            }
        )

    attempted = len(selected)
    success_ratio = len(successes) / attempted if attempted else 0.0
    failure_reason = None
    if not targets:
        failure_reason = "no_supported_metric_targets"
    elif not selected:
        failure_reason = "no_targets_selected"
    elif success_ratio < min(max(args.minimum_success_ratio, 0.0), 1.0):
        failure_reason = "metric_input_success_ratio_below_threshold"

    payload = {
        "status": "success" if failure_reason is None else "failed",
        "reason": failure_reason,
        "target_count": len(targets),
        "attempted": attempted,
        "succeeded": len(successes),
        "failed": len(failures),
        "success_ratio": round(success_ratio, 4),
        "minimum_success_ratio": args.minimum_success_ratio,
        "last_known_good_used": last_known_good_count,
        "successes": successes,
        "failures": failures,
    }
    _write_output(args.output, payload)

    run.status = payload["status"]
    run.finished_at = datetime.now(timezone.utc)
    run.symbols_succeeded = len(successes)
    run.symbols_failed = len(failures)
    run.error_summary = failure_reason
    run.metadata = payload
    if run_id:
        repo.update_provider_run(run_id, run)

    logger.info("MF metric input refresh: %s", json.dumps(payload, default=str))
    return 0 if failure_reason is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
