from __future__ import annotations

import argparse
import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from backend.scripts import sync_mf_metadata
from app.jobs import sync_mf_enrichment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _enabled(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheme-codes", type=str, default="")
    parser.add_argument("--limit", type=int, default=int(os.getenv("MFDATA_SYNC_SCHEME_LIMIT", "200")))
    args = parser.parse_args()

    logger.info("Starting AMFI-first mutual fund enrichment.")
    sync_mf_metadata.main()

    if not _enabled("ENABLE_MFDATA_FALLBACK_SYNC", False):
        logger.info("ENABLE_MFDATA_FALLBACK_SYNC is false. Skipping optional MFdata fallback.")
        return

    logger.info("Starting optional MFdata fallback. Existing AMFI/AMC/MFapi values stay authoritative.")
    previous_argv = sys.argv[:]
    sys.argv = [
        previous_argv[0],
        "--scheme-codes",
        args.scheme_codes,
        "--limit",
        str(args.limit),
    ]
    try:
        os.environ["ENABLE_MF_ENRICHMENT_SYNC"] = "true"
        sync_mf_enrichment.main()
    finally:
        sys.argv = previous_argv


if __name__ == "__main__":
    main()
