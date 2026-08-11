from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.database import supabase
from app.mf_ingestion.constants import ReportMonthWindow
from app.mf_ingestion.services.promotion_review_service import (
    find_holdings_out_of_band,
    find_risk_conflicts,
)
from app.mf_ingestion.sources.registry import PRODUCTION_TARGET_AMC_KEYS

AMC_KEY_ALIASES = {"absl": "aditya_birla"}

# Ordered so the table/JSON output groups causes from "systemic parser bug"
# (fix once, many conflicts disappear) to "one-off data issue" (fix per row).
HOLDINGS_CAUSES = (
    "out_of_band_total",
    "no_percent_aum_value",
    "non_valid_status",
)


def _normalize_amc_key(value: object) -> str:
    key = str(value or "").strip().lower()
    return AMC_KEY_ALIASES.get(key, key)


def _categorize_holdings_conflict(row: dict[str, Any], lower: float, upper: float) -> dict[str, Any]:
    """Classify one find_holdings_out_of_band() row by root cause. `causes` holds
    the reason(s) this row was flagged at all; `tags` holds contributing signals
    that aren't independently disqualifying (a row can have a missing ISIN or be
    staged in another document and still be perfectly in-band)."""
    total = row.get("total_percent_aum")
    causes: list[str] = []
    if total is None:
        causes.append("no_percent_aum_value")
    elif not (lower <= total <= upper):
        causes.append("out_of_band_total")
    if set(row.get("validation_statuses") or []) - {"valid"}:
        causes.append("non_valid_status")
    if not causes:
        causes.append("non_valid_status")

    tags: list[str] = []
    if (row.get("holding_rows_missing_isin") or 0) > 0:
        tags.append("missing_isin")
    if (row.get("also_staged_in_n_other_documents") or 0) > 0:
        tags.append("duplicate_across_documents")

    return {"causes": causes, "tags": tags}


def build_conflict_attribution(
    *,
    amcs: list[str],
    report_months: list[str],
    min_confidence: float = 90.0,
) -> dict[str, Any]:
    window = ReportMonthWindow()
    per_amc: dict[str, Any] = {}

    for amc in amcs:
        normalized_amc = _normalize_amc_key(amc)
        by_cause: dict[str, int] = defaultdict(int)
        by_tag: dict[str, int] = defaultdict(int)
        examples: dict[str, list[str]] = defaultdict(list)
        total_conflicts = 0

        for report_month in report_months:
            for row in find_risk_conflicts(
                amc=normalized_amc, report_month=report_month, min_confidence=min_confidence
            ):
                total_conflicts += 1
                by_cause["risk_mismatch"] += 1
                if len(examples["risk_mismatch"]) < 3:
                    examples["risk_mismatch"].append(str(row.get("raw_scheme_name") or row.get("staged_scheme_code")))

            for row in find_holdings_out_of_band(amc=normalized_amc, report_month=report_month):
                total_conflicts += 1
                classification = _categorize_holdings_conflict(row, window.lower_bound_pct, window.upper_bound_pct)
                label = str(row.get("raw_scheme_name") or row.get("scheme_key"))
                for cause in classification["causes"]:
                    key = f"holdings_{cause}"
                    by_cause[key] += 1
                    if len(examples[key]) < 3:
                        examples[key].append(label)
                for tag in classification["tags"]:
                    by_tag[f"holdings_{tag}"] += 1

        per_amc[normalized_amc] = {
            "total_conflicts": total_conflicts,
            "by_cause": dict(sorted(by_cause.items(), key=lambda item: -item[1])),
            "contributing_tags": dict(sorted(by_tag.items(), key=lambda item: -item[1])),
            "examples": {cause: names for cause, names in examples.items()},
        }

    ranked_amcs = sorted(per_amc, key=lambda amc: -per_amc[amc]["total_conflicts"])
    return {
        "report_months": report_months,
        "min_confidence": min_confidence,
        "amcs": per_amc,
        "ranked_amcs": ranked_amcs,
    }


def _print_table(report: dict[str, Any]) -> None:
    print(f"{'AMC':<16} {'TOTAL':<7} TOP CAUSES (count)")
    for amc in report["ranked_amcs"]:
        data = report["amcs"][amc]
        if not data["total_conflicts"]:
            continue
        top_causes = ", ".join(f"{cause}={count}" for cause, count in list(data["by_cause"].items())[:4])
        print(f"{amc:<16} {data['total_conflicts']:<7} {top_causes}")
    zero = [amc for amc in report["ranked_amcs"] if not report["amcs"][amc]["total_conflicts"]]
    if zero:
        print(f"\nNo flagged conflicts: {', '.join(zero)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only report attributing staged-vs-live conflicts to a root cause per "
            "AMC, ranked by conflict volume. Use this to decide which AMC's parser "
            "adapter to fix next -- never writes to any table."
        )
    )
    parser.add_argument("--report-months", required=True, help="Comma-separated YYYY-MM-01 values")
    parser.add_argument("--amcs", default=",".join(PRODUCTION_TARGET_AMC_KEYS))
    parser.add_argument("--min-confidence", type=float, default=90.0, help="risk scope only")
    parser.add_argument("--format", default="table", choices=("table", "json"))
    args = parser.parse_args()

    if not supabase:
        print(json.dumps({"status": "error", "issues": ["supabase_not_configured"]}))
        return 1

    amcs = [value.strip().lower() for value in args.amcs.split(",") if value.strip()]
    report_months = [value.strip() for value in args.report_months.split(",") if value.strip()]

    report = build_conflict_attribution(
        amcs=amcs, report_months=report_months, min_confidence=args.min_confidence
    )

    if args.format == "json":
        print(json.dumps({"status": "ok", **report}, indent=2, default=str))
    else:
        _print_table(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
