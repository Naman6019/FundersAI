from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.config import get_config
from app.mf_ingestion.parsers.factsheet_parser import FactsheetParser
from app.mf_ingestion.storage.r2_store import R2Store

ALLOWED_AMCS = {"uti", "absl"}


def _parse_month(value: str) -> date:
    raw = value.strip()
    if len(raw) == 7:
        raw = f"{raw}-01"
    return date.fromisoformat(raw).replace(day=1)


def _build_r2_store() -> R2Store:
    config = get_config()
    return R2Store(
        endpoint=config.r2_endpoint,
        access_key_id=config.r2_access_key_id,
        secret_access_key=config.r2_secret_access_key,
        raw_bucket=config.r2_raw_bucket,
        cold_bucket=config.r2_cold_bucket,
        signed_url_ttl_seconds=config.r2_signed_url_ttl_seconds,
    )


def _validate_document(
    document: dict[str, Any],
    *,
    expected_amc: str,
    expected_current_month: date,
    corrected_month: date,
    expected_checksum: str,
    observed_checksum: str,
    observed_body_month: date | None,
    has_applied_promotion: bool,
) -> list[str]:
    issues: list[str] = []
    if str(document.get("amc_code") or "").lower() != expected_amc:
        issues.append("source_amc_mismatch")
    if str(document.get("report_month") or "") != expected_current_month.isoformat():
        issues.append("source_current_month_mismatch")
    if str(document.get("checksum") or "") != expected_checksum:
        issues.append("source_checksum_mismatch")
    if observed_checksum != expected_checksum:
        issues.append("r2_checksum_mismatch")
    if str(document.get("storage_backend") or "").lower() != "r2":
        issues.append("source_not_stored_in_r2")
    if not document.get("storage_key"):
        issues.append("source_r2_key_missing")
    if observed_body_month != corrected_month:
        issues.append("observed_body_month_mismatch")
    if has_applied_promotion:
        issues.append("source_has_applied_promotion")
    return sorted(set(issues))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify official R2 body evidence before reconciling one MF raw-document month."
    )
    parser.add_argument("--source-document-id", required=True)
    parser.add_argument("--expected-amc", required=True, choices=sorted(ALLOWED_AMCS))
    parser.add_argument("--expected-current-month", required=True)
    parser.add_argument("--corrected-report-month", required=True)
    parser.add_argument("--expected-checksum", default="")
    parser.add_argument("--requested-by", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not supabase:
        print(json.dumps({"status": "error", "issues": ["supabase_not_configured"]}))
        return 2

    try:
        expected_current_month = _parse_month(args.expected_current_month)
        corrected_month = _parse_month(args.corrected_report_month)
    except ValueError:
        print(json.dumps({"status": "error", "issues": ["report_month_invalid"]}))
        return 2

    document_rows = (
        supabase.table("mf_raw_documents")
        .select(
            "id,amc_code,report_month,parse_status,checksum,storage_backend,"
            "storage_bucket,storage_key,source_url,source_document_type"
        )
        .eq("id", args.source_document_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not document_rows:
        print(json.dumps({"status": "error", "issues": ["source_document_not_found"]}))
        return 1
    document = document_rows[0]
    supplied_checksum = args.expected_checksum.strip()
    if args.apply and not supplied_checksum:
        print(
            json.dumps(
                {
                    "status": "error",
                    "issues": ["expected_checksum_required_for_apply"],
                }
            )
        )
        return 2
    reviewed_checksum = supplied_checksum or str(document.get("checksum") or "")

    applied_rows = (
        supabase.table("mf_promotion_runs")
        .select("id")
        .eq("source_document_id", args.source_document_id)
        .eq("status", "applied")
        .limit(1)
        .execute()
        .data
        or []
    )

    r2_store = _build_r2_store()
    if not r2_store.enabled:
        print(json.dumps({"status": "error", "issues": ["r2_not_configured"]}))
        return 2

    storage_key = str(document.get("storage_key") or "")
    suffix = Path(storage_key).suffix or ".pdf"
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="mf_month_audit_", suffix=suffix, delete=False) as handle:
            temp_path = handle.name
        r2_store.download_to_file(
            storage_key,
            temp_path,
            bucket=str(document.get("storage_bucket") or "") or None,
        )
        observed_checksum = hashlib.sha256(Path(temp_path).read_bytes()).hexdigest()
        observed_body_month = FactsheetParser().detect_report_month(temp_path)
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

    issues = _validate_document(
        document,
        expected_amc=args.expected_amc,
        expected_current_month=expected_current_month,
        corrected_month=corrected_month,
        expected_checksum=reviewed_checksum,
        observed_checksum=observed_checksum,
        observed_body_month=observed_body_month,
        has_applied_promotion=bool(applied_rows),
    )
    report = {
        "status": "eligible" if not issues else "rejected",
        "source_document_id": args.source_document_id,
        "amc_code": document.get("amc_code"),
        "source_url": document.get("source_url"),
        "expected_current_month": expected_current_month.isoformat(),
        "stored_report_month": document.get("report_month"),
        "corrected_report_month": corrected_month.isoformat(),
        "observed_body_month": observed_body_month.isoformat() if observed_body_month else None,
        "expected_checksum": reviewed_checksum,
        "checksum_source": "operator" if supplied_checksum else "database_dry_run",
        "observed_checksum": observed_checksum,
        "parse_status": document.get("parse_status"),
        "has_applied_promotion": bool(applied_rows),
        "issues": issues,
    }
    if issues:
        print(json.dumps(report, indent=2))
        return 1
    if not args.apply:
        report["status"] = "dry_run"
        print(json.dumps(report, indent=2))
        return 0

    result = supabase.rpc(
        "reconcile_mf_raw_document_report_month",
        {
            "p_source_document_id": args.source_document_id,
            "p_expected_current_month": expected_current_month.isoformat(),
            "p_corrected_report_month": corrected_month.isoformat(),
            "p_expected_checksum": reviewed_checksum,
            "p_observed_body_month": observed_body_month.isoformat(),
            "p_requested_by": args.requested_by,
            "p_reason": args.reason,
        },
    ).execute()
    report["status"] = "applied"
    report["result"] = result.data
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
