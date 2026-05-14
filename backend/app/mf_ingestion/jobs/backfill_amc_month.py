from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.mf_ingestion.services.ingestion_service import IngestionService
from app.mf_ingestion.services.parsing_service import ParsingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amc", required=True)
    parser.add_argument("--document-type", default="portfolio_disclosure", choices=("factsheet", "portfolio_disclosure"))
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--parse-limit", type=int, default=100)
    args = parser.parse_args()

    target_month = date(args.year, args.month, 1).isoformat()

    ingestion = IngestionService()
    ingest_result = ingestion.ingest_documents(
        amc=args.amc,
        document_type=args.document_type,
        max_documents=args.parse_limit,
    )

    parsing = ParsingService()
    parse_result = parsing.parse_pending_documents(limit=args.parse_limit, amc_code=args.amc, report_month=target_month)

    logger.info(json.dumps({"ingest": ingest_result, "parse": parse_result}, indent=2, default=str))


if __name__ == "__main__":
    main()
