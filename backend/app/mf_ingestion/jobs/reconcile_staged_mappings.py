from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.services.parsing_service import ParsingService


def _page_rows(build_query: Callable[[], Any], page_size: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = build_query().order("id").range(offset, offset + page_size - 1).execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


def _mapping_payload(
    *,
    scheme_code: str,
    family_id: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "mapped_scheme_code": scheme_code,
        "mapped_family_id": family_id,
        "mapping_confidence": confidence,
        "mapping_status": "mapped",
    }


def reconcile_staged_mappings(
    *,
    amc_code: str,
    report_month: str,
    apply: bool,
    source_document_id: str | None = None,
    limit_documents: int = 200,
) -> dict[str, Any]:
    if not supabase:
        return {"status": "error", "issues": ["supabase_not_configured"]}

    documents_query = (
        supabase.table("mf_raw_documents")
        .select("id,amc_code,report_month,parse_status")
        .in_("amc_code", [amc_code.lower(), amc_code.upper(), amc_code])
        .eq("report_month", report_month)
        .in_("parse_status", ["parsed", "parsed_partial"])
        .order("downloaded_at", desc=True)
        .limit(limit_documents)
    )
    if source_document_id:
        documents_query = documents_query.eq("id", source_document_id)
    documents = documents_query.execute().data or []

    service = ParsingService()
    cache: dict[str, tuple[str | None, str | None, float, str]] = {}
    proposed_candidates = 0
    proposed_holdings_groups = 0
    applied_candidates = 0
    applied_holdings_groups = 0
    unresolved: list[dict[str, Any]] = []

    for document in documents:
        document_id = str(document["id"])
        normalized_amc = str(document.get("amc_code") or amc_code)
        candidates = _page_rows(
            lambda: (
                supabase.table("mf_factsheet_candidates")
                .select(
                    "id,raw_scheme_name,mapped_scheme_code,mapped_family_id,"
                    "mapping_confidence,mapping_status,promotion_status,validation_issues"
                )
                .eq("source_document_id", document_id)
            )
        )
        holdings = _page_rows(
            lambda: (
                supabase.table("mf_scheme_holdings")
                .select(
                    "id,raw_scheme_name,mapped_scheme_code,mapped_family_id,"
                    "mapping_confidence,mapping_status"
                )
                .eq("source_document_id", document_id)
            )
        )

        for row_type, rows in (("candidate", candidates), ("holdings", holdings)):
            unique_rows: dict[str, dict[str, Any]] = {}
            for row in rows:
                raw_name = str(row.get("raw_scheme_name") or "").strip()
                if raw_name:
                    unique_rows.setdefault(raw_name, row)
            for raw_name, row in unique_rows.items():
                resolution = cache.get(raw_name)
                if resolution is None:
                    resolution = service._resolve_staged_mapping(normalized_amc, raw_name)
                    cache[raw_name] = resolution
                scheme_code, family_id, confidence, status = resolution
                if status != "mapped" or not scheme_code or not family_id or confidence < 90.0:
                    unresolved.append(
                        {
                            "source_document_id": document_id,
                            "row_type": row_type,
                            "raw_scheme_name": raw_name,
                            "mapping_status": status,
                            "mapping_confidence": confidence,
                        }
                    )
                    continue
                payload = _mapping_payload(
                    scheme_code=scheme_code,
                    family_id=family_id,
                    confidence=confidence,
                )
                if row_type == "candidate":
                    proposed_candidates += 1
                    issues = [
                        str(issue)
                        for issue in (row.get("validation_issues") or [])
                        if not str(issue).startswith("scheme_mapping_")
                    ]
                    payload["validation_issues"] = issues
                    if row.get("promotion_status") not in {"promoted", "partially_promoted"}:
                        payload["promotion_status"] = "staged"
                    if apply:
                        supabase.table("mf_factsheet_candidates").update(payload).eq(
                            "id", row["id"]
                        ).execute()
                        applied_candidates += 1
                else:
                    proposed_holdings_groups += 1
                    if apply:
                        (
                            supabase.table("mf_scheme_holdings")
                            .update(payload)
                            .eq("source_document_id", document_id)
                            .eq("raw_scheme_name", raw_name)
                            .execute()
                        )
                        applied_holdings_groups += 1

    return {
        "status": "applied" if apply else "dry_run",
        "amc_code": amc_code,
        "report_month": report_month,
        "documents": len(documents),
        "proposed_candidates": proposed_candidates,
        "proposed_holdings_groups": proposed_holdings_groups,
        "applied_candidates": applied_candidates,
        "applied_holdings_groups": applied_holdings_groups,
        "unresolved_count": len(unresolved),
        "unresolved_sample": unresolved[:50],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-evaluate staging-only scheme mappings; runtime tables are never written."
    )
    parser.add_argument("--amc", required=True)
    parser.add_argument("--report-month", required=True, help="Exact month as YYYY-MM-01")
    parser.add_argument("--source-document-id")
    parser.add_argument("--limit-documents", type=int, default=200)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = reconcile_staged_mappings(
        amc_code=args.amc,
        report_month=args.report_month,
        apply=args.apply,
        source_document_id=args.source_document_id,
        limit_documents=args.limit_documents,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in {"dry_run", "applied"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
