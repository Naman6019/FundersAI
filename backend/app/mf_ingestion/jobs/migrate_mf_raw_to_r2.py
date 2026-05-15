from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.config import get_config
from app.mf_ingestion.jobs.r2_archive_utils import build_r2_store
from app.mf_ingestion.storage.r2_store import build_safe_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=int(os.getenv("MF_R2_MIGRATION_LIMIT", "200")))
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
        supabase.table("mf_raw_documents")
        .select("id,amc_code,document_type,file_ext,file_name,report_month,checksum,content_type,file_size_bytes,storage_path,storage_backend,storage_bucket,storage_key")
        .neq("storage_backend", "r2")
        .order("downloaded_at", desc=False)
        .limit(max(args.limit, 1))
        .execute()
        .data
        or []
    )
    migrated = 0
    skipped = 0
    failed = 0

    for row in rows:
        try:
            local_path = Path(str(row.get("storage_path") or ""))
            if not local_path.exists():
                skipped += 1
                continue

            checksum = str(row.get("checksum") or "")
            ext = str(row.get("file_ext") or "") or _safe_extension(str(row.get("file_name") or ""))
            if not ext.startswith("."):
                ext = f".{ext}"
            report_month = str(row.get("report_month") or "")[:7] or "unknown-month"
            key = build_safe_key(
                "raw",
                str(row.get("amc_code") or "unknown"),
                report_month,
                str(row.get("document_type") or "unknown"),
                f"{checksum}{ext.lower()}",
            )
            exists = r2_store.object_exists(key, bucket=config.r2_raw_bucket)
            if not exists and not args.dry_run:
                r2_store.upload_file(
                    key=key,
                    file_path=local_path,
                    bucket=config.r2_raw_bucket,
                    content_type=str(row.get("content_type") or None),
                    metadata={
                        "checksum": checksum,
                        "file_size_bytes": str(row.get("file_size_bytes") or ""),
                    },
                )
            if not args.dry_run:
                supabase.table("mf_raw_documents").update(
                    {
                        "storage_backend": "r2",
                        "storage_bucket": config.r2_raw_bucket,
                        "storage_key": key,
                        "storage_metadata": {
                            "checksum": checksum,
                            "content_type": row.get("content_type"),
                            "file_size_bytes": row.get("file_size_bytes"),
                        },
                    }
                ).eq("id", row["id"]).execute()
            migrated += 1
        except Exception as exc:
            failed += 1
            logger.error("Raw document migration failed for id=%s: %s", row.get("id"), exc)

    logger.info(
        "migrate_mf_raw_to_r2 summary: scanned=%s migrated=%s skipped=%s failed=%s dry_run=%s",
        len(rows),
        migrated,
        skipped,
        failed,
        args.dry_run,
    )


def _safe_extension(file_name: str) -> str:
    if "." not in file_name:
        return ".bin"
    return "." + file_name.rsplit(".", 1)[-1].lower()


if __name__ == "__main__":
    main()
