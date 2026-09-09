"""
Standalone AMFI Mutual Fund NAV Sync script for GitHub Actions.
Downloads the full NAVAll.txt from AMFI and upserts to Supabase.
"""
import os
import argparse
import logging
import re
import requests
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
BATCH_SIZE = 500

_FAMILY_REMOVABLE_SUFFIXES = {
    "direct",
    "regular",
    "retail",
    "growth",
    "cumulative",
    "idcw",
    "dividend",
    "reinvestment",
    "payout",
    "payment",
    "institutional",
    "bonus",
    "option",
    "plan",
}


def _is_supported_scheme_name(
    scheme_name: str,
    plan: str = "",
    option: str = "",
) -> bool:
    """Keep direct-growth variants plus planless ETFs from AMFI NAVAll.

    AMFI's current semicolon feed puts the plan and option in their own
    columns. Legacy pipe rows keep them in the scheme name, so inspect all
    three fields rather than silently dropping current-format direct plans.
    """
    normalized_name = str(scheme_name or "").strip().lower()
    normalized_variant = " ".join(
        value.strip().lower() for value in (scheme_name, plan, option) if value
    )
    is_direct_growth = "direct" in normalized_variant and (
        "growth" in normalized_variant or "cumulative" in normalized_variant
    )
    return is_direct_growth or bool(re.search(r"\betf\b", normalized_name))


def _infer_amc_name(scheme_name: str) -> str | None:
    """Restore the canonical AMC label for planless AMFI ETF rows."""
    normalized = str(scheme_name or "").strip().lower()
    if normalized.startswith("edelweiss "):
        return "Edelweiss Mutual Fund"
    return None


def _canonical_scheme_name(scheme_name: str, plan: str = "", option: str = "") -> str:
    """Retain AMFI's plan and option when the current feed separates them."""
    parts = [str(value or "").strip() for value in (scheme_name, plan, option)]
    return " - ".join(part for part in parts if part)


def _auto_family_id(scheme_name: str) -> str:
    """Build the same stable family slug used by the existing auto-group script."""
    normalized = str(scheme_name or "").strip().lower()
    normalized = normalized.replace("smallcap", "small cap")
    normalized = normalized.replace("midcap", "mid cap")
    normalized = normalized.replace("largecap", "large cap")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    tokens = normalized.split()
    while len(tokens) > 1 and tokens[-1] in _FAMILY_REMOVABLE_SUFFIXES:
        tokens.pop()
    return "-".join(tokens)


