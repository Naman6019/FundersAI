from __future__ import annotations

import argparse
import json
import logging
import os
import sys
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

SUPPORTED_RISK_AMCS = ("hdfc", "icici", "ppfas", "sbi")


def _fetch_factsheet_documents(*, limit: int, amc: str | None, report_month: str | None) -> list[dict[str, Any]]:
    if not supabase:
        return []

    docs_by_id: dict[str, dict[str, Any]] = {}
    for field in ("document_type", "source_document_type"):
        query = supabase.table("mf_raw_documents").select("*").eq(field, "factsheet").limit(limit)
        if amc:
            query = query.in_("amc_code", [amc.lower(), amc.upper(), amc])
        else:
            query = query.in_("amc_code", list(SUPPORTED_RISK_AMCS) + [value.upper() for value in SUPPORTED_RISK_AMCS])
        if report_month:
            query = query.eq("report_month", report_month)
        try:
            for doc in query.execute().data or []:
                doc_id = str(doc.get("id") or "")
                if doc_id:
                    docs_by_id[doc_id] = doc
        except Exception as exc:
            logger.warning("event=factsheet_backfill_query_failed field=%s reason=%s", field, exc)

    return list(docs_by_id.values())[:limit]


def backfill_factsheet_risk_levels(
    *, limit: int = 50, amc: str | None = None, report_month: str | None = None, dry_run: bool = False
) -> dict[str, Any]:
    if not supabase:
        return {"status": "error", "reason": "supabase_not_configured"}

    normalized_amc = str(amc or "").strip().lower() or None
    if normalized_amc and normalized_amc not in SUPPORTED_RISK_AMCS:
        return {"status": "error", "reason": f"unsupported_amc:{normalized_amc}"}

    documents = _fetch_factsheet_documents(limit=limit, amc=normalized_amc, report_month=report_month)
    if dry_run:
        return {
            "status": "ok",
            "dry_run": True,
            "count": len(documents),
            "documents": [
                {
                    "id": doc.get("id"),
                    "amc_code": doc.get("amc_code"),
                    "report_month": doc.get("report_month"),
                    "source_url": doc.get("source_url"),
                }
                for doc in documents
            ],
        }

    service = ParsingService()
    processed = []
    for document in documents:
        parse_doc = dict(document)
        parse_doc["document_type"] = parse_doc.get("document_type") or parse_doc.get("source_document_type") or "factsheet"
        parse_doc["parse_status"] = "needs_reparse"
        processed.append(service._parse_one(parse_doc, bypass_official_coverage=True))

    return {"status": "ok", "count": len(processed), "processed": processed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--amc", default=None)
    parser.add_argument("--report-month", default=None, help="YYYY-MM-01")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = backfill_factsheet_risk_levels(
        limit=args.limit,
        amc=args.amc,
        report_month=args.report_month,
        dry_run=args.dry_run,
    )
    logger.info(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
