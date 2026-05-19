from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.config import get_config
from app.mf_ingestion.jobs.r2_archive_utils import build_r2_store, encode_rows_as_archive, write_manifest
from app.mf_ingestion.storage.r2_store import build_safe_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-schemes", type=int, default=int(os.getenv("MF_NAV_COMPACT_SCHEME_LIMIT", "300")))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--scheme-source", choices=("core_snapshot", "old_nav_rows"), default="core_snapshot")
    args = parser.parse_args()

    if not supabase:
        logger.error("Supabase client not configured.")
        return

    config = get_config()
    r2_store = build_r2_store(config)
    if not r2_store.enabled:
        logger.error("R2 storage is not configured.")
        return

    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=365 * 5)).isoformat()
    scheme_codes = _load_target_scheme_codes(cutoff=cutoff, limit=max(args.limit_schemes, 1), source=args.scheme_source)

    processed = 0
    archived_rows = 0
    failed = 0
    for scheme_code in scheme_codes:
        try:
            scheme_archived_rows = 0
            prev_first_row = None
            while True:
                old_rows = (
                    supabase.table("mutual_fund_nav_history")
                    .select("scheme_code,nav_date,nav")
                    .eq("scheme_code", scheme_code)
                    .lt("nav_date", cutoff)
                    .order("nav_date", desc=False)
                    .limit(5000)
                    .execute()
                    .data
                    or []
                )
                if not old_rows:
                    break
                current_first_row = (old_rows[0].get("nav_date"), old_rows[0].get("nav"))
                if prev_first_row == current_first_row:
                    raise RuntimeError(
                        f"Infinite loop detected: deletion of rows for scheme {scheme_code} "
                        f"starting at date {current_first_row[0]} failed to progress."
                    )
                prev_first_row = current_first_row
                by_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for row in old_rows:
                    nav_date = str(row.get("nav_date") or "")
                    by_year[nav_date[:4] if len(nav_date) >= 4 else "unknown"].append(row)

                for year, rows in by_year.items():
                    encoded, content_type = encode_rows_as_archive(rows)
                    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    key = build_safe_key("cold", "nav", scheme_code, f"year={year}", f"part-{ts}.parquet")
                    if not args.dry_run:
                        r2_store.upload_bytes(
                            key=key,
                            content=encoded,
                            bucket=config.r2_cold_bucket,
                            content_type=content_type,
                            metadata={"archive_kind": "nav_5y_compaction", "scheme_code": scheme_code, "year": year},
                        )
                        write_manifest(
                            archive_kind="nav_5y_compaction",
                            entity_key=scheme_code,
                            report_month=_year_to_month(year),
                            bucket=config.r2_cold_bucket,
                            key=key,
                            row_count=len(rows),
                            content_type=content_type,
                            payload={"cutoff": cutoff, "year": year},
                        )
                scheme_archived_rows += len(old_rows)
                archived_rows += len(old_rows)

                if not args.dry_run:
                    min_date = str(old_rows[0].get("nav_date") or "")
                    max_date = str(old_rows[-1].get("nav_date") or "")
                    (
                        supabase.table("mutual_fund_nav_history")
                        .delete()
                        .eq("scheme_code", scheme_code)
                        .gte("nav_date", min_date)
                        .lte("nav_date", max_date)
                        .lt("nav_date", cutoff)
                        .execute()
                    )
                else:
                    # Dry-run does not delete rows; break to avoid re-reading the same batch forever.
                    break

            if scheme_archived_rows > 0:
                processed += 1
        except Exception as exc:
            failed += 1
            logger.error("NAV compaction failed for scheme=%s: %s", scheme_code, exc)

    logger.info(
        "compact_mf_nav_5y summary: schemes=%s archived_rows=%s failed=%s dry_run=%s cutoff=%s",
        processed,
        archived_rows,
        failed,
        args.dry_run,
        cutoff,
    )


def _year_to_month(year: str) -> str | None:
    try:
        parsed = int(year)
    except Exception:
        return None
    if parsed < 1900 or parsed > 2100:
        return None
    return date(parsed, 1, 1).isoformat()


def _load_target_scheme_codes(*, cutoff: str, limit: int, source: str) -> list[str]:
    if not supabase:
        return []

    if source == "core_snapshot":
        rows = (
            supabase.table("mutual_fund_core_snapshot")
            .select("scheme_code")
            .order("last_updated", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        return [str(row.get("scheme_code")) for row in rows if row.get("scheme_code")]

    # Old-row source fallback: paginate through old NAV rows ordered by scheme_code
    # so we collect many unique schemes instead of only the first few.
    seen: set[str] = set()
    ordered: list[str] = []
    page_size = min(max(limit * 20, 2000), 10000)
    max_scan_rows = max(limit * 400, 200000)
    offset = 0

    while offset < max_scan_rows and len(ordered) < limit:
        page = (
            supabase.table("mutual_fund_nav_history")
            .select("scheme_code")
            .lt("nav_date", cutoff)
            .order("scheme_code", desc=False)
            .range(offset, offset + page_size - 1)
            .execute()
            .data
            or []
        )
        if not page:
            break

        for row in page:
            scheme_code = str(row.get("scheme_code") or "").strip()
            if not scheme_code or scheme_code in seen:
                continue
            seen.add(scheme_code)
            ordered.append(scheme_code)
            if len(ordered) >= limit:
                break
        offset += page_size

    return ordered


if __name__ == "__main__":
    main()
