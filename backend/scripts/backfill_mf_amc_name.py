"""Backfill `mutual_fund_core_snapshot.amc_name` from the supported-AMC registry.

`amc_name` is NULL for most AMFI NAVAll rows. The disclosure parser, family
invariant propagation, and promotion conflict detection all key off the AMC, so
a NULL silently demotes every affected scheme to review.

This script writes the canonical registry label (`HDFC Mutual Fund`) for rows
whose scheme name resolves to a supported AMC through the shared marker map.
Rows for unsupported AMCs are left untouched. Only NULL/empty values are filled;
an existing label is never overwritten.

Usage:
    python backend/scripts/backfill_mf_amc_name.py --dry-run
    python backend/scripts/backfill_mf_amc_name.py
    python backend/scripts/backfill_mf_amc_name.py --limit 500
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

from supabase import create_client

from app.mf_ingestion.sources.registry import SOURCES
from app.services.supported_amcs import canonical_amc_label

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

PAGE_SIZE = 1000
WRITE_BATCH_SIZE = 200

# Canonical label written for each resolved AMC code.
_AMC_LABELS = {source.amc_code: source.amc_name for source in SOURCES.values()}


def _fetch_missing_rows(client) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page = (
            client.table("mutual_fund_core_snapshot")
            .select("scheme_code,scheme_name,amc_name")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
            .data
            or []
        )
        if not page:
            break
        rows.extend(row for row in page if not str(row.get("amc_name") or "").strip())
        offset += PAGE_SIZE
    return rows


def backfill(*, dry_run: bool = True, limit: int | None = None, output: str | None = None) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    missing = _fetch_missing_rows(client)
    logger.info("Rows with NULL/empty amc_name: %s", len(missing))

    resolved: list[tuple[str, str]] = []
    unmatched: list[dict] = []
    label_counts: dict[str, int] = {}

    for row in missing:
        scheme_code = str(row.get("scheme_code") or "").strip()
        if not scheme_code:
            continue
        code = canonical_amc_label(row.get("scheme_name"))
        label = _AMC_LABELS.get(code or "")
        if not code or not label:
            unmatched.append(row)
            continue
        resolved.append((scheme_code, label))
        label_counts[label] = label_counts.get(label, 0) + 1

    if limit is not None:
        resolved = resolved[:limit]

    logger.info("Resolvable: %s  Unmatched (left untouched): %s", len(resolved), len(unmatched))

    written = 0
    if not dry_run:
        for start in range(0, len(resolved), WRITE_BATCH_SIZE):
            batch = resolved[start : start + WRITE_BATCH_SIZE]
            for scheme_code, label in batch:
                client.table("mutual_fund_core_snapshot").update({"amc_name": label}).eq(
                    "scheme_code", scheme_code
                ).execute()
            written += len(batch)
            logger.info("Updated %s/%s", written, len(resolved))

    payload = {
        "status": "dry_run" if dry_run else "applied",
        "missing_amc_name": len(missing),
        "resolvable": len(resolved),
        "unmatched": len(unmatched),
        "written": written,
        "by_label": dict(sorted(label_counts.items(), key=lambda item: item[1], reverse=True)),
        "unmatched_samples": [
            {"scheme_code": str(row.get("scheme_code")), "scheme_name": row.get("scheme_name")}
            for row in unmatched[:25]
        ],
    }

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report without writing.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum rows to update.")
    parser.add_argument("--output", default="", help="Optional JSON report path.")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")

    payload = backfill(dry_run=args.dry_run, limit=args.limit, output=args.output or None)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
