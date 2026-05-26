from __future__ import annotations

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("IndianAPI mutual fund ingestion is disabled. Use sync_mf_enrichment_unified instead.")


if __name__ == "__main__":
    main()
