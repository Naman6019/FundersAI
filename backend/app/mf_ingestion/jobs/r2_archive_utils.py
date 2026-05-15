from __future__ import annotations

import gzip
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.database import supabase
from app.mf_ingestion.config import IngestionConfig
from app.mf_ingestion.storage.checksum import sha256_bytes
from app.mf_ingestion.storage.r2_store import R2Store

logger = logging.getLogger(__name__)


def encode_rows_as_archive(rows: list[dict[str, Any]]) -> tuple[bytes, str]:
    if not rows:
        return b"", "application/octet-stream"
    try:
        import pandas as pd  # type: ignore

        frame = pd.DataFrame(rows)
        with tempfile.NamedTemporaryFile(prefix="mf_archive_", suffix=".parquet", delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            frame.to_parquet(temp_path, index=False)
            return temp_path.read_bytes(), "application/vnd.apache.parquet"
        finally:
            temp_path.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Falling back to gzip JSON archive payload: %s", exc)
        encoded = gzip.compress("\n".join(json.dumps(row, default=str) for row in rows).encode("utf-8"))
        return encoded, "application/gzip"


def write_manifest(
    *,
    archive_kind: str,
    entity_key: str,
    report_month: str | None,
    bucket: str,
    key: str,
    row_count: int,
    content_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if not supabase:
        return
    checksum = sha256_bytes(json.dumps(payload or {}, default=str, sort_keys=True).encode("utf-8"))
    manifest = {
        "archive_kind": archive_kind,
        "entity_key": entity_key,
        "report_month": report_month,
        "storage_bucket": bucket,
        "storage_key": key,
        "row_count": row_count,
        "content_type": content_type,
        "checksum": checksum,
        "metadata": payload or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase.table("mf_r2_archive_manifests").upsert(
        manifest,
        on_conflict="archive_kind,entity_key,storage_key",
    ).execute()


def build_r2_store(config: IngestionConfig) -> R2Store:
    return R2Store(
        endpoint=config.r2_endpoint,
        access_key_id=config.r2_access_key_id,
        secret_access_key=config.r2_secret_access_key,
        raw_bucket=config.r2_raw_bucket,
        cold_bucket=config.r2_cold_bucket,
        signed_url_ttl_seconds=config.r2_signed_url_ttl_seconds,
    )
