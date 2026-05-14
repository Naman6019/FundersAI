from __future__ import annotations

import logging
from pathlib import Path

from app.mf_ingestion.downloaders.base_downloader import BaseDownloader, DiscoveredDocument, DownloadedDocument
from app.mf_ingestion.parsers.adapters.ppfas_adapter import PPFASAdapter
from app.mf_ingestion.sources.registry import AMCDocumentSource

logger = logging.getLogger(__name__)


class AMCDownloader(BaseDownloader):
    def __init__(self, source: AMCDocumentSource, timeout_seconds: float, user_agent: str) -> None:
        self.source = source
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def list_documents(self, document_type: str) -> list[DiscoveredDocument]:
        adapter_key = (self.source.adapter_key or "").lower()
        if adapter_key == "ppfas":
            adapter = PPFASAdapter(user_agent=self.user_agent, timeout_seconds=int(self.timeout_seconds))
            docs = adapter.discover_documents(self.source, document_type=document_type)
            logger.info(
                "event=amc_discovery_complete amc_code=%s adapter=%s document_type=%s count=%s",
                self.source.amc_code,
                adapter_key,
                document_type,
                len(docs),
            )
            return docs

        raise NotImplementedError(f"No discovery adapter configured for adapter_key={adapter_key}")

    def download(self, discovered: DiscoveredDocument) -> DownloadedDocument:
        adapter_key = (self.source.adapter_key or "").lower()
        if adapter_key != "ppfas":
            raise NotImplementedError(f"No downloader configured for adapter_key={adapter_key}")

        adapter = PPFASAdapter(user_agent=self.user_agent, timeout_seconds=int(self.timeout_seconds))
        response = adapter.download_document(discovered.url)
        file_name = _derive_file_name(discovered.url, discovered.title)
        return DownloadedDocument(
            amc_name=discovered.amc_name,
            amc_code=discovered.amc_code,
            document_type=discovered.document_type,
            source_url=discovered.url,
            discovery_page_url=discovered.discovery_page_url,
            file_name=file_name,
            file_ext=discovered.file_ext,
            report_month=discovered.report_month,
            content_type=response.headers.get("Content-Type"),
            file_size_bytes=len(response.content),
            file_bytes=response.content,
        )


def _derive_file_name(url: str, fallback_title: str) -> str:
    path = Path(url.split("?", 1)[0])
    name = path.name.strip()
    if name:
        return name

    safe = "_".join((fallback_title or "document").split())
    return safe or "document"
