"""Populate canonical metadata for catalog registry funds into mutual_fund_core_snapshot."""
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")


def populate_registry_metadata() -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    config_file = BASE_DIR / "config" / "catalog_registry_funds.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    funds = json.loads(config_file.read_text(encoding="utf-8"))
    logger.info("Loaded %d registry funds from %s", len(funds), config_file.name)

    now_iso = datetime.now(timezone.utc).isoformat()
    updated = 0
    errors = []

    for fund in funds:
        code = str(fund["schemeCode"])
        payload = {
            "amc_name": fund["amcName"],
            "category": fund["category"],
            "plan_type": fund["plan"],
            "option_type": fund["option"],
            "benchmark": fund.get("benchmark"),
            "last_updated": now_iso,
        }
        try:
            res = (
                client.table("mutual_fund_core_snapshot")
                .update(payload)
                .eq("scheme_code", code)
                .execute()
            )
            if res.data:
                updated += 1
                logger.info("Updated core snapshot for %s (%s)", code, fund["schemeName"])
            else:
                logger.warning("Scheme %s not found in mutual_fund_core_snapshot", code)
        except Exception as exc:
            logger.error("Failed to update scheme %s: %s", code, exc)
            errors.append({"scheme_code": code, "error": str(exc)})

        # Mirror to legacy mutual_funds table where possible
        try:
            legacy_payload = {
                "category": fund["category"],
                "plan_type": fund["plan"],
                "option_type": fund["option"],
                "fund_house": fund["amcName"],
            }
            client.table("mutual_funds").update(legacy_payload).eq("scheme_code", int(code) if code.isdigit() else code).execute()
        except Exception:
            pass

    logger.info("Finished: %d/%d funds updated in mutual_fund_core_snapshot", updated, len(funds))
    return {"total": len(funds), "updated": updated, "errors": errors}


if __name__ == "__main__":
    result = populate_registry_metadata()
    print(json.dumps(result, indent=2))
