from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.database import supabase
from app.services.supported_amcs import SUPPORTED_MF_AMC_MARKERS


AMC_LABELS = {label.lower(): markers for label, markers in SUPPORTED_MF_AMC_MARKERS.items()}
DEFAULT_AMCS = "axis,hdfc,sbi,icici,ppfas,nippon"


def _get_all(table: str, columns: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    limit = 1000
    while True:
        page = supabase.table(table).select(columns).range(offset, offset + limit - 1).execute().data or []
        if not page:
            return rows
        rows.extend(page)
        offset += limit


def _parse_amc_list(raw: str | None) -> list[str]:
    return [token.strip().lower() for token in str(raw or DEFAULT_AMCS).split(",") if token.strip()]


def _matches_amc(row: dict[str, Any], amc: str) -> bool:
    labels = AMC_LABELS.get(amc, (amc,))
    text = " ".join(str(row.get(field) or "").lower() for field in ("amc_name", "scheme_name"))
    return any(label in text for label in labels)


def _issues(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def build_diagnostics(amcs: list[str] | None = None) -> dict[str, Any]:
    if not supabase:
        return {"status": "error", "reason": "supabase_not_configured"}

    requested_amcs = amcs or _parse_amc_list(os.getenv("MF_DISCLOSURE_COVERAGE_AMCS"))
    raw_docs = _get_all("mf_raw_documents", "id,amc_code,document_type,source_document_type,parse_status,validation_issues")
    review_rows = _get_all("mf_parse_review_queue", "source_document_id,amc_code,validation_issues")
    schemes = _get_all("mf_schemes", "id,amc_code,scheme_name")
    scheme_holdings = _get_all("mf_scheme_holdings", "scheme_id")
    family_mapping = _get_all("mutual_fund_family_mapping", "scheme_code,family_id")
    final_holdings = _get_all("mutual_fund_holdings", "scheme_code,family_id")
    final_sectors = _get_all("mutual_fund_sectors", "scheme_code,family_id")
    snapshot_rows = _get_all(
        "mutual_fund_core_snapshot",
        "scheme_code,scheme_name,amc_name,aum,expense_ratio,benchmark,fund_manager,risk_level",
    )

    scheme_to_amc = {str(row.get("id")): str(row.get("amc_code") or "").lower() for row in schemes if row.get("id")}
    parsed_scheme_counts: Counter[str] = Counter(
        scheme_to_amc[str(row.get("scheme_id"))]
        for row in scheme_holdings
        if scheme_to_amc.get(str(row.get("scheme_id")))
    )

    scheme_to_family = {str(row.get("scheme_code")): str(row.get("family_id")) for row in family_mapping if row.get("scheme_code") and row.get("family_id")}
    snapshot_family_by_amc: dict[str, set[str]] = defaultdict(set)
    for amc in requested_amcs:
        for row in snapshot_rows:
            if not _matches_amc(row, amc):
                continue
            scheme_code = str(row.get("scheme_code") or "")
            family_id = scheme_to_family.get(scheme_code) or f"scheme-{scheme_code}"
            snapshot_family_by_amc[amc].add(family_id)

    final_holding_families = {str(row.get("family_id")) for row in final_holdings if row.get("family_id")}
    final_sector_families = {str(row.get("family_id")) for row in final_sectors if row.get("family_id")}

    review_issues_by_doc: dict[str, list[str]] = defaultdict(list)
    for row in review_rows:
        doc_id = str(row.get("source_document_id") or "")
        if doc_id:
            review_issues_by_doc[doc_id].extend(_issues(row.get("validation_issues")))

    report: dict[str, Any] = {"status": "ok", "amcs": {}}
    for amc in requested_amcs:
        doc_status: Counter[str] = Counter()
        doc_type_status: dict[str, Counter[str]] = defaultdict(Counter)
        issue_counts: Counter[str] = Counter()
        for doc in raw_docs:
            if str(doc.get("amc_code") or "").lower() != amc:
                continue
            status = str(doc.get("parse_status") or "unknown")
            document_type = str(doc.get("document_type") or doc.get("source_document_type") or "unknown")
            doc_status[status] += 1
            doc_type_status[document_type][status] += 1
            issues = [*_issues(doc.get("validation_issues")), *review_issues_by_doc.get(str(doc.get("id") or ""), [])]
            issue_counts.update(issues)

        families = snapshot_family_by_amc.get(amc, set())
        family_rows = [
            row
            for row in snapshot_rows
            if _matches_amc(row, amc)
            and (scheme_to_family.get(str(row.get("scheme_code") or "")) or f"scheme-{row.get('scheme_code') or ''}") in families
        ]
        rows_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in family_rows:
            scheme_code = str(row.get("scheme_code") or "")
            family_id = scheme_to_family.get(scheme_code) or f"scheme-{scheme_code}"
            rows_by_family[family_id].append(row)
        core_counts = {
            field: sum(
                1
                for rows in rows_by_family.values()
                if any(row.get(field) not in (None, "") for row in rows)
            )
            for field in ("aum", "expense_ratio", "benchmark", "fund_manager", "risk_level")
        }
        report["amcs"][amc] = {
            "documents_by_status": dict(sorted(doc_status.items())),
            "documents_by_type_status": {key: dict(sorted(value.items())) for key, value in sorted(doc_type_status.items())},
            "review_issue_counts": dict(issue_counts.most_common(12)),
            "parser_scheme_holdings_count": parsed_scheme_counts.get(amc, 0),
            "snapshot_family_count": len(families),
            "aum_family_count": core_counts["aum"],
            "expense_ratio_family_count": core_counts["expense_ratio"],
            "benchmark_family_count": core_counts["benchmark"],
            "fund_manager_family_count": core_counts["fund_manager"],
            "risk_level_family_count": core_counts["risk_level"],
            "final_holding_family_count": len(families & final_holding_families),
            "final_sector_family_count": len(families & final_sector_families),
            "missing_final_holding_family_count": len(families - final_holding_families),
            "missing_final_sector_family_count": len(families - final_sector_families),
        }
    return report


def main() -> int:
    amcs = _parse_amc_list(os.getenv("MF_DISCLOSURE_DIAGNOSTIC_AMCS") or os.getenv("MF_DISCLOSURE_COVERAGE_AMCS"))
    print(json.dumps(build_diagnostics(amcs), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
