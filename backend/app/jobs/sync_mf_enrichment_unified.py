from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from backend.scripts import sync_mf_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheme-codes", type=str, default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    logger.info("Starting AMFI + AMC disclosure mutual fund enrichment.")
    summary = sync_mf_metadata.main()
    rendered = json.dumps(summary, indent=2, default=str)
    logger.info("Mutual-fund enrichment result: %s", rendered)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    return 0 if summary.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
