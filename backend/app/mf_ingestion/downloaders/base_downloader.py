from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os


def local_file_sources_allowed() -> bool:
    """Local `file://` documents are a LOCAL-DIAGNOSTIC-ONLY escape hatch.

    A `file://` candidate has no official host, no CDN evidence, and no reproducible
    provenance, so accepting one unconditionally would defeat the pipeline's first
    non-negotiable rule ("use only official AMC or AMFI sources") for every AMC, not
    just the one being tested. It is therefore opt-in per process and OFF by default,
    and must never be enabled in a hosted/CI run. Even when enabled, a locally sourced
    document still cannot be promoted: promotion independently requires R2-backed
    storage plus a matching checksum on an officially sourced row.

    This lives in the leaf downloader module rather than in `agents/validation.py` so
    both the validation policy and the HTTP layer can share it without importing
    `app.mf_ingestion.agents`, whose package `__init__` pulls in the discovery agent and
    would create an import cycle back through the downloader.
    """
    return str(os.getenv("MF_ALLOW_LOCAL_FILE_SOURCES", "")).strip().lower() in {
        "1",
        "true",
        "yes",
    }


@dataclass(frozen=True)
class DiscoveredDocument:
    amc_name: str
    amc_code: str
    document_type: str
    title: str
    url: str
    discovery_page_url: str
    file_ext: str
    report_month: date | None
    priority_score: int


@dataclass(frozen=True)
class DownloadedDocument:
    amc_name: str
    amc_code: str
    document_type: str
    source_url: str
    discovery_page_url: str
    file_name: str
    file_ext: str
    report_month: date | None
    content_type: str | None
    file_size_bytes: int
    file_bytes: bytes
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False


class BaseDownloader:
    def list_documents(self, document_type: str) -> list[DiscoveredDocument]:
        raise NotImplementedError

    def download(self, discovered: DiscoveredDocument) -> DownloadedDocument:
        raise NotImplementedError

    def probe_download(self, discovered: DiscoveredDocument, *, max_bytes: int = 65536) -> DownloadedDocument:
        """Return a bounded body probe when the downloader supports it."""
        return self.download(discovered)
