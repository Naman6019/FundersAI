from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.downloaders.amc_downloader import AMCDownloader
from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.services.ingestion_service import IngestionService
from app.mf_ingestion.services.source_manifest import build_source_manifest
from app.mf_ingestion.sources.registry import get_source
from app.mf_ingestion.storage.checksum import sha256_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_STATUSES = ("skipped_no_source_data", "failed")


def load_reacquire_documents(*, amc: str | None, limit: int, statuses: list[str]) -> list[dict[str, Any]]:
    if not supabase:
        return []
    query = (
        supabase.table("mf_raw_documents")
        .select("*")
        .in_("parse_status", statuses)
        .order("downloaded_at", desc=False)
        .limit(max(limit * 5, limit, 20))
    )
    if amc:
        query = query.in_("amc_code", [amc.lower(), amc.upper(), amc])
    rows = query.execute().data or []
    selected = []
    for row in rows:
        storage_backend = str(row.get("storage_backend") or "local").strip().lower()
        source_url = str(row.get("source_url") or "").strip()
        issues = [str(item) for item in (row.get("validation_issues") or [])]
        if storage_backend == "r2":
            continue
        if not source_url.startswith(("http://", "https://")):
            continue
        if row.get("parse_status") == "failed" and "raw_file_missing" not in issues:
            continue
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def reacquire_document(row: dict[str, Any], service: IngestionService, *, dry_run: bool = False) -> dict[str, Any]:
    source = get_source(str(row.get("amc_code") or ""))
    document_type = str(row.get("document_type") or row.get("source_document_type") or "").strip().lower()
    source_url = str(row.get("source_url") or "").strip()
    discovered = DiscoveredDocument(
        amc_name=source.amc_name,
        amc_code=source.amc_code,
        document_type=document_type,
        title=str(row.get("file_name") or Path(source_url.split("?", 1)[0]).name or "official-document"),
        url=source_url,
        discovery_page_url=str(row.get("discovery_page_url") or source_url),
        file_ext=str(row.get("file_ext") or Path(source_url.split("?", 1)[0]).suffix or ""),
        report_month=_parse_report_month(row.get("report_month")),
        priority_score=9_000_000,
    )
    if dry_run:
        return {"id": row.get("id"), "status": "dry_run", "source_url": source_url}

    downloader = AMCDownloader(source, service.config.request_timeout_seconds, service.config.user_agent)
    downloaded = downloader.download(discovered)
    checksum = sha256_bytes(downloaded.file_bytes)
    raw_path, storage_backend, storage_bucket, storage_key, storage_metadata = service._persist_raw_document(
        downloaded=downloaded,
        checksum=checksum,
    )
    storage_metadata["source_manifest"] = build_source_manifest(
        source=source,
        document_type=downloaded.document_type,
        source_url=downloaded.source_url,
        discovery_page_url=downloaded.discovery_page_url,
        report_month=downloaded.report_month,
        expected_file_type=downloaded.file_ext or downloaded.file_name,
        checksum=checksum,
        acquisition_status="reacquired",
    )
    payload = {
        "storage_path": raw_path,
        "storage_backend": storage_backend,
        "storage_bucket": storage_bucket,
        "storage_key": storage_key,
        "storage_metadata": storage_metadata,
        "checksum": checksum,
        "content_type": downloaded.content_type,
        "file_size_bytes": downloaded.file_size_bytes,
        "parse_status": "pending",
        "validation_issues": [],
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "parsed_at": None,
    }
    supabase.table("mf_raw_documents").update(payload).eq("id", row["id"]).execute()
    return {"id": row.get("id"), "status": "reacquired", "storage_backend": storage_backend, "storage_key": storage_key}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amc", default=None)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--statuses", default=",".join(DEFAULT_STATUSES))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not supabase:
        logger.error("Supabase is not configured.")
        return 1

    statuses = [token.strip() for token in args.statuses.split(",") if token.strip()]
    service = IngestionService()
    rows = load_reacquire_documents(amc=args.amc, limit=max(args.limit, 1), statuses=statuses)
    results = []
    failures = 0
    for row in rows:
        try:
            results.append(reacquire_document(row, service, dry_run=args.dry_run))
        except Exception as exc:
            failures += 1
            logger.exception("Reacquire failed for id=%s: %s", row.get("id"), exc)
            results.append({"id": row.get("id"), "status": "error", "reason": type(exc).__name__})
    print(json.dumps({"status": "ok" if failures == 0 else "partial", "results": results}, indent=2, default=str))
    return 1 if failures else 0


def _parse_report_month(value: object):
    if value in (None, ""):
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.date().replace(day=1)
        except ValueError:
            continue
    return None


if __name__ == "__main__":
    raise SystemExit(main())
