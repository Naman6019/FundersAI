from __future__ import annotations

import argparse
import logging
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.mfapi_service import delete_expired_nav_cache_rows
from app.services.mf_metric_target_service import supported_metric_targets
from app.repositories.stock_repository import StockRepository

logging.basicConfig(level=logging.INFO)


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete NAV cache rows beyond the retention window.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        logging.info("NAV cache retention dry run: deletion skipped")
        return 0
    repo = StockRepository()
    if not repo.supabase:
        logging.error("Supabase client is not configured; refusing unprotected cache cleanup.")
        return 1
    try:
        protected = {
            row["scheme_code"]
            for row in supported_metric_targets(repo.supabase)
        }
    except Exception as exc:
        logging.error("Unable to resolve protected metric targets; refusing cache cleanup: %s", exc)
        return 1
    delete_expired_nav_cache_rows(protected_scheme_codes=protected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
