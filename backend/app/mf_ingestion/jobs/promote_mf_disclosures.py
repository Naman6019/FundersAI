from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import date
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.sources.registry import get_source_by_code

CORE_SCOPES = {"risk", "ter_aum", "benchmark", "manager"}
PORTFOLIO_SCOPES = {"holdings", "sectors"}
ALLOWED_SCOPES = CORE_SCOPES | PORTFOLIO_SCOPES
PAGE_SIZE = 1000


def _parse_scopes(value: str) -> list[str]:
    scopes = list(dict.fromkeys(part.strip().lower() for part in value.split(",") if part.strip()))
    invalid = sorted(set(scopes) - ALLOWED_SCOPES)
    if invalid:
        raise ValueError(f"invalid_scopes:{','.join(invalid)}")
    if not scopes:
        raise ValueError("promotion_scope_required")
    return scopes


def _parse_report_month(value: str) -> date:
    raw = value.strip()
    if len(raw) == 7:
        raw = f"{raw}-01"
    parsed = date.fromisoformat(raw)
    return parsed.replace(day=1)


def _fetch_all_rows(
    table: str,
    columns: str,
    *,
    filters: dict[str, Any],
    page_size: int = PAGE_SIZE,
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


def _available_core_scopes(candidate: dict[str, Any], requested_scopes: list[str]) -> list[str]:
    available: list[str] = []
    for scope in requested_scopes:
        if scope == "risk" and candidate.get("risk_level") not in (None, ""):
            available.append(scope)
        elif scope == "ter_aum" and all(
            candidate.get(field) not in (None, "") for field in ("expense_ratio", "aum")
        ):
            available.append(scope)
        elif scope == "benchmark" and candidate.get("benchmark") not in (None, ""):
            available.append(scope)
        elif scope == "manager" and candidate.get("fund_manager") not in (None, ""):
            available.append(scope)
    return available


def _validate_source_document(document: dict[str, Any], expected_report_month: date) -> list[str]:
    issues: list[str] = []
    if str(document.get("report_month") or "") != expected_report_month.isoformat():
        issues.append("source_report_month_mismatch")
    if document.get("parse_status") not in {"parsed", "parsed_partial"}:
        issues.append("source_not_parsed")
    if str(document.get("storage_backend") or "").lower() != "r2":
        issues.append("source_not_r2_backed")
    if not document.get("checksum") or not document.get("storage_key"):
        issues.append("r2_evidence_missing")
    return issues


def _validate_candidate(
    candidate: dict[str, Any],
    mapping_by_code: dict[str, str],
    document: dict[str, Any],
    expected_report_month: date,
) -> list[str]:
    issues: list[str] = []
    scheme_code = str(candidate.get("mapped_scheme_code") or "")
    family_id = str(candidate.get("mapped_family_id") or "")
    if candidate.get("mapping_status") != "mapped":
        issues.append("mapping_not_reviewed")
    if not scheme_code or not family_id:
        issues.append("mapped_code_or_family_missing")
    if float(candidate.get("mapping_confidence") or 0.0) < 90.0:
        issues.append("mapping_confidence_below_90")
    if mapping_by_code.get(scheme_code) != family_id:
        issues.append("mapping_changed")
    if not candidate.get("report_month"):
        issues.append("report_month_missing")
    elif str(candidate.get("report_month")) != expected_report_month.isoformat():
        issues.append("candidate_report_month_mismatch")
    if str(candidate.get("amc_code") or "").lower() != str(document.get("amc_code") or "").lower():
        issues.append("candidate_amc_mismatch")
    if candidate.get("checksum") != document.get("checksum"):
        issues.append("candidate_checksum_mismatch")
    if candidate.get("storage_key") != document.get("storage_key"):
        issues.append("candidate_storage_key_mismatch")
    if candidate.get("promotion_status") == "rejected":
        issues.append("candidate_rejected")
    return sorted(set(issues))


def _validate_holding(
    row: dict[str, Any],
    mapping_by_code: dict[str, str],
    document: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    if row.get("validation_status") != "valid":
        issues.append("holdings_validation_not_valid")
    if row.get("mapping_status") != "mapped":
        issues.append("holdings_mapping_not_reviewed")
    if float(row.get("mapping_confidence") or 0.0) < 90.0:
        issues.append("holdings_mapping_confidence_below_90")
    code = str(row.get("mapped_scheme_code") or "")
    family = str(row.get("mapped_family_id") or "")
    if mapping_by_code.get(code) != family:
        issues.append("holdings_mapping_changed")
    if str(row.get("report_month") or "") != str(document.get("report_month") or ""):
        issues.append("holdings_report_month_mismatch")
    return sorted(set(issues))


def build_dry_run(
    source_document_id: str,
    scopes: list[str],
    expected_report_month: date,
) -> dict[str, Any]:
    document_result = (
        supabase.table("mf_raw_documents")
        .select("id,amc_code,report_month,parse_status,checksum,storage_backend,storage_key")
        .eq("id", source_document_id)
        .limit(1)
        .execute()
    )
    if not document_result.data:
        return {"status": "rejected", "issues": ["source_document_not_found"]}
    document = document_result.data[0]
    try:
        source = get_source_by_code(str(document.get("amc_code") or ""))
    except ValueError:
        return {"status": "rejected", "issues": ["unknown_amc"]}
    if not source.promotion_enabled:
        return {"status": "rejected", "issues": ["promotion_disabled"]}

    candidates = _fetch_all_rows(
        "mf_factsheet_candidates",
        "*",
        filters={"source_document_id": source_document_id},
    )
    holdings = _fetch_all_rows(
        "mf_scheme_holdings",
        "id,mapped_scheme_code,mapped_family_id,mapping_status,mapping_confidence,"
        "report_month,raw_scheme_name,validation_status",
        filters={"source_document_id": source_document_id},
    )
    codes = sorted(
        {
            str(row.get("mapped_scheme_code"))
            for row in [*candidates, *holdings]
            if row.get("mapped_scheme_code")
        }
    )
    mapping_by_code: dict[str, str] = {}
    if codes:
        mapping_result = (
            supabase.table("mutual_fund_family_mapping")
            .select("scheme_code,family_id")
            .in_("scheme_code", codes)
            .execute()
        )
        mapping_by_code = {
            str(row["scheme_code"]): str(row["family_id"])
            for row in (mapping_result.data or [])
            if row.get("scheme_code") and row.get("family_id")
        }

    issues = _validate_source_document(document, expected_report_month)
    warnings: list[str] = []
    candidate_reports = []
    operation_count = 0
    valid_holdings_rows = 0
    rejected_holdings_rows = 0
    holdings_rejection_reasons: Counter[str] = Counter()
    if CORE_SCOPES.intersection(scopes):
        if not candidates:
            issues.append("factsheet_candidates_missing")
        for candidate in candidates:
            candidate_issues = _validate_candidate(
                candidate,
                mapping_by_code,
                document,
                expected_report_month,
            )
            eligible_scopes = (
                _available_core_scopes(candidate, scopes)
                if not candidate_issues
                else []
            )
            unavailable_scopes = sorted(CORE_SCOPES.intersection(scopes) - set(eligible_scopes))
            candidate_reports.append(
                {
                    "candidate_id": candidate.get("id"),
                    "raw_scheme_name": candidate.get("raw_scheme_name"),
                    "mapped_scheme_code": candidate.get("mapped_scheme_code"),
                    "mapped_family_id": candidate.get("mapped_family_id"),
                    "eligible_scopes": eligible_scopes,
                    "unavailable_scopes": unavailable_scopes,
                    "issues": candidate_issues,
                }
            )
            operation_count += int(bool(eligible_scopes))
            warnings.extend(candidate_issues)
            warnings.extend(f"{candidate.get('id')}:{scope}_unavailable" for scope in unavailable_scopes)

    if PORTFOLIO_SCOPES.intersection(scopes):
        if not holdings:
            issues.append("staged_holdings_missing")
        for row in holdings:
            row_issues = _validate_holding(row, mapping_by_code, document)
            if row_issues:
                warnings.extend(row_issues)
                rejected_holdings_rows += 1
                holdings_rejection_reasons.update(set(row_issues))
            else:
                valid_holdings_rows += 1
        if valid_holdings_rows:
            operation_count += 1
        elif holdings:
            issues.append("staged_holdings_have_no_promotable_rows")
        if rejected_holdings_rows:
            issues.append("staged_holdings_contain_non_promotable_rows")

    if operation_count == 0 and not issues:
        issues.append("no_promotable_operations")

    return {
        "status": "promotable" if not issues else "rejected",
        "source_document": document,
        "expected_report_month": expected_report_month.isoformat(),
        "scopes": scopes,
        "candidate_reports": candidate_reports,
        "staged_holdings_rows": len(holdings),
        "promotable_holdings_rows": valid_holdings_rows,
        "rejected_holdings_rows": rejected_holdings_rows,
        "holdings_rejection_reasons": dict(sorted(holdings_rejection_reasons.items())),
        "warnings": sorted(set(warnings)),
        "issues": sorted(set(issues)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run or apply reviewed MF disclosure promotion.")
    parser.add_argument("--source-document-id", required=True)
    parser.add_argument("--scopes", required=True, help="risk,ter_aum,benchmark,manager,holdings,sectors")
    parser.add_argument("--expected-report-month", required=True, help="Exact reviewed month in YYYY-MM form")
    parser.add_argument("--requested-by", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not supabase:
        print(json.dumps({"status": "error", "issues": ["supabase_not_configured"]}))
        return 2
    try:
        scopes = _parse_scopes(args.scopes)
        expected_report_month = _parse_report_month(args.expected_report_month)
    except ValueError as exc:
        print(json.dumps({"status": "error", "issues": [str(exc)]}))
        return 2

    report = build_dry_run(args.source_document_id, scopes, expected_report_month)
    if report["status"] != "promotable":
        print(json.dumps(report, indent=2, default=str))
        return 1
    if not args.apply:
        report["status"] = "dry_run"
        print(json.dumps(report, indent=2, default=str))
        return 0

    applied: list[dict[str, Any]] = []
    core_scopes = [scope for scope in scopes if scope in CORE_SCOPES]
    if core_scopes:
        for candidate in report["candidate_reports"]:
            candidate_scopes = candidate["eligible_scopes"]
            if not candidate_scopes or candidate["issues"]:
                continue
            result = supabase.rpc(
                "promote_mf_factsheet_candidate",
                {
                    "p_candidate_id": candidate["candidate_id"],
                    "p_scopes": candidate_scopes,
                    "p_requested_by": args.requested_by,
                    "p_expected_report_month": expected_report_month.isoformat(),
                },
            ).execute()
            applied.append({"candidate_id": candidate["candidate_id"], "result": result.data})

    portfolio_scopes = [scope for scope in scopes if scope in PORTFOLIO_SCOPES]
    if portfolio_scopes:
        result = supabase.rpc(
            "promote_mf_holdings_document",
            {
                "p_source_document_id": args.source_document_id,
                "p_scopes": portfolio_scopes,
                "p_requested_by": args.requested_by,
                "p_expected_report_month": expected_report_month.isoformat(),
            },
        ).execute()
        applied.append({"source_document_id": args.source_document_id, "result": result.data})

    print(json.dumps({"status": "applied", "operations": applied}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
