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

from app.mf_ingestion.services.parsing_service import ParsingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--amc", default=None)
    parser.add_argument("--report-month", default=None, help="YYYY-MM-01")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when parse failures occur.")
    parser.add_argument(
        "--fail-on-needs-review",
        action="store_true",
        help="When used with --strict, treat needs_review as a failure.",
    )
    args = parser.parse_args()

    service = ParsingService()
    result = service.parse_pending_documents(limit=args.limit, amc_code=args.amc, report_month=args.report_month)
    logger.info(json.dumps(result, indent=2, default=str))
    if args.strict:
        if str(result.get("status") or "").strip().lower() == "error":
            return 1
        processed = result.get("processed")
        if isinstance(processed, list):
            for item in processed:
                if not isinstance(item, dict):
                    continue
                status = str(item.get("status") or "").strip().lower()
                if status == "failed":
                    return 1
                if args.fail_on_needs_review and status == "needs_review":
                    return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
