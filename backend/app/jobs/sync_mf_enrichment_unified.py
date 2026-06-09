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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheme-codes", type=str, default="")
    parser.parse_args()

    logger.info("Starting AMFI + AMC disclosure mutual fund enrichment.")
    sync_mf_metadata.main()
    logger.info("Mutual-fund enrichment completed without external fallback providers.")


if __name__ == "__main__":
    main()
