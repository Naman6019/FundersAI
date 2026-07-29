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
from scripts.report_mf_staging_coverage import (
    _get_filtered,
    _normalize_amc_key,
    _ratio,
    _sector_not_applicable,
    failed_strict_amcs,
)

CORE_SCOPE_FIELDS = {
    "risk": ("risk_level",),
    "ter_aum": ("expense_ratio", "aum"),
    "benchmark": ("benchmark",),
    "manager": ("fund_manager",),
}


def _get_in_filtered(
    table: str,
    columns: str,
    *,
    column: str,
    values: list[object],
    filters: dict[str, object] | None = None,
    batch_size: int = 100,
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    unique_values = list(dict.fromkeys(values))
    for offset in range(0, len(unique_values), batch_size):
        query = supabase.table(table).select(columns).in_(
            column,
            unique_values[offset : offset + batch_size],
        )
        for filter_column, value in (filters or {}).items():
            query = query.eq(filter_column, value)
        start = 0
        while True:
            page = query.range(start, start + page_size - 1).execute().data or []
            rows.extend(page)
            if len(page) < page_size:
                break
            start += page_size
    return rows


def _promotion_month(row: dict[str, Any]) -> str:
    payload = row.get("provider_payload") or {}
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("report_month") or "")


def _compact_staging_rows(
    rows: list[dict[str, Any]],
    *,
    amc_by_document_id: dict[str, str],
    value_column: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[object, ...], dict[str, Any]] = {}
    identity_columns = (
        "source_document_id",
        "report_month",
        "raw_scheme_name",
        "mapped_scheme_code",
        "mapped_family_id",
        "mapping_status",
        "mapping_confidence",
        "validation_status",
    )
    for row in rows:
        source_document_id = str(row.get("source_document_id") or "")
        amc_code = amc_by_document_id.get(source_document_id)
        if not source_document_id or not amc_code:
            continue
        key = tuple(row.get(column) for column in identity_columns)
        current = grouped.setdefault(
            key,
            {
                **{column: row.get(column) for column in identity_columns},
                "amc_code": amc_code,
                value_column: None,
            },
        )
        if row.get(value_column) not in (None, ""):
            current[value_column] = "__present__"
    return list(grouped.values())


