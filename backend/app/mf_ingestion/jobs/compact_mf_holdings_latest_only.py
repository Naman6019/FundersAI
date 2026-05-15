from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
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

AMC_DISCLOSURE_SOURCE = "amc_disclosure"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-groups", type=int, default=int(os.getenv("MF_HOLDINGS_COMPACT_GROUP_LIMIT", "1000")))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not supabase:
        logger.error("Supabase client not configured.")
        return

    config = get_config()
    r2_store = build_r2_store(config)
    if not r2_store.enabled:
        logger.error("R2 storage is not configured.")
        return

    rows = (
        supabase.table("mutual_fund_holdings")
        .select("*")
        .eq("source", AMC_DISCLOSURE_SOURCE)
        .order("updated_at", desc=False)
        .limit(max(args.limit_groups * 300, 5000))
        .execute()
        .data
        or []
    )
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        group_key = str(row.get("family_id") or f"scheme-{row.get('scheme_code')}")
        groups[group_key].append(row)

    processed = 0
    archived_rows = 0
    deleted_rows = 0
    failed = 0
    for group_key, group_rows in list(groups.items())[: max(args.limit_groups, 1)]:
        try:
            latest_date = max(str(row.get("as_of_date") or "") for row in group_rows)
            stale = [row for row in group_rows if str(row.get("as_of_date") or "") != latest_date]
            if not stale:
                continue
            payload, content_type = encode_rows_as_archive(stale)
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            report_month = latest_date[:7] if latest_date else "unknown-month"
            key = build_safe_key(
                "cold",
                "portfolio",
                group_key,
                f"report_month={report_month}",
                f"part-{ts}.parquet",
            )
            if not args.dry_run:
                r2_store.upload_bytes(
                    key=key,
                    content=payload,
                    bucket=config.r2_cold_bucket,
                    content_type=content_type,
                    metadata={"archive_kind": "holdings_latest_only", "group_key": group_key},
                )
                write_manifest(
                    archive_kind="holdings_latest_only",
                    entity_key=group_key,
                    report_month=_month_to_date(report_month),
                    bucket=config.r2_cold_bucket,
                    key=key,
                    row_count=len(stale),
                    content_type=content_type,
                    payload={"latest_date": latest_date},
                )
                for stale_date in sorted({str(row.get("as_of_date") or "") for row in stale if row.get("as_of_date")}):
                    delete_query = (
                        supabase.table("mutual_fund_holdings")
                        .delete()
                        .eq("source", AMC_DISCLOSURE_SOURCE)
                        .eq("as_of_date", stale_date)
                    )
                    family_id = group_rows[0].get("family_id")
                    if family_id not in (None, ""):
                        delete_query = delete_query.eq("family_id", str(family_id))
                    else:
                        delete_query = delete_query.eq("scheme_code", group_rows[0].get("scheme_code"))
                    delete_query.execute()
            processed += 1
            archived_rows += len(stale)
            deleted_rows += len(stale)
        except Exception as exc:
            failed += 1
            logger.error("Holdings compaction failed for group=%s: %s", group_key, exc)

    logger.info(
        "compact_mf_holdings_latest_only summary: groups=%s archived_rows=%s deleted_rows=%s failed=%s dry_run=%s",
        processed,
        archived_rows,
        deleted_rows,
        failed,
        args.dry_run,
    )


def _month_to_date(value: str) -> str | None:
    text = (value or "").strip()
    if len(text) != 7:
        return None
    return f"{text}-01"


if __name__ == "__main__":
    main()
