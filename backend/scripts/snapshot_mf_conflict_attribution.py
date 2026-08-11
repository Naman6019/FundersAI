from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.database import supabase
from scripts.report_mf_conflict_attribution import build_conflict_attribution
from app.mf_ingestion.sources.registry import PRODUCTION_TARGET_AMC_KEYS

SNAPSHOT_TABLE = "mf_conflict_attribution_snapshots"


def _latest_snapshot(amc_code: str) -> dict[str, Any] | None:
    rows = (
        supabase.table(SNAPSHOT_TABLE)
        .select("taken_at,total_conflicts,by_cause")
        .eq("amc_code", amc_code)
        .order("taken_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def take_snapshot(
    *, amcs: list[str], report_months: list[str], min_confidence: float = 90.0
) -> dict[str, Any]:
    """Runs the conflict-attribution report, records one row per AMC into
    mf_conflict_attribution_snapshots, and returns each AMC's delta against its
    immediately preceding snapshot (None if this is the first snapshot for that
    AMC) -- read-only against every table except an insert into the snapshot
    table itself."""
    report = build_conflict_attribution(
        amcs=amcs, report_months=report_months, min_confidence=min_confidence
    )

    results: dict[str, Any] = {}
    for amc in amcs:
        data = report["amcs"].get(amc, {"total_conflicts": 0, "by_cause": {}, "contributing_tags": {}})
        previous = _latest_snapshot(amc)
        delta = None
        if previous is not None:
            delta = data["total_conflicts"] - int(previous["total_conflicts"])

        inserted = (
            supabase.table(SNAPSHOT_TABLE)
            .insert(
                {
                    "report_months": report_months,
                    "amc_code": amc,
                    "total_conflicts": data["total_conflicts"],
                    "by_cause": data["by_cause"],
                    "contributing_tags": data["contributing_tags"],
                }
            )
            .execute()
            .data
        )
        results[amc] = {
            "total_conflicts": data["total_conflicts"],
            "previous_total_conflicts": int(previous["total_conflicts"]) if previous else None,
            "delta": delta,
            "snapshot_id": (inserted or [{}])[0].get("id"),
        }
    return results


def _print_table(results: dict[str, Any]) -> None:
    print(f"{'AMC':<16} {'TOTAL':<7} {'PREVIOUS':<10} DELTA")
    for amc, data in sorted(results.items(), key=lambda item: -item[1]["total_conflicts"]):
        previous = data["previous_total_conflicts"]
        delta = data["delta"]
        delta_str = "-" if delta is None else (f"+{delta}" if delta > 0 else str(delta))
        print(f"{amc:<16} {data['total_conflicts']:<7} {previous if previous is not None else '-':<10} {delta_str}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Runs the per-AMC conflict-attribution report and records one snapshot row "
            "per AMC into mf_conflict_attribution_snapshots, printing the delta against "
            "each AMC's previous snapshot. Intended to run on a schedule (e.g. after "
            "sync-mf-disclosures) so conflict volume is a visible trend, not just a "
            "point-in-time count."
        )
    )
    parser.add_argument("--report-months", required=True, help="Comma-separated YYYY-MM-01 values")
    parser.add_argument("--amcs", default=",".join(PRODUCTION_TARGET_AMC_KEYS))
    parser.add_argument("--min-confidence", type=float, default=90.0)
    parser.add_argument("--format", default="table", choices=("table", "json"))
    args = parser.parse_args()

    if not supabase:
        print(json.dumps({"status": "error", "issues": ["supabase_not_configured"]}))
        return 1

    amcs = [value.strip().lower() for value in args.amcs.split(",") if value.strip()]
    report_months = [value.strip() for value in args.report_months.split(",") if value.strip()]

    results = take_snapshot(amcs=amcs, report_months=report_months, min_confidence=args.min_confidence)

    if args.format == "json":
        print(json.dumps({"status": "ok", "results": results}, indent=2, default=str))
    else:
        _print_table(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
