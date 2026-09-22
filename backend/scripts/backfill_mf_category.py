"""Backfill `mutual_fund_core_snapshot.category` from AMFI's NAVAll category headers.

`category` is NULL for most AMFI rows, and the public catalog gate requires it, so most schemes
could never pass the gate no matter how deep their NAV history was. The authoritative value is
already published by AMFI as a section header in NAVAll.txt; this fills the column from it.

What this does NOT do:

* It never overwrites an existing category. Three live published funds disagree with AMFI's
  current filing — SBI Contra, Quant Multi Cap and ICICI Prudential Value are live as "Flexi
  Cap" while AMFI now files them as Contra / Multi Cap / Value. Those replacement values are not
  in the catalog's accepted list, so writing them would set `is_published = false` and de-index
  pages that currently rank. A human-reviewed value is left alone.
* It never guesses. A scheme whose AMFI label is absent or unmapped is skipped and reported,
  which leaves its existing gate reason in place.
* It does not publish anything. Publication stays the catalog builder's decision, under its own
  gate.

Usage:
    python backend/scripts/backfill_mf_category.py --dry-run
    python backend/scripts/backfill_mf_category.py
    python backend/scripts/backfill_mf_category.py --limit 100
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

import requests
from supabase import create_client

from app.services.mf_category_service import parse_navall_categories, sebi_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

AMFI_URL = os.environ.get("AMFI_URL", "https://www.amfiindia.com/spages/NAVAll.txt")
PAGE_SIZE = 1000
WRITE_BATCH_SIZE = 200


def fetch_amfi_text() -> str:
    response = requests.get(AMFI_URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return response.content.decode("utf-8", errors="replace")


def load_core_rows(client) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        batch = (
            client.table("mutual_fund_core_snapshot")
            .select("scheme_code,category")
            .order("scheme_code")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
            .data
            or []
        )
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report without writing.")
    parser.add_argument("--limit", type=int, default=None, help="Cap the number of rows written.")
    args = parser.parse_args(argv)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")

    client = create_client(url, key)

    logger.info("Fetching AMFI NAVAll for category headers...")
    label_by_code = parse_navall_categories(fetch_amfi_text())
    logger.info("AMFI published a category for %s scheme codes.", len(label_by_code))

    core_rows = load_core_rows(client)
    logger.info("Loaded %s core snapshot rows.", len(core_rows))

    updates: list[dict] = []
    skipped_no_label = 0
    skipped_unmapped = 0
    already_set = 0

    for row in core_rows:
        if str(row.get("category") or "").strip():
            already_set += 1
            continue

        code = str(row.get("scheme_code"))
        label = label_by_code.get(code)
        if not label:
            skipped_no_label += 1
            continue

        value = sebi_category(label)
        if not value:
            skipped_unmapped += 1
            logger.warning("AMFI label not mapped for %s: %r", code, label)
            continue

        updates.append({"scheme_code": code, "category": value})

    if args.limit is not None:
        updates = updates[: args.limit]

    logger.info(
        "Planned updates=%s already_set=%s skipped_no_label=%s skipped_unmapped=%s",
        len(updates),
        already_set,
        skipped_no_label,
        skipped_unmapped,
    )
    for value, count in Counter(item["category"] for item in updates).most_common():
        logger.info("  %-40s %s", value, count)

    if args.dry_run:
        logger.info("Dry run: no rows written.")
        return 0

    written = 0
    for offset in range(0, len(updates), WRITE_BATCH_SIZE):
        batch = updates[offset : offset + WRITE_BATCH_SIZE]
        try:
            client.table("mutual_fund_core_snapshot").upsert(
                batch, on_conflict="scheme_code"
            ).execute()
            written += len(batch)
        except Exception as exc:  # noqa: BLE001 - reported and counted, never swallowed
            logger.error("Category update failed at offset %s: %s", offset, exc)

    logger.info("Wrote category for %s/%s rows.", written, len(updates))
    if written != len(updates):
        raise RuntimeError("Category backfill did not persist every batch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
