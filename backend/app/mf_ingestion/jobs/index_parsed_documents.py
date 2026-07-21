from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.database import supabase
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser
from app.mf_ingestion.services.parsing_service import ParsingService
from app.mf_ingestion.sources.registry import get_source
from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.document_indexing_service import DocumentIndexingService

DEFAULT_AMCS = "axis,hdfc,sbi,icici,ppfas,nippon"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create citations-ready chunks from parsed official AMC PDFs")
    parser.add_argument("--limit", type=int, default=10, help="Maximum new documents to index.")
    parser.add_argument("--amcs", default=DEFAULT_AMCS, help="Comma-separated enabled AMC source keys.")
    parser.add_argument("--force", action="store_true", help="Reindex documents that already have chunks.")
    parser.add_argument("--require-embeddings", action="store_true", help="Fail instead of using lexical-only chunks.")
    parser.add_argument("--minimum-available", type=int, default=0, help="Require this many indexed documents after the run.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any selected document fails.")
    parser.add_argument("--output", help="Optional JSON summary path.")
    args = parser.parse_args()

    if not supabase:
        raise SystemExit("supabase_not_configured")
    _verify_chunk_schema()
    if args.limit < 1:
        parser.error("--limit must be at least one")
    if args.minimum_available < 0:
        parser.error("--minimum-available cannot be negative")

    amc_keys = _normalize_amcs(args.amcs)
    amc_codes = [get_source(key).amc_code for key in amc_keys]
    candidate_limit = max(args.limit * 4, 20)
    documents = (
        supabase.table("mf_raw_documents")
        .select("*")
        .in_("parse_status", ["parsed", "parsed_partial"])
        .in_("amc_code", amc_codes)
        .eq("file_ext", ".pdf")
        .order("parsed_at", desc=True)
        .limit(candidate_limit)
        .execute()
        .data
        or []
    )
    existing_ids = _existing_document_ids(documents, require_embeddings=args.require_embeddings) if not args.force else set()
    parser_service = ParsingService()
    indexer = DocumentIndexingService(
        MutualFundRepository(),
        require_embeddings=args.require_embeddings,
    )
    indexed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for document in documents:
        document_id = str(document.get("id") or "")
        if document_id in existing_ids:
            skipped.append({"document_id": document_id, "reason": "already_indexed"})
            continue
        if len(indexed) >= args.limit:
            break

        path = None
        temporary_path = None
        try:
            path, temporary_path = parser_service._resolve_document_path(document)
            if not path or Path(path).suffix.lower() != ".pdf":
                raise RuntimeError("indexable_pdf_unavailable")
            chunk_count = indexer.index(document, PDFTextParser().extract_text(path))
            if chunk_count < 1:
                raise RuntimeError("document_produced_no_chunks")
            indexed.append(
                {
                    "document_id": document_id,
                    "amc_code": str(document.get("amc_code") or "").lower(),
                    "report_month": document.get("report_month"),
                    "chunks_indexed": chunk_count,
                    "index_mode": indexer.last_index_mode,
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "document_id": document_id,
                    "amc_code": str(document.get("amc_code") or "").lower(),
                    "error_type": type(exc).__name__,
                    "error": str(exc) or repr(exc),
                }
            )
        finally:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)

    available_count = len(existing_ids) + len(indexed)
    summary = {
        "requested_amcs": amc_keys,
        "candidate_pdf_count": len(documents),
        "previously_indexed_count": len(existing_ids),
        "newly_indexed_count": len(indexed),
        "available_document_count": available_count,
        "indexed": indexed,
        "skipped": skipped,
        "failures": failures,
    }
    rendered = json.dumps(summary, indent=2, default=str)
    print(rendered)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    if available_count < args.minimum_available:
        return 1
    if args.strict and failures:
        return 1
    return 0


def _normalize_amcs(raw: str) -> list[str]:
    values: list[str] = []
    for item in str(raw or "").split(","):
        key = item.strip().lower()
        if key and key not in values:
            get_source(key)
            values.append(key)
    if not values:
        raise ValueError("at_least_one_amc_required")
    return values


def _existing_document_ids(documents: list[dict[str, Any]], *, require_embeddings: bool = False) -> set[str]:
    document_ids = [str(document.get("id") or "") for document in documents if document.get("id")]
    if not document_ids:
        return set()
    query = supabase.table("amc_document_chunks").select("document_id").in_("document_id", document_ids)
    if require_embeddings:
        query = query.not_.is_("embedding", "null")
    rows = query.limit(5_000).execute().data or []
    return {str(row.get("document_id") or "") for row in rows if row.get("document_id")}


def _verify_chunk_schema() -> None:
    """Fail before downloading PDFs when the additive repair migration is missing."""
    (
        supabase.table("amc_document_chunks")
        .select("document_id,chunk_hash,parser_version,source_url")
        .limit(1)
        .execute()
    )


if __name__ == "__main__":
    raise SystemExit(main())
