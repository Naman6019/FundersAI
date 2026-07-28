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
from app.mf_ingestion.sources.registry import PRODUCTION_TARGET_AMC_KEYS

CORE_FIELDS = ("aum", "expense_ratio", "benchmark", "fund_manager", "risk_level")
AMC_KEY_ALIASES = {"absl": "aditya_birla"}
NON_SECTOR_SCHEME_MARKERS = (
    "fund of fund",
    " fof",
    "gold etf",
    "silver etf",
    "liquid etf",
    "overnight fund",
    "money market fund",
    "short duration fund",
    "low duration fund",
    "ultra short duration fund",
    "medium duration fund",
    "long duration fund",
    "corporate bond fund",
    "credit risk fund",
    "banking and psu debt fund",
    "banking & psu debt fund",
    "gilt fund",
    "floater fund",
)


def _ratio(count: int, total: int) -> float:
    return round((count / total) * 100.0, 2) if total else 0.0


def _normalize_amc_key(value: object) -> str:
    key = str(value or "").strip().lower()
    return AMC_KEY_ALIASES.get(key, key)


def _sector_not_applicable(raw_scheme_name: object) -> bool:
    normalized = f" {str(raw_scheme_name or '').strip().lower()} "
    return any(marker in normalized for marker in NON_SECTOR_SCHEME_MARKERS)


