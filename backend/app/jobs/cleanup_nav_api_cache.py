from __future__ import annotations

import argparse
import logging
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.mfapi_service import delete_expired_nav_cache_rows

logging.basicConfig(level=logging.INFO)


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete NAV cache rows beyond the retention window.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        logging.info("NAV cache retention dry run: deletion skipped")
        return 0
    delete_expired_nav_cache_rows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
