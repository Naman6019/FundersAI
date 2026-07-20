from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.provider_usage import get_first_usage_row, get_usage_rows


def _float_env(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _runtime_legacy_references() -> list[str]:
    legacy_name = "mutual_fund_" + "nav_history"
    allowed = {
        (BACKEND_DIR / "app" / "mf_ingestion" / "jobs" / "archive_mf_nav_history.py").resolve(),
        (BACKEND_DIR / "migrations" / "20260512_quota_safe_provider_architecture.sql").resolve(),
        (BACKEND_DIR / "manual_migrations" / "drop_mutual_fund_nav_history_after_readiness.sql").resolve(),
        Path(__file__).resolve(),
    }
    offenders: list[str] = []
    roots = (BACKEND_DIR / "app", BACKEND_DIR / "scripts", REPO_ROOT / "frontend", REPO_ROOT / ".github" / "workflows")
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.resolve() in allowed or "__pycache__" in path.parts:
                continue
            if path.suffix not in {".py", ".ts", ".tsx", ".yml", ".yaml"}:
                continue
            if legacy_name in path.read_text(encoding="utf-8", errors="ignore"):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    return offenders


def build_readiness_report(archive_report: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    required_days = max(_float_env("MF_NAV_CACHE_OBSERVATION_DAYS", "7"), 0)
    minimum_requests = max(int(os.getenv("MF_NAV_CACHE_MIN_OBSERVED_REQUESTS", "10")), 1)
    max_failure_rate = max(_float_env("MF_NAV_CACHE_MAX_FAILURE_RATE", "0.10"), 0)
    max_stale_rate = max(_float_env("MF_NAV_CACHE_MAX_STALE_RATE", "0.25"), 0)
    usage_rows = get_usage_rows("mfapi", current - timedelta(days=max(required_days + 30, 31)), current, limit=10000)
    cache_rows = [row for row in usage_rows if str(row.get("endpoint") or "").startswith("nav_cache/")]
    first_cache_row = get_first_usage_row(
        "mfapi",
        current - timedelta(days=max(required_days + 30, 31)),
        current,
        endpoint_prefix="nav_cache/",
    )
    earliest = None
    if first_cache_row:
        try:
            earliest = datetime.fromisoformat(str(first_cache_row["created_at"]).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            earliest = None
    observed_days = ((current - earliest.astimezone(timezone.utc)).total_seconds() / 86400) if earliest else 0.0
    observed_requests = len(cache_rows)
    failures = sum(1 for row in usage_rows if not bool(row.get("success", True)))
    stale_fallbacks = sum(1 for row in cache_rows if row.get("endpoint") == "nav_cache/stale_fallback")
    hits = sum(1 for row in cache_rows if row.get("endpoint") == "nav_cache/hit")
    refreshes = sum(1 for row in cache_rows if row.get("endpoint") == "nav_cache/refresh")
    failure_rate = failures / len(usage_rows) if usage_rows else 1.0
    stale_rate = stale_fallbacks / observed_requests if observed_requests else 1.0
    legacy_references = _runtime_legacy_references()

    checks = {
        "archive_verified": bool(archive_report.get("archive_verified")),
        "observation_window_complete": observed_days >= required_days,
        "minimum_requests_met": observed_requests >= minimum_requests,
        "cache_hits_observed": hits > 0,
        "cache_refreshes_observed": refreshes > 0,
        "failure_rate_healthy": failure_rate <= max_failure_rate,
        "stale_rate_healthy": stale_rate <= max_stale_rate,
        "no_runtime_legacy_references": not legacy_references,
    }
    return {
        "checked_at": current.isoformat(),
        "drop_ready": all(checks.values()),
        "checks": checks,
        "metrics": {
            "observed_days": round(observed_days, 3),
            "required_days": required_days,
            "observed_requests": observed_requests,
            "provider_events": len(usage_rows),
            "minimum_requests": minimum_requests,
            "hits": hits,
            "refreshes": refreshes,
            "stale_fallbacks": stale_fallbacks,
            "failures": failures,
            "failure_rate": round(failure_rate, 4),
            "stale_rate": round(stale_rate, 4),
        },
        "runtime_legacy_references": legacy_references,
        "archive": archive_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate the destructive NAV history drop.")
    parser.add_argument("--archive-report", required=True)
    parser.add_argument("--output", default="nav-history-drop-readiness.json")
    args = parser.parse_args()
    archive_report = json.loads(Path(args.archive_report).read_text(encoding="utf-8"))
    report = build_readiness_report(archive_report)
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["drop_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
