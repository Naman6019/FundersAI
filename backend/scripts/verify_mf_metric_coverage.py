from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.admin_service import _mf_metric_coverage


def coverage_failures(
    coverage: dict[str, Any],
    *,
    history_minimum: float,
    alpha_beta_minimum: float,
    benchmark_risk_minimum: float,
) -> list[str]:
    supported = int(coverage.get("supported_mapped_total") or 0)
    history_ratio = int(coverage.get("history_ready_count") or 0) / supported if supported else 0.0
    history_alpha_beta_ratio = (
        int(coverage.get("supported_history_alpha_beta_count") or 0) / supported
        if supported
        else 0.0
    )
    failures: list[str] = []
    if supported == 0:
        failures.append("no_supported_mapped_schemes")
    if history_ratio < history_minimum:
        failures.append("history_coverage_below_threshold")
    if history_alpha_beta_ratio < alpha_beta_minimum:
        failures.append("alpha_beta_coverage_below_threshold")
    if float(coverage.get("supported_benchmark_coverage") or 0) < benchmark_risk_minimum:
        failures.append("benchmark_coverage_below_threshold")
    if float(coverage.get("supported_risk_coverage") or 0) < benchmark_risk_minimum:
        failures.append("risk_coverage_below_threshold")
    if not bool((coverage.get("benchmark_freshness") or {}).get("fresh")):
        failures.append("benchmark_stale")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-minimum", type=float, default=float(os.getenv("MF_METRIC_HISTORY_COVERAGE_MIN", "0.90")))
    parser.add_argument("--alpha-beta-minimum", type=float, default=float(os.getenv("MF_METRIC_ALPHA_BETA_COVERAGE_MIN", "0.90")))
    parser.add_argument("--benchmark-risk-minimum", type=float, default=float(os.getenv("MF_OFFICIAL_FIELD_COVERAGE_MIN", "0.95")))
    parser.add_argument("--output", default="mf-metric-coverage-health.json")
    args = parser.parse_args()
    coverage = _mf_metric_coverage(datetime.now(timezone.utc))
    failures = coverage_failures(
        coverage,
        history_minimum=args.history_minimum,
        alpha_beta_minimum=args.alpha_beta_minimum,
        benchmark_risk_minimum=args.benchmark_risk_minimum,
    )
    payload = {"status": "success" if not failures else "failed", "failures": failures, **coverage}
    Path(args.output).write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