def parse_amfi_nav_payload(payload: str) -> list[dict]:
    """Parse AMFI's six-column fund rows and eight-column ETF rows."""
    updates = []
    for line in str(payload or "").splitlines():
        trimmed = line.strip().lstrip("\ufeff")
        if not trimmed:
            continue

        delimiter = "|" if "|" in trimmed else ";"
        cols = [value.strip() for value in trimmed.split(delimiter)]
        if len(cols) < 6:
            continue
        try:
            scheme_code = int(cols[0])
            base_scheme_name = cols[3]
            nav = float(cols[-2])
            date_str = cols[-1]
        except (ValueError, IndexError):
            continue

        # Current NAVAll uses eight semicolon columns (name, plan, option),
        # while the legacy pipe format embeds plan and option in the name.
        plan = cols[4] if len(cols) >= 8 else ""
        option = cols[5] if len(cols) >= 8 else ""
        if not _is_supported_scheme_name(base_scheme_name, plan, option):
            continue
        scheme_name = _canonical_scheme_name(base_scheme_name, plan, option)

        isin = next(
            (cols[index] for index in (1, 2) if index < len(cols) and cols[index] not in {"", "-"}),
            None,
        )
        try:
            nav_date = datetime.strptime(date_str, "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            # A malformed official row must never acquire a fabricated "today"
            # date. Skipping it keeps the reconciliation gate honest.
            logger.warning("Skipping AMFI NAV row with invalid date for scheme %s: %r", scheme_code, date_str)
            continue

        updates.append(
            {
                "scheme_code": scheme_code,
                "scheme_name": scheme_name,
                "isin": isin,
                "nav": nav,
                "nav_date": nav_date,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **(
                    {"amc_name": amc_name}
                    if (amc_name := _infer_amc_name(scheme_name))
                    else {}
                ),
            }
        )
    return updates

def fetch_amfi_nav():
    """
    Downloads NAVAll.txt with retries and exponential backoff.
    Parses AMFI's semicolon-delimited fund rows and ETF rows.
    """
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        logger.info(f"Fetching AMFI NAV data from {AMFI_URL}...")
        response = session.get(AMFI_URL, timeout=30)
        response.raise_for_status()
        
        # Handle encoding issues
        return parse_amfi_nav_payload(response.content.decode("utf-8", errors="replace"))
    except Exception as e:
        logger.error(f"Failed to fetch AMFI NAV: {e}")
        return []


def _load_existing_core_rows(supabase, batch: list[dict]) -> dict[str, dict]:
    codes = [str(row.get("scheme_code")) for row in batch if row.get("scheme_code") is not None]
    if not codes:
        return {}
    try:
        res = (
            supabase.table("mutual_fund_core_snapshot")
            .select("scheme_code,amc_name,data_source,provider_payload")
            .in_("scheme_code", codes)
            .execute()
        )
    except Exception as exc:
        logger.warning("Existing MF core lookup failed before AMFI NAV upsert: %s", exc)
        return {}
    return {str(row.get("scheme_code")): row for row in (res.data or []) if row.get("scheme_code") is not None}


def _load_existing_family_mappings(supabase, batch: list[dict]) -> dict[str, dict]:
    codes = [str(row.get("scheme_code")) for row in batch if row.get("scheme_code") is not None]
    if not codes:
        return {}
    try:
        res = (
            supabase.table("mutual_fund_family_mapping")
            .select("scheme_code,family_id")
            .in_("scheme_code", codes)
            .execute()
        )
    except Exception as exc:
        logger.warning("Existing MF family mapping lookup failed: %s", exc)
        return {}
    return {str(row.get("scheme_code")): row for row in (res.data or []) if row.get("scheme_code") is not None}


def _build_missing_etf_family_mappings(
    batch: list[dict], existing: dict[str, dict]
) -> list[dict]:
    mappings = []
    for row in batch:
        code = str(row.get("scheme_code") or "")
        name = str(row.get("scheme_name") or "")
        if code in existing or not re.search(r"\betf\b", name, flags=re.IGNORECASE):
            continue
        family_id = _auto_family_id(name)
        if not family_id:
            continue
        mappings.append(
            {
                "scheme_code": code,
                "family_id": family_id,
                "confidence": 0.9,
                "source": "amfi-navall-etf-v1",
            }
        )
    return mappings


def _merge_sources(*values: object) -> str:
    ordered: list[str] = []
    for value in values:
        for part in str(value or "").split("+"):
            clean = part.strip()
            if clean and clean not in ordered:
                ordered.append(clean)
    return "+".join(ordered)


def _build_core_snapshot_row(update: dict, existing: dict | None = None) -> dict:
    existing = existing or {}
    row = {
        "scheme_code": str(update["scheme_code"]),
        "scheme_name": update["scheme_name"],
        "nav": update["nav"],
        "nav_date": update["nav_date"],
        "data_source": _merge_sources(existing.get("data_source"), "amfi_navall"),
        "provider_payload": existing.get("provider_payload"),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    amc_name = existing.get("amc_name") or update.get("amc_name")
    if amc_name:
        row["amc_name"] = amc_name
    return row


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Sync AMFI NAVAll into the mutual-fund snapshots.")
    parser.add_argument(
        "--nav-only",
        action="store_true",
        help="Skip ETF family-mapping creation; use for the daily NAV reliability job.",
    )
    args = parser.parse_args(argv)
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    updates = fetch_amfi_nav()
    if not updates:
        raise RuntimeError("AMFI NAV feed returned no supported scheme updates.")

    logger.info(f"Parsed {len(updates)} fund schemes.")

    success = 0
    failed_batch_offsets: list[int] = []
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i:i + BATCH_SIZE]
        try:
            existing_core = _load_existing_core_rows(supabase, batch)
            # 1. Update main table
            mutual_fund_batch = [
                {key: value for key, value in row.items() if key != "amc_name"}
                for row in batch
            ]
            supabase.table('mutual_funds').upsert(
                mutual_fund_batch,
                on_conflict='scheme_code',
            ).execute()

            # 2. Keep latest NAV and core snapshot aligned. Full history is cached on demand.
            core_snapshot_batch = [
                _build_core_snapshot_row(u, existing_core.get(str(u["scheme_code"])))
                for u in batch
            ]
            supabase.table('mutual_fund_core_snapshot').upsert(core_snapshot_batch, on_conflict='scheme_code').execute()

            if not args.nav_only:
                # ETF identities have no Direct Growth suffix; create only missing
                # mappings so reviewed mappings for existing schemes are untouched.
                existing_mappings = _load_existing_family_mappings(supabase, batch)
                missing_mappings = _build_missing_etf_family_mappings(batch, existing_mappings)
                if missing_mappings:
                    supabase.table("mutual_fund_family_mapping").upsert(
                        missing_mappings, on_conflict="scheme_code"
                    ).execute()
            
            success += len(batch)
            logger.info(f"Upserted batch {i//BATCH_SIZE + 1}: {success}/{len(updates)} schemes done.")
        except Exception as e:
            logger.error(f"Batch upsert failed at offset {i}: {e}")
            failed_batch_offsets.append(i)

    logger.info(f"Finished. {success}/{len(updates)} schemes synced to Supabase.")
    if failed_batch_offsets:
        raise RuntimeError(
            "AMFI NAV sync did not persist every batch; failed offsets: "
            + ", ".join(str(offset) for offset in failed_batch_offsets)
        )

if __name__ == "__main__":
    main()
