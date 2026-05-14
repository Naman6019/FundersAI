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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amc", default="ppfas", help="AMC key, e.g. ppfas")
    parser.add_argument("--document-type", choices=DOC_TYPES)
    parser.add_argument("--all-document-types", action="store_true")
    parser.add_argument("--max-documents", type=int, default=1)
    args = parser.parse_args()

    if not args.document_type and not args.all_document_types:
        parser.error("Provide either --document-type or --all-document-types")

    service = IngestionService()

    targets = DOC_TYPES if args.all_document_types else (args.document_type,)
    results: dict[str, object] = {}
    for document_type in targets:
        results[document_type] = service.ingest_documents(
            amc=args.amc,
            document_type=document_type,
            max_documents=args.max_documents,
        )

    logger.info(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
