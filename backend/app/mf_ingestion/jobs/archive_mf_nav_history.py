from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.config import get_config
from app.mf_ingestion.jobs.r2_archive_utils import build_r2_store, encode_rows_as_archive, write_manifest
from app.mf_ingestion.storage.checksum import sha256_bytes
from app.mf_ingestion.storage.r2_store import build_safe_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _archive_group(
    *,
    rows: list[dict[str, Any]],
    scheme_code: str,
    year: str,
    run_id: str,
    store: Any,
    bucket: str,
    verify: bool,
) -> dict[str, Any]:
    encoded, content_type = encode_rows_as_archive(rows)
    checksum = sha256_bytes(encoded)
    suffix = "parquet" if content_type == "application/vnd.apache.parquet" else "jsonl.gz"
    key = build_safe_key("cold", "nav-history", f"scheme={scheme_code}", f"year={year}", f"archive-{run_id}.{suffix}")
    store.upload_bytes(
        key=key,
        content=encoded,
        bucket=bucket,
        content_type=content_type,
        metadata={
            "archive_kind": "nav_history_full",
            "scheme_code": scheme_code,
            "year": year,
            "checksum": checksum,
        },
    )
    exists = store.object_exists(key, bucket=bucket) if verify else True
    if not exists:
        raise RuntimeError(f"archive_object_missing:{key}")
    write_manifest(
        archive_kind="nav_history_full",
        entity_key=scheme_code,
        report_month=f"{year}-01-01" if year.isdigit() else None,
        bucket=bucket,
        key=key,
        row_count=len(rows),
        content_type=content_type,
        checksum=checksum,
        payload={"scheme_code": scheme_code, "year": year, "archive_run_id": run_id},
    )
    return {
        "scheme_code": scheme_code,
        "year": year,
        "row_count": len(rows),
        "object_key": key,
        "checksum": checksum,
        "object_exists": exists,
    }


def run_archive(*, page_size: int, verify: bool) -> dict[str, Any]:
    if not supabase:
        raise RuntimeError("supabase_not_configured")
    config = get_config()
    store = build_r2_store(config)
    if not store.enabled or not config.r2_cold_bucket:
        raise RuntimeError("r2_not_configured")

    page_size = max(1, min(page_size, 5000))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    offset = 0
    database_count: int | None = None
    scanned_count = 0
    archived_count = 0
    failures: list[str] = []
    manifests: list[dict[str, Any]] = []
    group_key: tuple[str, str] | None = None
    group_rows: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal archived_count, group_rows
        if not group_key or not group_rows:
            return
        scheme_code, year = group_key
        manifest = _archive_group(
            rows=group_rows,
            scheme_code=scheme_code,
            year=year,
            run_id=run_id,
            store=store,
            bucket=config.r2_cold_bucket,
            verify=verify,
        )
        manifests.append(manifest)
        archived_count += len(group_rows)
        group_rows = []

    while True:
        query = (
            supabase.table("mutual_fund_nav_history")
            .select("scheme_code,nav_date,nav", count="exact" if offset == 0 else None)
            .order("scheme_code", desc=False)
            .order("nav_date", desc=False)
            .range(offset, offset + page_size - 1)
        )
        response = query.execute()
        if offset == 0:
            database_count = int(response.count or 0)
        rows = response.data or []
        if not rows:
            break
        for row in rows:
            scheme_code = str(row.get("scheme_code") or "").strip()
            nav_date = str(row.get("nav_date") or "")
            year = nav_date[:4] if len(nav_date) >= 4 else "unknown"
            next_key = (scheme_code, year)
            if not scheme_code:
                failures.append("row_missing_scheme_code")
                continue
            if group_key is not None and next_key != group_key:
                try:
                    flush()
                except Exception as exc:
                    failures.append(f"{group_key[0]}:{group_key[1]}:{exc}")
                    group_rows = []
            group_key = next_key
            group_rows.append(row)
            scanned_count += 1
        offset += len(rows)
        if len(rows) < page_size:
            break

    try:
        flush()
    except Exception as exc:
        key = group_key or ("unknown", "unknown")
        failures.append(f"{key[0]}:{key[1]}:{exc}")

    count_matches = database_count is not None and database_count == scanned_count == archived_count
    if not count_matches:
        failures.append(
            f"row_count_mismatch:database={database_count}:scanned={scanned_count}:archived={archived_count}"
        )
    return {
        "archive_run_id": run_id,
        "database_row_count": database_count,
        "scanned_row_count": scanned_count,
        "archived_row_count": archived_count,
        "object_count": len(manifests),
        "count_matches": count_matches,
        "verified_objects": verify,
        "failures": failures,
        "manifests": manifests,
        "archive_verified": count_matches and not failures and all(item["object_exists"] for item in manifests),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive all legacy NAV history without deleting database rows.")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--report-output", default="nav-history-archive-report.json")
    args = parser.parse_args()
    report = run_archive(page_size=args.page_size, verify=args.verify)
    Path(args.report_output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info(
        "NAV archive rows=%s objects=%s failures=%s archive_verified=%s",
        report["archived_row_count"],
        report["object_count"],
        len(report["failures"]),
        report["archive_verified"],
    )
    return 0 if report["archive_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
