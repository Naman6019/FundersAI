from __future__ import annotations

from dataclasses import dataclass
from datetime import date


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


class BaseDownloader:
    def list_documents(self, document_type: str) -> list[DiscoveredDocument]:
        raise NotImplementedError

    def download(self, discovered: DiscoveredDocument) -> DownloadedDocument:
        raise NotImplementedError

    def probe_download(self, discovered: DiscoveredDocument, *, max_bytes: int = 65536) -> DownloadedDocument:
        """Return a bounded body probe when the downloader supports it."""
        return self.download(discovered)
