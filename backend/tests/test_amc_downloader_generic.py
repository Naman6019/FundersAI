from __future__ import annotations

from datetime import date

import pytest

from app.mf_ingestion.downloaders.amc_downloader import AMCDownloader
from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.sources.registry import AMCDocumentSource


class _FakeResponse:
    def __init__(self, *, url: str, text: str = "", content: bytes = b"", headers: dict | None = None) -> None:
        self.url = url
        self.text = text
        self.content = content
        self.headers = headers or {}
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None


def test_hdfc_generic_discovery_parses_anchor_documents(monkeypatch):
    html = """
    <html><body>
      <a href="/downloads/HDFC-FlexiCap-Factsheet-Apr-2026.pdf">Factsheet Apr 2026</a>
      <a href="/downloads/HDFC-Portfolio-Apr-2026.xlsx">Portfolio Disclosure Apr 2026</a>
    </body></html>
    """

    def fake_get(url, timeout=None, headers=None, **kwargs):  # noqa: ANN001
        return _FakeResponse(url="https://www.hdfcfund.com/downloads", text=html, headers={"Content-Type": "text/html"})

    monkeypatch.setattr("app.mf_ingestion.downloaders.amc_downloader.requests.get", fake_get)

    source = AMCDocumentSource(
        amc_name="HDFC Mutual Fund",
        amc_code="HDFC",
        adapter_key="hdfc",
        factsheet_page_url="https://www.hdfcfund.com/downloads",
        portfolio_disclosure_page_url="https://www.hdfcfund.com/statutory-disclosure",
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
    )
    downloader = AMCDownloader(source=source, timeout_seconds=10.0, user_agent="test-agent")
    docs = downloader.list_documents("factsheet")

    assert docs
    assert docs[0].amc_code == "HDFC"
    assert docs[0].file_ext == ".pdf"
    assert docs[0].report_month == date(2026, 4, 1)


def test_sbi_generic_download_returns_file_bytes(monkeypatch):
    payload = b"dummy-pdf-bytes"

    def fake_get(url, timeout=None, headers=None, **kwargs):  # noqa: ANN001
        return _FakeResponse(url=url, content=payload, headers={"Content-Type": "application/pdf"})

    monkeypatch.setattr("app.mf_ingestion.downloaders.amc_downloader.requests.get", fake_get)

    source = AMCDocumentSource(
        amc_name="SBI Mutual Fund",
        amc_code="SBI",
        adapter_key="sbi",
        factsheet_page_url="https://www.sbimf.com/en-us/downloads",
        portfolio_disclosure_page_url="https://www.sbimf.com/en-us/disclosures",
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
    )
    downloader = AMCDownloader(source=source, timeout_seconds=10.0, user_agent="test-agent")
    discovered = DiscoveredDocument(
        amc_name="SBI Mutual Fund",
        amc_code="SBI",
        document_type="factsheet",
        title="SBI Factsheet Apr 2026",
        url="https://www.sbimf.com/en-us/downloads/sbi-factsheet-apr-2026.pdf",
        discovery_page_url="https://www.sbimf.com/en-us/downloads",
        file_ext=".pdf",
        report_month=date(2026, 4, 1),
        priority_score=100,
    )

    downloaded = downloader.download(discovered)
    assert downloaded.amc_code == "SBI"
    assert downloaded.file_name == "sbi-factsheet-apr-2026.pdf"
    assert downloaded.file_size_bytes == len(payload)
    assert downloaded.file_bytes == payload


def test_sbi_generic_download_rejects_error_page(monkeypatch):
    payload = b"<html><body>error</body></html>"

    def fake_get(url, timeout=None, headers=None, **kwargs):  # noqa: ANN001
        return _FakeResponse(
            url="https://www.sbimf.com/error?aspxerrorpath=/docs/default-source/scheme-portfolios/file.xlsx",
            content=payload,
            headers={"Content-Type": "text/html"},
        )

    monkeypatch.setattr("app.mf_ingestion.downloaders.amc_downloader.requests.get", fake_get)

    source = AMCDocumentSource(
        amc_name="SBI Mutual Fund",
        amc_code="SBI",
        adapter_key="sbi",
        factsheet_page_url="https://www.sbimf.com/en-us/downloads",
        portfolio_disclosure_page_url="https://www.sbimf.com/en-us/disclosures",
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
    )
    downloader = AMCDownloader(source=source, timeout_seconds=10.0, user_agent="test-agent")
    discovered = DiscoveredDocument(
        amc_name="SBI Mutual Fund",
        amc_code="SBI",
        document_type="portfolio_disclosure",
        title="SBI Portfolio Apr 2026",
        url="https://www.sbimf.com/docs/default-source/scheme-portfolios/file.xlsx",
        discovery_page_url="https://www.sbimf.com/en-us/disclosures",
        file_ext=".xlsx",
        report_month=date(2026, 4, 1),
        priority_score=100,
    )

    with pytest.raises(RuntimeError, match="download_rejected_error_page"):
        downloader.download(discovered)