def _get_selected_staging_rows(
    *,
    report_month: str,
    amcs: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_amcs = {_normalize_amc_key(amc) for amc in amcs}
    raw_documents = _get_filtered(
        "mf_raw_documents",
        "id,amc_code,report_month",
        filters={"report_month": report_month},
    )
    amc_by_document_id = {
        str(row["id"]): str(row.get("amc_code") or "")
        for row in raw_documents
        if row.get("id")
        and _normalize_amc_key(row.get("amc_code")) in normalized_amcs
    }
    document_ids = list(amc_by_document_id)
    if not document_ids:
        return [], []

    holding_rows = _get_in_filtered(
        "mf_scheme_holdings",
        "source_document_id,report_month,raw_scheme_name,mapped_scheme_code,"
        "mapped_family_id,mapping_status,mapping_confidence,validation_status,sector",
        column="source_document_id",
        values=document_ids,
        filters={"report_month": report_month},
        batch_size=20,
    )
    sector_rows = _get_in_filtered(
        "mf_scheme_sector_allocations",
        "source_document_id,report_month,raw_scheme_name,mapped_scheme_code,"
        "mapped_family_id,mapping_status,mapping_confidence,validation_status,sector_name",
        column="source_document_id",
        values=document_ids,
        filters={"report_month": report_month},
        batch_size=20,
    )
    return (
        _compact_staging_rows(
            holding_rows,
            amc_by_document_id=amc_by_document_id,
            value_column="sector",
        ),
        _compact_staging_rows(
            sector_rows,
            amc_by_document_id=amc_by_document_id,
            value_column="sector_name",
        ),
    )


def build_runtime_coverage(
    *,
    report_month: str,
    amcs: list[str],
    candidates: list[dict[str, Any]],
    staged_holdings: list[dict[str, Any]],
    staged_sectors: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    runtime_holdings: list[dict[str, Any]],
    runtime_sectors: list[dict[str, Any]],
    threshold: float,
) -> dict[str, Any]:
    snapshots_by_code = {
        str(row.get("scheme_code")): row
        for row in snapshots
        if row.get("scheme_code") is not None
    }
    report: dict[str, Any] = {}
    for amc in amcs:
        normalized_amc = _normalize_amc_key(amc)
        current_candidates = [
            row
            for row in candidates
            if _normalize_amc_key(row.get("amc_code")) == normalized_amc
            and str(row.get("report_month") or "") == report_month
            and row.get("mapping_status") == "mapped"
            and row.get("mapped_scheme_code")
            and row.get("mapped_family_id")
            and float(row.get("mapping_confidence") or 0.0) >= 90.0
            and row.get("promotion_status") != "rejected"
        ]
        core_families = {
            str(row["mapped_family_id"]) for row in current_candidates
        }
        covered_core: dict[str, set[str]] = {
            scope: set() for scope in CORE_SCOPE_FIELDS
        }
        for candidate in current_candidates:
            snapshot = snapshots_by_code.get(str(candidate["mapped_scheme_code"]), {})
            promoted_scopes = set(candidate.get("promoted_scopes") or [])
            for scope, fields in CORE_SCOPE_FIELDS.items():
                if scope in promoted_scopes and all(
                    snapshot.get(field) not in (None, "") for field in fields
                ):
                    covered_core[scope].add(str(candidate["mapped_family_id"]))

        current_holdings = [
            row
            for row in staged_holdings
            if _normalize_amc_key(row.get("amc_code")) == normalized_amc
            and str(row.get("report_month") or "") == report_month
            and row.get("mapping_status") == "mapped"
            and row.get("mapped_scheme_code")
            and row.get("mapped_family_id")
            and float(row.get("mapping_confidence") or 0.0) >= 90.0
        ]
        holding_families = {
            str(row["mapped_family_id"]) for row in current_holdings
        }
        valid_sector_families = {
            str(row["mapped_family_id"])
            for row in current_holdings
            if row.get("validation_status") == "valid"
            and row.get("sector") not in (None, "")
        }
        direct_sector_families = {
            str(row["mapped_family_id"])
            for row in staged_sectors
            if _normalize_amc_key(row.get("amc_code")) == normalized_amc
            and str(row.get("report_month") or "") == report_month
            and row.get("mapping_status") == "mapped"
            and row.get("mapped_scheme_code")
            and row.get("mapped_family_id")
            and float(row.get("mapping_confidence") or 0.0) >= 90.0
            and row.get("validation_status") == "valid"
            and row.get("sector_name") not in (None, "")
        }
        valid_sector_families.update(direct_sector_families)
        holding_rows_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in current_holdings:
            holding_rows_by_family[str(row["mapped_family_id"])].append(row)
        sector_applicable_families = {
            family_id
            for family_id, rows in holding_rows_by_family.items()
            if family_id in valid_sector_families
            or any(
                not _sector_not_applicable(row.get("raw_scheme_name"))
                for row in rows
            )
        }
        sector_applicable_families.update(direct_sector_families)

        scheme_codes = {
            str(row["mapped_scheme_code"]) for row in current_holdings
        }
        live_holding_families = {
            str(row["family_id"])
            for row in runtime_holdings
            if str(row.get("scheme_code")) in scheme_codes
            and str(row.get("family_id") or "") in holding_families
            and str(row.get("as_of_date") or "") == report_month
            and row.get("source") == "amc_disclosure"
        }
        live_isin_families = {
            str(row["family_id"])
            for row in runtime_holdings
            if str(row.get("scheme_code")) in scheme_codes
            and str(row.get("family_id") or "") in holding_families
            and str(row.get("as_of_date") or "") == report_month
            and row.get("source") == "amc_disclosure"
            and row.get("isin") not in (None, "")
        }
        live_sector_families = {
            str(row["family_id"])
            for row in runtime_sectors
            if str(row.get("scheme_code")) in scheme_codes
            and str(row.get("family_id") or "") in sector_applicable_families
            and row.get("source") == "amc_disclosure"
            and _promotion_month(row) == report_month
        }

        counts = {
            **{
                scope: len(families)
                for scope, families in covered_core.items()
            },
            "holdings": len(live_holding_families),
            "holding_isin": len(live_isin_families),
            "sectors": len(live_sector_families),
        }
        percentages = {
            **{
                scope: _ratio(counts[scope], len(core_families))
                for scope in CORE_SCOPE_FIELDS
            },
            "holdings": _ratio(counts["holdings"], len(holding_families)),
            "holding_isin": _ratio(
                counts["holding_isin"],
                len(live_holding_families),
            ),
            "sectors": (
                _ratio(counts["sectors"], len(sector_applicable_families))
                if sector_applicable_families
                else (100.0 if holding_families else 0.0)
            ),
        }
        report[normalized_amc] = {
            "core_families": len(core_families),
            "holding_families": len(holding_families),
            "sector_applicable_families": len(sector_applicable_families),
            "counts": counts,
            "percentages": percentages,
            "passes_all_fields": bool(core_families and holding_families)
            and all(value >= threshold for value in percentages.values()),
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only runtime coverage report for promoted AMC disclosures."
    )
    parser.add_argument("--report-month", required=True, help="Exact month as YYYY-MM-01")
    parser.add_argument("--amcs", default=",".join(PRODUCTION_TARGET_AMC_KEYS))
    parser.add_argument("--strict-amcs", default="")
    parser.add_argument("--threshold", type=float, default=80.0)
    args = parser.parse_args()
    if not supabase:
        print(json.dumps({"status": "error", "issues": ["supabase_not_configured"]}))
        return 1

    amcs = [value.strip().lower() for value in args.amcs.split(",") if value.strip()]
    strict_amcs = [
        value.strip().lower()
        for value in args.strict_amcs.split(",")
        if value.strip()
    ]
    candidates = _get_filtered(
        "mf_factsheet_candidates",
        "id,amc_code,report_month,mapped_scheme_code,mapped_family_id,"
        "mapping_status,mapping_confidence,promotion_status,promoted_scopes,promoted_at",
        filters={"report_month": args.report_month},
    )
    staged_holdings, staged_sectors = _get_selected_staging_rows(
        report_month=args.report_month,
        amcs=amcs,
    )
    scheme_codes = sorted(
        {
            str(row["mapped_scheme_code"])
            for row in [*candidates, *staged_holdings, *staged_sectors]
            if row.get("mapped_scheme_code")
        }
    )
    numeric_scheme_codes = [
        int(value) for value in scheme_codes if value.isdigit()
    ]
    snapshots = _get_in_filtered(
        "mutual_fund_core_snapshot",
        "scheme_code,risk_level,expense_ratio,aum,benchmark,fund_manager",
        column="scheme_code",
        values=scheme_codes,
    )
    runtime_holdings = _get_in_filtered(
        "mutual_fund_holdings",
        "scheme_code,family_id,as_of_date,security_name,isin,source,provider_payload",
        column="scheme_code",
        values=numeric_scheme_codes,
        filters={"source": "amc_disclosure", "as_of_date": args.report_month},
    )
    runtime_sectors = _get_in_filtered(
        "mutual_fund_sectors",
        "scheme_code,family_id,source,provider_payload",
        column="scheme_code",
        values=scheme_codes,
        filters={"source": "amc_disclosure"},
    )
    report = build_runtime_coverage(
        report_month=args.report_month,
        amcs=amcs,
        candidates=candidates,
        staged_holdings=staged_holdings,
        staged_sectors=staged_sectors,
        snapshots=snapshots,
        runtime_holdings=runtime_holdings,
        runtime_sectors=runtime_sectors,
        threshold=args.threshold,
    )
    failed_amcs = failed_strict_amcs(report, strict_amcs)
    print(
        json.dumps(
            {
                "status": "ok",
                "report_month": args.report_month,
                "threshold_percent": args.threshold,
                "strict_amcs": strict_amcs,
                "failed_strict_amcs": failed_amcs,
                "amcs": report,
            },
            indent=2,
        )
    )
    return 1 if failed_amcs else 0


if __name__ == "__main__":
    raise SystemExit(main())
