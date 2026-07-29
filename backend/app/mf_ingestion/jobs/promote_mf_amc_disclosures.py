from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date
from typing import Any

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.jobs.promote_mf_disclosures import (
    CORE_SCOPES,
    MIN_PORTFOLIO_FAMILY_COVERAGE,
    PORTFOLIO_SCOPES,
    _fetch_all_rows,
    _parse_report_month,
    _parse_scopes,
    apply_promotable_report,
    build_dry_run,
)
from app.mf_ingestion.sources.registry import PRODUCTION_TARGET_AMC_KEYS, get_source

AMC_ALIASES = {"absl": "aditya_birla"}
DEFAULT_MAX_SOURCE_DOCUMENTS = 150
SAFE_PORTFOLIO_QUARANTINE_ISSUES = frozenset(
    {
        "staged_holdings_below_family_coverage_threshold",
        "staged_holdings_have_no_promotable_rows",
        "staged_sectors_below_family_coverage_threshold",
        "staged_sectors_have_no_promotable_rows",
    }
)


def _normalize_amc(value: object) -> str:
    key = str(value or "").strip().lower()
    return AMC_ALIASES.get(key, key)


def _build_target_scopes(
    *,
    amc: str,
    requested_scopes: list[str],
    candidates: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
    sector_allocations: list[dict[str, Any]],
) -> dict[str, list[str]]:
    normalized_amc = _normalize_amc(amc)
    targets: dict[str, set[str]] = defaultdict(set)

    requested_core = CORE_SCOPES.intersection(requested_scopes)
    if requested_core:
        for row in candidates:
            if _normalize_amc(row.get("amc_code")) == normalized_amc and row.get(
                "source_document_id"
            ):
                targets[str(row["source_document_id"])].update(requested_core)

    if "holdings" in requested_scopes:
        for row in holdings:
            if _normalize_amc(row.get("amc_code")) == normalized_amc and row.get(
                "source_document_id"
            ):
                targets[str(row["source_document_id"])].add("holdings")

    if "sectors" in requested_scopes:
        current_direct_sectors = [
            row
            for row in sector_allocations
            if _normalize_amc(row.get("amc_code")) == normalized_amc
            and row.get("source_document_id")
            and row.get("sector_name") not in (None, "")
        ]
        # Official aggregate sector allocations supersede holdings-derived
        # fallback sectors for an AMC/report month.
        if not current_direct_sectors:
            for row in holdings:
                if (
                    _normalize_amc(row.get("amc_code")) == normalized_amc
                    and row.get("source_document_id")
                    and row.get("sector") not in (None, "")
                ):
                    targets[str(row["source_document_id"])].add("sectors")
        for row in current_direct_sectors:
            targets[str(row["source_document_id"])].add("sectors")

    requested_order = {scope: index for index, scope in enumerate(requested_scopes)}
    return {
        source_document_id: sorted(scopes, key=requested_order.__getitem__)
        for source_document_id, scopes in sorted(targets.items())
    }


def _source_recency_key(document: dict[str, Any]) -> tuple[str, str]:
    return (
        str(document.get("parsed_at") or document.get("downloaded_at") or ""),
        str(document.get("id") or ""),
    )


def _preferred_document_type(scope: str) -> str:
    return "factsheet" if scope in CORE_SCOPES else "portfolio_disclosure"


def _is_tabular_portfolio_document(document: dict[str, Any]) -> bool:
    source_path = str(document.get("source_url") or "").split("?", 1)[0].lower()
    return source_path.endswith((".csv", ".xls", ".xlsx", ".zip"))


