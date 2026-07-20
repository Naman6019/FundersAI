from __future__ import annotations

import argparse
import json
import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.mf_ingestion.services.ingestion_service import IngestionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOC_TYPES = ("factsheet", "portfolio_disclosure")


def _is_nonfatal_skip(item: dict[str, object]) -> bool:
    status = str(item.get("status") or "").strip().lower()
    reason = str(item.get("reason") or "").strip().lower()
    return status == "skipped" and reason in {"duplicate_checksum"}


def _has_document_errors(result: dict[str, object]) -> bool:
    skipped = result.get("skipped_documents")
    if not isinstance(skipped, list):
        return False
    for item in skipped:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").strip().lower()
        if status == "error":
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amc", default="ppfas", help="AMC key, e.g. ppfas")
    parser.add_argument("--document-type", choices=DOC_TYPES)
    parser.add_argument("--all-document-types", action="store_true")
    parser.add_argument("--max-documents", type=int, default=1)
    parser.add_argument(
        "--allow-disabled-source",
        action="store_true",
        help="Explicitly test acquisition for a production-disabled source without enabling it in the registry.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when discovery/download has issues.")
    args = parser.parse_args()

    if not args.document_type and not args.all_document_types:
        parser.error("Provide either --document-type or --all-document-types")

    service = IngestionService()

    targets = DOC_TYPES if args.all_document_types else (args.document_type,)
    results: dict[str, object] = {}
    strict_failures: list[str] = []
    for document_type in targets:
        result = service.ingest_documents(
            amc=args.amc,
            document_type=document_type,
            max_documents=args.max_documents,
            allow_disabled_source=args.allow_disabled_source,
        )
        results[document_type] = result
        if not args.strict:
            continue
        status = str(result.get("status") or "").strip().lower()
        reason = str(result.get("reason") or "").strip().lower()
        ingested = result.get("ingested_documents")
        skipped = result.get("skipped_documents")
        ingested_docs = ingested if isinstance(ingested, list) else []
        skipped_docs = skipped if isinstance(skipped, list) else []

        if status == "error":
            strict_failures.append(f"{document_type}:status_error:{reason or 'unknown'}")
            continue
        if reason == "no_documents_found":
            strict_failures.append(f"{document_type}:no_documents_found")
            continue
        if _has_document_errors(result):
            strict_failures.append(f"{document_type}:download_errors")
            continue
        if not ingested_docs and skipped_docs and all(
            isinstance(item, dict) and _is_nonfatal_skip(item) for item in skipped_docs
        ):
            # Duplicate checksum skips are acceptable and should not fail strict mode.
            continue

    logger.info(json.dumps(results, indent=2, default=str))
    if strict_failures:
        logger.error("Strict ingestion checks failed: %s", ", ".join(strict_failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
