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
from app.mf_ingestion.services.promotion_review_service import (
    find_holdings_out_of_band,
    find_risk_conflicts,
)


def _print_table(rows: list[dict[str, Any]], scope: str) -> None:
    if not rows:
        print("No flagged rows -- nothing blocking this scope.")
        return
    if scope == "risk":
        print(
            f"{'FAMILY':<10} {'STAGED SCHEME':<28} {'STAGED RISK':<14} "
            f"{'LIVE MISMATCH (scheme: risk)':<50} {'DECISION':<12} SOURCE"
        )
        for row in rows:
            mismatches = "; ".join(
                f"{m['scheme_code']}: {m['live_risk_level']}" for m in row["mismatched_live_schemes"]
            )
            decision = (row.get("decision") or {}).get("resolution") or "-"
            print(
                f"{row['family_id']:<10} {str(row['raw_scheme_name'])[:27]:<28} "
                f"{str(row['staged_risk_level'])[:13]:<14} {mismatches[:49]:<50} {decision:<12} {row.get('source_url') or ''}"
            )
    else:
        print(
            f"{'SCHEME':<28} {'TOTAL %AUM':<12} {'BAND':<12} {'STATUS':<14} "
            f"{'ROWS':<6} {'NO ISIN':<8} {'ALSO IN':<8} {'DECISION':<12} SOURCE"
        )
        for row in rows:
            band = f"{row['expected_band'][0]}-{row['expected_band'][1]}"
            statuses = ",".join(row["validation_statuses"]) or "-"
            also_in = f"{row['also_staged_in_n_other_documents']} doc(s)" if row["also_staged_in_n_other_documents"] else "-"
            decision = (row.get("decision") or {}).get("resolution") or "-"
            print(
                f"{str(row['raw_scheme_name'] or row['scheme_key'])[:27]:<28} "
                f"{str(row['total_percent_aum']):<12} {band:<12} {statuses[:13]:<14} "
                f"{row['holding_row_count']:<6} {row['holding_rows_missing_isin']:<8} {also_in:<8} {decision:<12} {row.get('source_url') or ''}"
            )
    print(f"\n{len(rows)} flagged.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only report of staged-vs-live conflicts blocking a specific promotion "
            "scope. Never writes to any table -- for reviewing before a manual `Promote "
            "MF Disclosures` / `Promote MF AMC Disclosures` workflow run, or before using "
            "the admin Promotion Review panel."
        )
    )
    parser.add_argument("--amc", required=True, help="e.g. icici, kotak")
    parser.add_argument("--scope", required=True, choices=("risk", "holdings"))
    parser.add_argument("--report-month", required=True, help="Exact month as YYYY-MM-01")
    parser.add_argument("--min-confidence", type=float, default=90.0, help="risk scope only")
    parser.add_argument("--format", default="table", choices=("table", "json"))
    args = parser.parse_args()

    if not supabase:
        print(json.dumps({"status": "error", "issues": ["supabase_not_configured"]}))
        return 1

    if args.scope == "risk":
        rows = find_risk_conflicts(
            amc=args.amc, report_month=args.report_month, min_confidence=args.min_confidence
        )
    else:
        rows = find_holdings_out_of_band(amc=args.amc, report_month=args.report_month)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "status": "ok",
                    "amc": args.amc,
                    "scope": args.scope,
                    "report_month": args.report_month,
                    "count": len(rows),
                    "rows": rows,
                },
                indent=2,
                default=str,
            )
        )
    else:
        print(f"AMC={args.amc} scope={args.scope} report_month={args.report_month}\n")
        _print_table(rows, args.scope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
