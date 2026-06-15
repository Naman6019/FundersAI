from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.repositories.mf_ingestion_repository import MfIngestionRepository
from app.mf_ingestion.config import get_config
from app.mf_ingestion.storage.r2_store import R2Store, build_safe_key

router = APIRouter(prefix="/api/internal/mf", tags=["mf-ingestion"])


def get_mf_ingestion_repository() -> MfIngestionRepository:
    return MfIngestionRepository()


@router.get("/schemes/{scheme_name}/holdings")
def get_scheme_holdings(
    scheme_name: str,
    report_month: str | None = Query(default=None, description="YYYY-MM-01"),
    limit: int = Query(default=250, ge=1, le=5000),
    repository: MfIngestionRepository = Depends(get_mf_ingestion_repository),
):
    if not repository:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    normalized = scheme_name.strip().lower()
    scheme = repository.get_scheme_by_normalized_name(normalized)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    rows = repository.get_scheme_holdings(scheme["id"], report_month=report_month, limit=limit)
    return {
        "scheme": scheme,
        "report_month": report_month,
        "holdings": rows,
        "count": len(rows),
    }


@router.get("/documents/{source_document_id}/signed-url")
def get_document_signed_url(
    source_document_id: str,
    artifact: str = Query(default="raw", pattern="^(raw|debug)$"),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    repository: MfIngestionRepository = Depends(get_mf_ingestion_repository),
):
    expected_admin_key = os.getenv("MF_INTERNAL_ADMIN_KEY", "").strip()
    if not expected_admin_key or x_admin_key != expected_admin_key:
        raise HTTPException(status_code=403, detail="admin_auth_required")
    if not repository:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    config = get_config()
    r2_store = R2Store(
        endpoint=config.r2_endpoint,
        access_key_id=config.r2_access_key_id,
        secret_access_key=config.r2_secret_access_key,
        raw_bucket=config.r2_raw_bucket,
        cold_bucket=config.r2_cold_bucket,
        signed_url_ttl_seconds=config.r2_signed_url_ttl_seconds,
    )
    if not r2_store.enabled:
        raise HTTPException(status_code=500, detail="r2_not_configured")

    row = repository.get_raw_document_storage(source_document_id)
    if not row:
        raise HTTPException(status_code=404, detail="source_document_not_found")

    if artifact == "raw":
        if str(row.get("storage_backend") or "").strip().lower() != "r2" or not row.get("storage_key"):
            raise HTTPException(status_code=404, detail="raw_r2_object_not_found")
        key = build_safe_key(str(row["storage_key"]))
        bucket = str(row.get("storage_bucket") or config.r2_raw_bucket)
    else:
        month_segment = str(row.get("report_month") or "")[:7] or "unknown-month"
        key = build_safe_key(
            "debug",
            str(row.get("amc_code") or "unknown"),
            month_segment,
            source_document_id,
            "holdings_parse_summary.json.gz",
        )
        bucket = config.r2_cold_bucket

    if not r2_store.object_exists(key, bucket=bucket):
        raise HTTPException(status_code=404, detail="r2_object_not_found")

    signed_url = r2_store.generate_signed_url(
        key=key,
        bucket=bucket,
        expires_seconds=config.r2_signed_url_ttl_seconds,
    )
    return {
        "source_document_id": source_document_id,
        "artifact": artifact,
        "bucket": bucket,
        "key": key,
        "signed_url": signed_url,
        "expires_in_seconds": config.r2_signed_url_ttl_seconds,
    }
