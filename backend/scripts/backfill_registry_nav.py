"""Backfill NAV history into nav_api_cache for the 29 catalog registry funds."""
import json
import logging
import os
from pathlib import Path
import sys
import time

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from app.services.mfapi_service import get_cached_nav_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    config_file = BASE_DIR / "config" / "catalog_registry_funds.json"
    funds = json.loads(config_file.read_text(encoding="utf-8"))
    logger.info("Starting NAV backfill for %d registry funds...", len(funds))

    successes = []
    failures = []

    for i, fund in enumerate(funds, 1):
        code = str(fund["schemeCode"])
        name = fund["schemeName"]
        logger.info("[%d/%d] Fetching NAV history for %s (%s)...", i, len(funds), code, name)
        try:
            res = get_cached_nav_history(code, force_refresh=True)
            status = res.get("cache_status")
            points = res.get("point_count", 0)
            if points > 0:
                logger.info("  -> Success for %s: %d points, status=%s", code, points, status)
                successes.append({"scheme_code": code, "points": points, "status": status})
            else:
                logger.warning("  -> Zero points for %s: %s", code, res.get("error"))
                failures.append({"scheme_code": code, "error": res.get("error") or "zero_points"})
        except Exception as exc:
            logger.error("  -> Exception for %s: %s", code, exc)
            failures.append({"scheme_code": code, "error": str(exc)})

        time.sleep(0.3)

    logger.info("Backfill complete: %d succeeded, %d failed", len(successes), len(failures))
    return {"succeeded": len(successes), "failed": len(failures), "failures": failures}


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2))
