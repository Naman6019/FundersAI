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
    _fetch_all_rows,
    _fetch_all_rpc_rows,
    _parse_report_month,
    _parse_scopes,
    apply_promotable_report,
    build_dry_run,
)
from app.mf_ingestion.sources.registry import PRODUCTION_TARGET_AMC_KEYS, get_source

AMC_ALIASES = {"absl": "aditya_birla"}
DEFAULT_MAX_SOURCE_DOCUMENTS = 150


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

        checksum_groups: dict[str, list[str]] = defaultdict(list)
        for source_document_id in source_ids:
            document = metadata.get(source_document_id, {})
            checksum = str(document.get("checksum") or "").strip()
            checksum_groups[checksum or f"missing:{source_document_id}"].append(
                source_document_id
            )

        checksum_winners: list[str] = []
        preferred_type = _preferred_document_type(scope)
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


def _compact_rows(function_name: str, report_month: date) -> list[dict[str, Any]]:
    return _fetch_all_rpc_rows(
        function_name,
        {"p_report_month": report_month.isoformat()},
    )


def collect_promotion_targets(
    *,
    amc: str,
    requested_scopes: list[str],
    report_month: date,
) -> dict[str, list[str]]:
    candidates = _fetch_all_rows(
        "mf_factsheet_candidates",
        "id,source_document_id,amc_code,report_month",
        filters={"report_month": report_month.isoformat()},
    )
    holdings = _compact_rows("mf_staging_holding_coverage_rows", report_month)
    sector_allocations = _compact_rows("mf_staging_sector_coverage_rows", report_month)
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

    rejected = [row for row in target_reports if row["status"] != "promotable"]
    return {
        "status": "promotable" if not rejected else "rejected",
        "amc": amc,
        "expected_report_month": expected_report_month.isoformat(),
        "requested_scopes": scopes,
        "source_document_count": len(targets),
        "target_count": len(target_reports),
        "rejected_target_count": len(rejected),
        "target_reports": target_reports,
        "issues": [] if not rejected else ["one_or_more_promotion_targets_rejected"],
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
                "targets": applied,
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