def _get_filtered(
    table: str,
    columns: str,
    *,
    filters: dict[str, object],
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        query = supabase.table(table).select(columns)
        for column, value in filters.items():
            query = query.eq(column, value)
        page = query.order("id").range(start, start + page_size - 1).execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        start += page_size


def _get_by_source_document_ids(
    table: str,
    columns: str,
    source_document_ids: list[str],
    *,
    chunk_size: int = 1,
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk_start in range(0, len(source_document_ids), chunk_size):
        chunk = source_document_ids[chunk_start : chunk_start + chunk_size]
        start = 0
        while True:
            query = supabase.table(table).select(columns)
            if len(chunk) == 1:
                query = query.eq("source_document_id", chunk[0])
            else:
                query = query.in_("source_document_id", chunk)
            page = (
                query.order("id")
                .range(start, start + page_size - 1)
                .execute()
                .data
                or []
            )
            rows.extend(page)
            if len(page) < page_size:
                break
            start += page_size
    return rows


def build_staging_coverage(
    *,
    report_month: str,
    amcs: list[str],
    candidates: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
    sector_allocations: list[dict[str, Any]] | None = None,
    threshold: float,
) -> dict[str, Any]:
    sector_allocations = sector_allocations or []
    report: dict[str, Any] = {}
    for amc in amcs:
        normalized_amc = _normalize_amc_key(amc)
        current_candidates = [
            row
            for row in candidates
            if _normalize_amc_key(row.get("amc_code")) == normalized_amc
            and str(row.get("report_month") or "") == report_month
        ]
        candidate_rows = [
            row
            for row in current_candidates
            if row.get("mapping_status") == "mapped" and row.get("mapped_family_id")
        ]
        observed_core_groups = {
            (
                f"family:{row['mapped_family_id']}"
                if row.get("mapping_status") == "mapped" and row.get("mapped_family_id")
                else f"raw:{row.get('normalized_scheme_name') or row.get('raw_scheme_name')}"
            )
            for row in current_candidates
        }
        core_families: dict[str, set[str]] = defaultdict(set)
        for row in candidate_rows:
            family_id = str(row["mapped_family_id"])
            for field in CORE_FIELDS:
                if row.get(field) not in (None, ""):
                    core_families[field].add(family_id)

        current_holdings = [
            row
            for row in holdings
            if _normalize_amc_key(row.get("amc_code")) == normalized_amc
            and str(row.get("report_month") or "") == report_month
        ]
        holding_rows = [
            row
            for row in current_holdings
            if row.get("mapping_status") == "mapped" and row.get("mapped_family_id")
        ]
        observed_portfolio_groups = {
            (
                f"family:{row['mapped_family_id']}"
                if row.get("mapping_status") == "mapped" and row.get("mapped_family_id")
                else f"raw:{str(row.get('raw_scheme_name') or '').strip().lower()}"
            )
            for row in current_holdings
            if row.get("mapped_family_id") or row.get("raw_scheme_name")
        }
        holding_families = {str(row["mapped_family_id"]) for row in holding_rows}
        sector_families = {
            str(row["mapped_family_id"])
            for row in holding_rows
            if row.get("sector") not in (None, "")
        }
        direct_sector_families = {
            str(row["mapped_family_id"])
            for row in sector_allocations
            if _normalize_amc_key(row.get("amc_code")) == normalized_amc
            and str(row.get("report_month") or "") == report_month
            and row.get("mapping_status") == "mapped"
            and row.get("mapped_family_id")
            and row.get("validation_status") == "valid"
            and row.get("sector_name") not in (None, "")
        }
        sector_families.update(direct_sector_families)
        holding_rows_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in holding_rows:
            holding_rows_by_family[str(row["mapped_family_id"])].append(row)
        sector_applicable_families = {
            family_id
            for family_id, rows in holding_rows_by_family.items()
            if family_id in sector_families
            or any(not _sector_not_applicable(row.get("raw_scheme_name")) for row in rows)
        }
        sector_applicable_families.update(direct_sector_families)
        sector_not_applicable_families = holding_families - sector_applicable_families
        counts = {
            **{field: len(core_families[field]) for field in CORE_FIELDS},
            "holdings": len(holding_families),
            "sectors": len(sector_families),
        }
        core_total = len({str(row["mapped_family_id"]) for row in candidate_rows})
        portfolio_total = len(holding_families)
        percentages = {
            **{field: _ratio(counts[field], core_total) for field in CORE_FIELDS},
            "holdings": _ratio(counts["holdings"], portfolio_total),
            "sectors": (
                _ratio(counts["sectors"], len(sector_applicable_families))
                if sector_applicable_families
                else (100.0 if portfolio_total else 0.0)
            ),
        }
        mapping_percentages = {
            "core": _ratio(core_total, len(observed_core_groups)),
            "portfolio": _ratio(portfolio_total, len(observed_portfolio_groups)),
        }
        report[normalized_amc] = {
            "observed_core_groups": len(observed_core_groups),
            "mapped_core_families": core_total,
            "observed_portfolio_groups": len(observed_portfolio_groups),
            "mapped_portfolio_families": portfolio_total,
            "sector_applicable_families": len(sector_applicable_families),
            "sector_not_applicable_families": len(sector_not_applicable_families),
            "mapping_percentages": mapping_percentages,
            "counts": counts,
            "percentages": percentages,
            "passes_all_fields": bool(core_total and portfolio_total)
            and all(value >= threshold for value in percentages.values())
            and all(value >= threshold for value in mapping_percentages.values()),
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only distinct-family staging coverage report.")
    parser.add_argument("--report-month", required=True, help="Exact month as YYYY-MM-01")
    parser.add_argument("--amcs", default=",".join(PRODUCTION_TARGET_AMC_KEYS))
    parser.add_argument("--threshold", type=float, default=80.0)
    args = parser.parse_args()
    if not supabase:
        print(json.dumps({"status": "error", "issues": ["supabase_not_configured"]}))
        return 1

    amcs = [value.strip().lower() for value in args.amcs.split(",") if value.strip()]
    candidates = _get_filtered(
        "mf_factsheet_candidates",
        "id,amc_code,report_month,raw_scheme_name,normalized_scheme_name,"
        "mapped_family_id,mapping_status,"
        "aum,expense_ratio,benchmark,fund_manager,risk_level",
        filters={"report_month": args.report_month},
    )
    raw_document_rows = _get_filtered(
        "mf_raw_documents",
        "id,amc_code",
        filters={"report_month": args.report_month},
    )
    raw_documents = {
        str(row["id"]): _normalize_amc_key(row.get("amc_code"))
        for row in raw_document_rows
        if row.get("id")
    }
    source_document_ids = sorted(raw_documents)
    holdings = _get_by_source_document_ids(
        "mf_scheme_holdings",
        "id,source_document_id,report_month,raw_scheme_name,"
        "mapped_family_id,mapping_status,sector",
        source_document_ids,
    )
    for row in holdings:
        row["amc_code"] = raw_documents.get(str(row.get("source_document_id") or ""), "")
    sector_allocations = _get_by_source_document_ids(
        "mf_scheme_sector_allocations",
        "id,source_document_id,report_month,raw_scheme_name,sector_name,"
        "mapped_family_id,mapping_status,validation_status",
        source_document_ids,
    )
    for row in sector_allocations:
        row["amc_code"] = raw_documents.get(str(row.get("source_document_id") or ""), "")

    report = build_staging_coverage(
        report_month=args.report_month,
        amcs=amcs,
        candidates=candidates,
        holdings=holdings,
        sector_allocations=sector_allocations,
        threshold=args.threshold,
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "report_month": args.report_month,
                "threshold_percent": args.threshold,
                "amcs": report,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
