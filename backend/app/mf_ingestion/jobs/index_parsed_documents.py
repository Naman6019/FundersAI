from __future__ import annotations

import argparse
from pathlib import Path

from app.database import supabase
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser
from app.mf_ingestion.services.parsing_service import ParsingService
from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.document_indexing_service import DocumentIndexingService


def main() -> None:
    parser = argparse.ArgumentParser(description="Create citations-ready embeddings from parsed official AMC PDFs")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    if not supabase:
        raise SystemExit("supabase_not_configured")
    documents = supabase.table("mf_raw_documents").select("*").in_("parse_status", ["parsed", "parsed_partial"]).order("parsed_at", desc=True).limit(max(1, args.limit)).execute().data or []
    parser_service = ParsingService()
    indexer = DocumentIndexingService(MutualFundRepository())
    for document in documents:
        path, temporary_path = parser_service._resolve_document_path(document)
        try:
            if path and Path(path).suffix.lower() == ".pdf":
                print({"document_id": document["id"], "chunks_indexed": indexer.index(document, PDFTextParser().extract_text(path))})
        finally:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
