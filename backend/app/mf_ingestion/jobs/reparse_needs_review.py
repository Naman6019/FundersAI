from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.services.parsing_service import ParsingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_RETRY_STATUSES = ("needs_review", "failed", "parsed_partial")


def _parse_statuses(raw: str | None) -> list[str]:
    values = []
    for token in str(raw or "").split(","):
        value = token.strip().lower()
        if value and value not in values:
            values.append(value)
    return values or list(DEFAULT_RETRY_STATUSES)


def _to_utc_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _latest_attempt_at(document: dict[str, Any]) -> datetime | None:
    parsed_at = _to_utc_datetime(document.get("parsed_at"))
    downloaded_at = _to_utc_datetime(document.get("downloaded_at"))
    values = [dt for dt in (parsed_at, downloaded_at) if dt is not None]
    return max(values) if values else None


def _eligible_for_retry(document: dict[str, Any], *, cutoff: datetime) -> bool:
    latest_at = _latest_attempt_at(document)
    if latest_at is None:
        return True
    return latest_at <= cutoff


def load_retry_documents(
    *,
    supabase_client: Any,
    statuses: list[str],
    amc: str | None,
    limit: int,
    min_age_hours: float,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = now_utc - timedelta(hours=max(float(min_age_hours), 0.0))
    normalized_statuses = [status.strip().lower() for status in statuses if status.strip()]
    query_limit = max(limit * 10, limit, 100)

    query = supabase_client.table("mf_raw_documents").select("*").in_("parse_status", normalized_statuses)
    if amc:
        query = query.in_("amc_code", [amc.lower(), amc.upper(), amc])
    rows = query.limit(query_limit).execute().data or []

    eligible = [
        row
        for row in rows
        if str(row.get("parse_status") or "").strip().lower() in normalized_statuses
        and _eligible_for_retry(row, cutoff=cutoff)
    ]
    eligible.sort(key=lambda row: _latest_attempt_at(row) or datetime.min.replace(tzinfo=timezone.utc))
    return eligible[:limit]


def reparse_documents(documents: list[dict[str, Any]], service: ParsingService) -> dict[str, int]:
    success_count = 0
    still_actionable_count = 0
    runtime_error_count = 0
    skipped_duplicate_count = 0

    for doc in documents:
        doc_id = doc.get("id")
        amc_code = doc.get("amc_code")
        report_month = doc.get("report_month")
        logger.info("Processing doc %s (AMC: %s, Month: %s)", doc_id, amc_code, report_month)

        try:
            if amc_code and report_month:
                existing_parsed = supabase.table("mf_raw_documents").select("id").eq("amc_code", amc_code).eq("report_month", report_month).eq("parse_status", "parsed").limit(1).execute()
                if existing_parsed.data:
                    logger.info("Skipping doc %s as duplicate. AMC %s, Month %s already successfully parsed.", doc_id, amc_code, report_month)
                    supabase.table("mf_raw_documents").update({"parse_status": "skipped_duplicate"}).eq("id", doc_id).execute()
                    supabase.table("mf_parse_review_queue").delete().eq("source_document_id", doc_id).execute()
                    skipped_duplicate_count += 1
                    continue

            supabase.table("mf_raw_documents").update({"parse_status": "needs_reparse"}).eq("id", doc_id).execute()

            doc_to_parse = dict(doc)
            doc_to_parse["parse_status"] = "needs_reparse"
            result = service._parse_one(doc_to_parse)
            status = str((result or {}).get("status") or "").strip().lower()

            if status not in {"failed", "needs_review", "parsed_partial"}:
                logger.info("Doc %s no longer actionable after retry: %s", doc_id, result)
                supabase.table("mf_parse_review_queue").delete().eq("source_document_id", doc_id).execute()
                success_count += 1
            else:
                logger.warning("Doc %s still needs action after retry: %s", doc_id, result)
                still_actionable_count += 1
        except Exception as exc:
            logger.exception("Unexpected error parsing doc %s: %s", doc_id, exc)
            runtime_error_count += 1

    return {
        "success_count": success_count,
        "still_actionable_count": still_actionable_count,
        "runtime_error_count": runtime_error_count,
        "skipped_duplicate_count": skipped_duplicate_count,
    }


def retry_exit_code(summary: dict[str, int], *, fail_on_still_actionable: bool = False) -> int:
    if summary["runtime_error_count"] > 0:
        return 1
    if fail_on_still_actionable and summary["still_actionable_count"] > 0:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amc", default=None, help="Filter by AMC code (e.g., ppfas, icici)")
    parser.add_argument("--limit", type=int, default=50, help="Max docs to retry.")
    parser.add_argument("--min-age-hours", type=float, default=6.0, help="Retry only docs older than this many hours.")
    parser.add_argument("--statuses", default="needs_review,failed,parsed_partial", help="Comma-separated parse statuses to retry.")
    parser.add_argument(
        "--fail-on-still-actionable",
        action="store_true",
        help="Exit non-zero when retried docs remain failed, needs_review, or parsed_partial.",
    )
    args = parser.parse_args()

    if not supabase:
        logger.error("Supabase is not configured.")
        return 1

    service = ParsingService()
    statuses = _parse_statuses(args.statuses)
    documents = load_retry_documents(
        supabase_client=supabase,
        statuses=statuses,
        amc=args.amc,
        limit=max(args.limit, 1),
        min_age_hours=max(args.min_age_hours, 0.0),
    )

    if not documents:
        logger.info(
            "No eligible parser action documents found. statuses=%s amc=%s min_age_hours=%s",
            statuses,
            args.amc,
            args.min_age_hours,
        )
        return 0

    logger.info("Found %s eligible documents to retry.", len(documents))
    summary = reparse_documents(documents, service)
    logger.info("Reparse retry complete: %s", json.dumps(summary, sort_keys=True))
    return retry_exit_code(summary, fail_on_still_actionable=args.fail_on_still_actionable)


if __name__ == "__main__":
    raise SystemExit(main())
