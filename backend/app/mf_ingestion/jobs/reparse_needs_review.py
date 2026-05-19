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

from app.database import supabase
from app.mf_ingestion.services.parsing_service import ParsingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amc", default=None, help="Filter by AMC code (e.g., ppfas, icici)")
    args = parser.parse_args()

    if not supabase:
        logger.error("Supabase is not configured.")
        return 1

    service = ParsingService()
    
    # Query documents that are in needs_review or failed status
    query = supabase.table("mf_raw_documents").select("*").in_("parse_status", ["needs_review", "failed"])
    if args.amc:
        query = query.in_("amc_code", [args.amc.lower(), args.amc.upper()])
        
    documents = query.execute().data or []
    
    if not documents:
        logger.info("No documents found with parse_status = 'needs_review' or 'failed'.")
        return 0

    logger.info(f"Found {len(documents)} documents to re-parse.")
    
    success_count = 0
    failure_count = 0
    
    for doc in documents:
        doc_id = doc.get("id")
        amc_code = doc.get("amc_code")
        report_month = doc.get("report_month")
        logger.info(f"Processing doc {doc_id} (AMC: {amc_code}, Month: {report_month})")
        
        # Set parse_status to needs_reparse in database so the parser service bypasses already_parsed checks
        supabase.table("mf_raw_documents").update({"parse_status": "needs_reparse"}).eq("id", doc_id).execute()
        
        # Prepare document dict with parse_status = 'needs_reparse'
        doc_to_parse = dict(doc)
        doc_to_parse["parse_status"] = "needs_reparse"
        
        try:
            result = service._parse_one(doc_to_parse)
            status = result.get("status")
            reason = result.get("reason")
            
            if status == "parsed" or (isinstance(result, dict) and status != "failed" and status != "needs_review"):
                logger.info(f"Doc {doc_id} successfully parsed: {result}")
                # Clean up any pending review items for this document
                supabase.table("mf_parse_review_queue").delete().eq("source_document_id", doc_id).execute()
                success_count += 1
            else:
                logger.error(f"Doc {doc_id} failed to parse or needs review: {result}")
                failure_count += 1
        except Exception as e:
            logger.exception(f"Unexpected error parsing doc {doc_id}: {e}")
            failure_count += 1
            
    logger.info(f"Reparse complete. Successes: {success_count}, Failures/Review: {failure_count}")
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