def _dedupe_target_scopes(
    targets: dict[str, list[str]],
    documents: list[dict[str, Any]],
    requested_scopes: list[str],
) -> dict[str, list[str]]:
    metadata = {str(row.get("id")): row for row in documents if row.get("id")}
    selected: dict[str, set[str]] = defaultdict(set)

    for scope in requested_scopes:
        source_ids = [
            source_document_id
            for source_document_id, scopes in targets.items()
            if scope in scopes
        ]
        preferred_type = _preferred_document_type(scope)
        preferred_source_ids = [
            source_document_id
            for source_document_id in source_ids
            if str(
                metadata.get(source_document_id, {}).get("document_type") or ""
            ).strip().lower()
            == preferred_type
        ]
        # Do not let holdings parsed from a combined factsheet overwrite a
        # dedicated official portfolio disclosure for the same month.
        if preferred_source_ids:
            source_ids = preferred_source_ids
        if scope in PORTFOLIO_SCOPES:
            tabular_source_ids = [
                source_document_id
                for source_document_id in source_ids
                if _is_tabular_portfolio_document(
                    metadata.get(source_document_id, {})
                )
            ]
            # A dedicated workbook is stronger portfolio evidence than a
            # combined factsheet PDF, even when discovery stored both under
            # the portfolio-disclosure role.
            if tabular_source_ids:
                source_ids = tabular_source_ids

        checksum_groups: dict[str, list[str]] = defaultdict(list)
        for source_document_id in source_ids:
            document = metadata.get(source_document_id, {})
            checksum = str(document.get("checksum") or "").strip()
            checksum_groups[checksum or f"missing:{source_document_id}"].append(
                source_document_id
            )

        checksum_winners: list[str] = []
        for group in checksum_groups.values():
            checksum_winners.append(
                max(
                    group,
                    key=lambda source_document_id: (
                        str(
                            metadata.get(source_document_id, {}).get("document_type")
                            or ""
                        )
                        == preferred_type,
                        _source_recency_key(metadata.get(source_document_id, {})),
                    ),
                )
            )

        url_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for source_document_id in checksum_winners:
            document = metadata.get(source_document_id, {})
            document_type = str(document.get("document_type") or "").strip().lower()
            source_url = str(document.get("source_url") or "").strip()
            key = (
                document_type,
                source_url or f"missing:{source_document_id}",
            )
            url_groups[key].append(source_document_id)

        for group in url_groups.values():
            winner = max(
                group,
                key=lambda source_document_id: _source_recency_key(
                    metadata.get(source_document_id, {})
                ),
            )
            selected[winner].add(scope)

    requested_order = {scope: index for index, scope in enumerate(requested_scopes)}
    return {
        source_document_id: sorted(scopes, key=requested_order.__getitem__)
        for source_document_id, scopes in sorted(selected.items())
    }


