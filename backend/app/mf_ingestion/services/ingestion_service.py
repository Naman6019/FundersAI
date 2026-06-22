from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.database import supabase
from app.mf_ingestion.config import get_config
from app.mf_ingestion.downloaders.amc_downloader import AMCDownloader
from app.mf_ingestion.sources.registry import AMCDocumentSource, get_source
from app.mf_ingestion.storage.checksum import sha256_bytes
from app.mf_ingestion.storage.raw_file_store import RawFileStore
from app.mf_ingestion.storage.r2_store import R2Store, build_safe_key
from app.mf_ingestion.services.source_manifest import build_source_manifest, load_source_manifest_documents

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self) -> None:
        self.config = get_config()
        self.raw_store = RawFileStore(self.config.raw_storage_root)
        self.r2_store = R2Store(
            endpoint=self.config.r2_endpoint,
            access_key_id=self.config.r2_access_key_id,
            secret_access_key=self.config.r2_secret_access_key,
            raw_bucket=self.config.r2_raw_bucket,
            cold_bucket=self.config.r2_cold_bucket,
            signed_url_ttl_seconds=self.config.r2_signed_url_ttl_seconds,
        )

    def ingest_latest_amc_document(self, amc: str, document_type: str, max_documents: int = 1) -> dict[str, Any]:
        result = self.ingest_documents(amc=amc, document_type=document_type, max_documents=max_documents)
        if result.get("ingested_documents"):
            return result["ingested_documents"][0]
        if result.get("skipped_documents"):
            return result["skipped_documents"][0]
        return {"status": "skipped", "reason": result.get("reason", "no_documents_processed")}

    def ingest_documents(self, amc: str, document_type: str, max_documents: int = 1) -> dict[str, Any]:
        source = get_source(amc)
        if not source.enabled:
            return {"status": "skipped", "reason": f"{amc}_source_not_enabled"}
        if not supabase:
            return {"status": "error", "reason": "supabase_not_configured"}
        if self.config.require_r2_for_raw_storage and not self.r2_store.enabled:
            return {"status": "error", "reason": "r2_required_for_raw_storage"}

        self._upsert_source_row(source)

        downloader = AMCDownloader(source, self.config.request_timeout_seconds, self.config.user_agent)
        manifest_docs = load_source_manifest_documents(self.config.source_manifest_path, source, document_type)
        try:
            discovered_docs = _dedupe_discovered_documents(
                [*manifest_docs, *downloader.list_documents(document_type=document_type)]
            )
        except Exception as exc:
            if manifest_docs:
                logger.warning(
                    "event=amc_discovery_failed_using_manifest amc_code=%s document_type=%s manifest_count=%s reason=%s",
                    source.amc_code,
                    document_type,
                    len(manifest_docs),
                    exc,
                )
                discovered_docs = manifest_docs
            else:
                logger.error(
                    "event=amc_discovery_failed amc_code=%s document_type=%s reason=%s",
                    source.amc_code,
                    document_type,
                    exc,
                )
                return {"status": "error", "reason": str(exc)}

        if not discovered_docs:
            logger.error(
                "event=amc_discovery_empty amc_code=%s document_type=%s manifest_count=%s",
                source.amc_code,
                document_type,
                len(manifest_docs),
            )
            return {"status": "skipped", "reason": "no_documents_found", "document_type": document_type}

        selected = discovered_docs[: max(max_documents, 1)]
        ingested: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        for discovered in selected:
            try:
                downloaded = downloader.download(discovered)
                logger.info(
                    "event=file_downloaded amc_code=%s document_type=%s source_url=%s",
                    downloaded.amc_code,
                    downloaded.document_type,
                    downloaded.source_url,
                )
            except Exception as exc:
                logger.error(
                    "event=file_download_failed amc_code=%s document_type=%s source_url=%s reason=%s",
                    source.amc_code,
                    document_type,
                    discovered.url,
                    exc,
                )
                skipped.append(
                    {
                        "status": "error",
                        "reason": str(exc),
                        "source_url": discovered.url,
                        "document_type": document_type,
                    }
                )
                continue

            checksum = sha256_bytes(downloaded.file_bytes)
            duplicate = (
                supabase.table("mf_raw_documents")
                .select("id")
                .eq("checksum", checksum)
                .limit(1)
                .execute()
            )
            if duplicate.data:
                logger.info(
                    "event=duplicate_checksum_skipped amc_code=%s document_type=%s checksum=%s",
                    downloaded.amc_code,
                    downloaded.document_type,
                    checksum,
                )
                skipped.append(
                    {
                        "status": "skipped",
                        "reason": "duplicate_checksum",
                        "source_document_id": duplicate.data[0]["id"],
                        "source_url": downloaded.source_url,
                        "document_type": downloaded.document_type,
                    }
                )
                continue

            raw_path, storage_backend, storage_bucket, storage_key, storage_metadata = self._persist_raw_document(
                downloaded=downloaded,
                checksum=checksum,
            )
            storage_metadata["source_manifest"] = build_source_manifest(
                source=source,
                document_type=downloaded.document_type,
                source_url=downloaded.source_url,
                discovery_page_url=downloaded.discovery_page_url,
                report_month=downloaded.report_month,
                expected_file_type=downloaded.file_ext or downloaded.file_name,
                checksum=checksum,
                acquisition_status="acquired",
            )
            now_iso = datetime.now(timezone.utc).isoformat()
            payload = {
                "amc_name": downloaded.amc_name,
                "amc_code": downloaded.amc_code,
                "document_type": downloaded.document_type,
                "source_document_type": downloaded.document_type,
                "report_month": downloaded.report_month.isoformat() if downloaded.report_month else None,
                "source_url": downloaded.source_url,
                "discovery_page_url": downloaded.discovery_page_url,
                "file_name": downloaded.file_name,
                "file_ext": downloaded.file_ext,
                "storage_path": raw_path,
                "storage_backend": storage_backend,
                "storage_bucket": storage_bucket,
                "storage_key": storage_key,
                "storage_metadata": storage_metadata,
                "checksum": checksum,
                "content_type": downloaded.content_type,
                "file_size_bytes": downloaded.file_size_bytes,
                "parse_status": "pending",
                "downloaded_at": now_iso,
                "parser_version": self.config.parser_version,
            }
            inserted = supabase.table("mf_raw_documents").insert(payload).execute()
            source_document_id = str((inserted.data or [{}])[0].get("id") or "")
            logger.info(
                "event=raw_document_inserted amc_code=%s document_type=%s source_document_id=%s",
                downloaded.amc_code,
                downloaded.document_type,
                source_document_id,
            )

            ingested.append(
                {
                    "status": "ingested",
                    "source_document_id": source_document_id,
                    "checksum": checksum,
                    "source_url": downloaded.source_url,
                    "discovery_page_url": downloaded.discovery_page_url,
                    "document_type": downloaded.document_type,
                    "report_month": payload["report_month"],
                }
            )

        return {
            "status": "ok",
            "document_type": document_type,
            "ingested_documents": ingested,
            "skipped_documents": skipped,
        }

    def _upsert_source_row(self, source: AMCDocumentSource) -> None:
        payload = {
            "amc_name": source.amc_name,
            "amc_code": source.amc_code,
            "listing_url": source.factsheet_page_url or source.portfolio_disclosure_page_url,
            "base_url": _base_url_from_pages(source),
            "adapter_key": source.adapter_key,
            "factsheet_page_url": source.factsheet_page_url,
            "portfolio_disclosure_page_url": source.portfolio_disclosure_page_url,
            "requires_confirmation": source.requires_confirmation,
            "confirmation_type": source.confirmation_type,
            "confirmation_notes": source.confirmation_notes,
            "is_enabled": source.enabled,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("mf_amc_sources").upsert(payload, on_conflict="amc_code").execute()

    def _persist_raw_document(
        self,
        *,
        downloaded: Any,
        checksum: str,
    ) -> tuple[str, str, str | None, str | None, dict[str, Any]]:
        metadata = {
            "checksum": checksum,
            "content_type": downloaded.content_type or "",
            "file_size_bytes": str(downloaded.file_size_bytes or 0),
        }

        ext = downloaded.file_ext or _safe_extension(downloaded.file_name)
        if not ext.startswith("."):
            ext = f".{ext}"
        month_segment = downloaded.report_month.strftime("%Y-%m") if downloaded.report_month else "unknown-month"
        key = build_safe_key(
            "raw",
            downloaded.amc_code,
            month_segment,
            downloaded.document_type,
            f"{checksum}{ext.lower()}",
        )

        if self.r2_store.enabled:
            uploaded = self.r2_store.upload_bytes(
                key=key,
                content=downloaded.file_bytes,
                bucket=self.config.r2_raw_bucket,
                content_type=downloaded.content_type,
                metadata={k: str(v) for k, v in metadata.items()},
            )
            storage_path = f"r2://{uploaded['bucket']}/{uploaded['key']}"
            return storage_path, "r2", uploaded["bucket"], uploaded["key"], metadata

        if self.config.require_r2_for_raw_storage:
            raise RuntimeError("r2_required_for_raw_storage")

        local_path = self.raw_store.save(downloaded, checksum)
        return str(Path(local_path).resolve()), "local", None, None, metadata


def _base_url_from_pages(source: AMCDocumentSource) -> str | None:
    page = source.factsheet_page_url or source.portfolio_disclosure_page_url
    if not page:
        return None
    parsed = urlparse(page)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _safe_extension(file_name: str) -> str:
    if "." not in file_name:
        return ".bin"
    return "." + file_name.rsplit(".", 1)[-1].lower()


def _dedupe_discovered_documents(documents: list[Any]) -> list[Any]:
    deduped: list[Any] = []
    seen: set[str] = set()
    for document in documents:
        url = str(getattr(document, "url", "") or "").strip()
        key = url.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(document)
    return deduped