def _split_scope_groups(scopes: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    core_scopes = [scope for scope in scopes if scope in CORE_SCOPES]
    if core_scopes:
        groups.append(core_scopes)
    if "holdings" in scopes:
        groups.append(["holdings"])
    if "sectors" in scopes:
        groups.append(["sectors"])
    return groups


def _percentage(count: int, total: int) -> float:
    return round((count / total) * 100.0, 2) if total else 0.0


def _core_batch_coverage(
    target_reports: list[dict[str, Any]],
    scopes: list[str],
) -> dict[str, Any]:
    core_reports = [
        row for row in target_reports if CORE_SCOPES.intersection(row["scopes"])
    ]
    observed: set[str] = set()
    mapped: set[str] = set()
    promotable_by_scope: dict[str, set[str]] = {
        scope: set() for scope in scopes if scope in CORE_SCOPES
    }
    for row in core_reports:
        for candidate in row["report"].get("candidate_reports", []):
            family_id = str(candidate.get("mapped_family_id") or "").strip()
            raw_name = str(candidate.get("raw_scheme_name") or "").strip().lower()
            observed.add(f"family:{family_id}" if family_id else f"raw:{raw_name}")
            if family_id and not candidate.get("issues"):
                mapped.add(family_id)
            if row["status"] != "promotable" or candidate.get("issues"):
                continue
            for scope in candidate.get("eligible_scopes", []):
                if scope in promotable_by_scope and family_id:
                    promotable_by_scope[scope].add(family_id)

    return {
        "observed_families": len(observed),
        "mapped_families": len(mapped),
        "mapping_percentage": _percentage(len(mapped), len(observed)),
        "field_percentages": {
            scope: _percentage(len(families), len(mapped))
            for scope, families in promotable_by_scope.items()
        },
    }


def _portfolio_batch_coverage(
    target_reports: list[dict[str, Any]],
    scope: str,
) -> dict[str, Any]:
    coverage_key = (
        "holdings_family_coverage"
        if scope == "holdings"
        else "sector_family_coverage"
    )
    scope_reports = [row for row in target_reports if scope in row["scopes"]]
    observed: set[str] = set()
    applicable: set[str] = set()
    promotable: set[str] = set()
    isin_ready: set[str] = set()
    for row in scope_reports:
        coverage = row["report"].get(coverage_key) or {}
        observed.update(str(value) for value in coverage.get("observed_keys", []))
        applicable.update(
            str(value) for value in coverage.get("applicable_family_ids", [])
        )
        if row["status"] == "promotable":
            promotable.update(
                str(value) for value in coverage.get("promotable_family_ids", [])
            )
            if scope == "holdings":
                isin_ready.update(
                    str(value) for value in coverage.get("isin_family_ids", [])
                )

    denominator = applicable if scope == "sectors" and applicable else observed
    return {
        "target_count": len(scope_reports),
        "promotable_target_count": sum(
            row["status"] == "promotable" for row in scope_reports
        ),
        "quarantined_target_count": sum(
            row["status"] != "promotable" for row in scope_reports
        ),
        "observed_families": len(observed),
        "applicable_families": len(applicable),
        "promotable_families": len(promotable),
        "isin_ready_families": len(isin_ready),
        "post_apply_family_coverage_percentage": _percentage(
            len(promotable),
            len(denominator),
        ),
        "post_apply_isin_family_coverage_percentage": (
            _percentage(len(isin_ready), len(promotable))
            if scope == "holdings"
            else None
        ),
    }


def _is_safe_portfolio_quarantine(target_report: dict[str, Any]) -> bool:
    issues = set(target_report.get("issues") or [])
    scopes = set(target_report.get("scopes") or [])
    return bool(issues) and scopes.issubset(PORTFOLIO_SCOPES) and issues.issubset(
        SAFE_PORTFOLIO_QUARANTINE_ISSUES
    )


def assess_batch_targets(
    target_reports: list[dict[str, Any]],
    scopes: list[str],
) -> dict[str, Any]:
    rejected = [row for row in target_reports if row["status"] != "promotable"]
    unsafe_rejected = [
        row for row in rejected if not _is_safe_portfolio_quarantine(row)
    ]
    coverage: dict[str, Any] = {}
    issues: list[str] = []

    requested_core = [scope for scope in scopes if scope in CORE_SCOPES]
    if requested_core:
        core_coverage = _core_batch_coverage(target_reports, requested_core)
        coverage["core"] = core_coverage
        if (
            core_coverage["mapping_percentage"]
            < MIN_PORTFOLIO_FAMILY_COVERAGE
        ):
            issues.append("core_batch_mapping_coverage_below_80")
        for scope, percentage in core_coverage["field_percentages"].items():
            if percentage < MIN_PORTFOLIO_FAMILY_COVERAGE:
                issues.append(f"{scope}_batch_family_coverage_below_80")

    for scope in ("holdings", "sectors"):
        if scope not in scopes:
            continue
        scope_coverage = _portfolio_batch_coverage(target_reports, scope)
        coverage[scope] = scope_coverage
        if (
            not scope_coverage["target_count"]
            or scope_coverage["post_apply_family_coverage_percentage"]
            < MIN_PORTFOLIO_FAMILY_COVERAGE
        ):
            issues.append(f"{scope}_batch_family_coverage_below_80")
        if (
            scope == "holdings"
            and scope_coverage["post_apply_isin_family_coverage_percentage"]
            < MIN_PORTFOLIO_FAMILY_COVERAGE
        ):
            issues.append("holding_isin_batch_family_coverage_below_80")

    if unsafe_rejected:
        issues.append("one_or_more_unsafe_promotion_targets_rejected")

    return {
        "status": "promotable" if not issues else "rejected",
        "coverage": coverage,
        "issues": sorted(set(issues)),
        "rejected_target_count": len(rejected),
        "quarantined_target_count": len(rejected) - len(unsafe_rejected),
        "unsafe_rejected_target_count": len(unsafe_rejected),
        "warnings": (
            [f"{len(rejected)}_non_promotable_targets_quarantined"]
            if rejected and not unsafe_rejected and not issues
            else []
        ),
    }


def _fetch_rows_by_document_ids(
    table: str,
    columns: str,
    *,
    source_document_ids: list[str],
    report_month: date,
    batch_size: int = 20,
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for offset in range(0, len(source_document_ids), batch_size):
        query = (
            supabase.table(table)
            .select(columns)
            .in_(
                "source_document_id",
                source_document_ids[offset : offset + batch_size],
            )
            .eq("report_month", report_month.isoformat())
        )
        start = 0
        while True:
            page = query.range(start, start + page_size - 1).execute().data or []
            rows.extend(page)
            if len(page) < page_size:
                break
            start += page_size
    return rows


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


def _get_selected_amc_staging_rows(
    *,
    amc: str,
    report_month: date,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_documents = _fetch_all_rows(
        "mf_raw_documents",
        "id,amc_code",
        filters={"report_month": report_month.isoformat()},
    )
    normalized_amc = _normalize_amc(amc)
    amc_by_document_id = {
        str(row["id"]): str(row.get("amc_code") or "")
        for row in raw_documents
        if row.get("id") and _normalize_amc(row.get("amc_code")) == normalized_amc
    }
    source_document_ids = list(amc_by_document_id)
    if not source_document_ids:
        return [], [], []

    candidates = _fetch_rows_by_document_ids(
        "mf_factsheet_candidates",
        "id,source_document_id,amc_code,report_month",
        source_document_ids=source_document_ids,
        report_month=report_month,
    )
    holdings = _fetch_rows_by_document_ids(
        "mf_scheme_holdings",
        "source_document_id,report_month,raw_scheme_name,mapped_scheme_code,"
        "mapped_family_id,mapping_status,mapping_confidence,validation_status,sector",
        source_document_ids=source_document_ids,
        report_month=report_month,
    )
    sector_allocations = _fetch_rows_by_document_ids(
        "mf_scheme_sector_allocations",
        "source_document_id,report_month,raw_scheme_name,mapped_scheme_code,"
        "mapped_family_id,mapping_status,mapping_confidence,validation_status,"
        "sector_name",
        source_document_ids=source_document_ids,
        report_month=report_month,
    )
    return (
        candidates,
        _compact_staging_rows(
            holdings,
            amc_by_document_id=amc_by_document_id,
            value_column="sector",
        ),
        _compact_staging_rows(
            sector_allocations,
            amc_by_document_id=amc_by_document_id,
            value_column="sector_name",
        ),
    )


def collect_promotion_targets(
    *,
    amc: str,
    requested_scopes: list[str],
    report_month: date,
) -> dict[str, list[str]]:
    candidates, holdings, sector_allocations = _get_selected_amc_staging_rows(
        amc=amc,
        report_month=report_month,
    )
    targets = _build_target_scopes(
        amc=amc,
        requested_scopes=requested_scopes,
        candidates=candidates,
        holdings=holdings,
        sector_allocations=sector_allocations,
    )
    if not targets:
        return {}
    documents = (
        supabase.table("mf_raw_documents")
        .select("id,document_type,checksum,source_url,downloaded_at,parsed_at")
        .in_("id", list(targets))
        .execute()
        .data
        or []
    )
    return _dedupe_target_scopes(targets, documents, requested_scopes)


def build_amc_dry_run(
    *,
    amc: str,
    scopes: list[str],
    expected_report_month: date,
    max_source_documents: int,
) -> dict[str, Any]:
    source = get_source(amc)
    if not source.promotion_enabled:
        return {"status": "rejected", "amc": amc, "issues": ["promotion_disabled"]}

    targets = collect_promotion_targets(
        amc=amc,
        requested_scopes=scopes,
        report_month=expected_report_month,
    )
    if not targets:
        return {"status": "rejected", "amc": amc, "issues": ["promotion_targets_missing"]}
    if len(targets) > max_source_documents:
        return {
            "status": "rejected",
            "amc": amc,
            "source_document_count": len(targets),
            "max_source_documents": max_source_documents,
            "issues": ["promotion_target_limit_exceeded"],
        }

    target_reports: list[dict[str, Any]] = []
    for source_document_id, target_scopes in targets.items():
        for scope_group in _split_scope_groups(target_scopes):
            report = build_dry_run(
                source_document_id,
                scope_group,
                expected_report_month,
            )
            target_reports.append(
                {
                    "source_document_id": source_document_id,
                    "scopes": scope_group,
                    "status": report.get("status"),
                    "issues": report.get("issues", []),
                    "warnings": report.get("warnings", []),
                    "report": report,
                }
            )

    batch_gate = assess_batch_targets(target_reports, scopes)
    return {
        "status": batch_gate["status"],
        "amc": amc,
        "expected_report_month": expected_report_month.isoformat(),
        "requested_scopes": scopes,
        "source_document_count": len(targets),
        "target_count": len(target_reports),
        "promotable_target_count": sum(
            row["status"] == "promotable" for row in target_reports
        ),
        "rejected_target_count": batch_gate["rejected_target_count"],
        "quarantined_target_count": batch_gate["quarantined_target_count"],
        "unsafe_rejected_target_count": batch_gate[
            "unsafe_rejected_target_count"
        ],
        "batch_coverage": batch_gate["coverage"],
        "target_reports": target_reports,
        "warnings": batch_gate["warnings"],
        "issues": batch_gate["issues"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bounded dry-run or apply promotion for one AMC and report month."
    )
    parser.add_argument("--amc", required=True, choices=sorted(PRODUCTION_TARGET_AMC_KEYS))
    parser.add_argument("--scopes", required=True)
    parser.add_argument("--expected-report-month", required=True)
    parser.add_argument("--max-source-documents", type=int, default=DEFAULT_MAX_SOURCE_DOCUMENTS)
    parser.add_argument("--requested-by", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not supabase:
        print(json.dumps({"status": "error", "issues": ["supabase_not_configured"]}))
        return 2
    if not 1 <= args.max_source_documents <= DEFAULT_MAX_SOURCE_DOCUMENTS:
        print(json.dumps({"status": "error", "issues": ["max_source_documents_invalid"]}))
        return 2
    try:
        scopes = _parse_scopes(args.scopes)
        expected_report_month = _parse_report_month(args.expected_report_month)
    except ValueError as exc:
        print(json.dumps({"status": "error", "issues": [str(exc)]}))
        return 2

    report = build_amc_dry_run(
        amc=args.amc,
        scopes=scopes,
        expected_report_month=expected_report_month,
        max_source_documents=args.max_source_documents,
    )
    if report["status"] != "promotable":
        print(json.dumps(report, indent=2, default=str))
        return 1
    if not args.apply:
        report["status"] = "dry_run"
        print(json.dumps(report, indent=2, default=str))
        return 0

    # Revalidate every target immediately before the first mutation.
    revalidated = build_amc_dry_run(
        amc=args.amc,
        scopes=scopes,
        expected_report_month=expected_report_month,
        max_source_documents=args.max_source_documents,
    )
    if revalidated["status"] != "promotable":
        print(json.dumps(revalidated, indent=2, default=str))
        return 1

    applied: list[dict[str, Any]] = []
    for target_report in revalidated["target_reports"]:
        if target_report["status"] != "promotable":
            continue
        operations = apply_promotable_report(
            target_report["report"],
            target_report["scopes"],
            expected_report_month,
            requested_by=args.requested_by,
        )
        applied.append(
            {
                "source_document_id": target_report["source_document_id"],
                "scopes": target_report["scopes"],
                "operations": operations,
            }
        )
    print(
        json.dumps(
            {
                "status": "applied",
                "amc": args.amc,
                "expected_report_month": expected_report_month.isoformat(),
                "source_document_count": revalidated["source_document_count"],
                "target_count": len(applied),
                "quarantined_target_count": revalidated[
                    "quarantined_target_count"
                ],
                "targets": applied,
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
