from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.mf_ingestion.downloaders import amc_downloader
from app.mf_ingestion.downloaders.amc_downloader import AMCDownloader
from app.mf_ingestion.parsers.adapters.ppfas_adapter import _ppfas_confirmation_url
from app.mf_ingestion.sources.registry import AMCDocumentSource


def _source(adapter_key: str, factsheet_url: str, portfolio_url: str | None = None) -> AMCDocumentSource:
    return AMCDocumentSource(
        amc_name=f"{adapter_key.upper()} Mutual Fund",
        amc_code=adapter_key.upper(),
        adapter_key=adapter_key,
        factsheet_page_url=factsheet_url,
        portfolio_disclosure_page_url=portfolio_url or factsheet_url,
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
    )


def test_hdfc_embedded_portfolio_xlsx_links_are_discovered(monkeypatch) -> None:
    html = """
    <script>
    {"files":[{"title":"Monthly HDFC Nifty G-Sec Jun 2036 Index Fund - 30 April 2026.xlsx",
    "file":{"url":"https://files.hdfcfund.com/s3fs-public/2026-05/Monthly%20HDFC%20Nifty%20G-Sec%20Jun%202036%20Index%20Fund%20-%2030%20April%202026.xlsx"}}]}
    </script>
    """

    def fake_request(*args, **kwargs):
        return SimpleNamespace(text=html, url="https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio")

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fake_request)
    source = _source("hdfc", "https://www.hdfcfund.com/factsheets", "https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio")

    docs = AMCDownloader(source, timeout_seconds=1, user_agent="test").list_documents("portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].file_ext == ".xlsx"
    assert docs[0].report_month == date(2026, 4, 1)
    assert docs[0].url.endswith(".xlsx")


def test_sbi_recent_factsheet_endpoint_is_discovered(monkeypatch) -> None:
    html = """
    <tr><td><a href="https://www.sbimf.com/docs/default-source/scheme-factsheets/all-sbimf-schemes-factsheet-april-2026.pdf?x=1">
    All SBIMF Schemes Factsheet April 2026</a></td></tr>
    """

    def fake_request(*args, **kwargs):
        return SimpleNamespace(text=html, url="https://www.sbimf.com/ajaxcall/CMS/GetRecentFactSheets")

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fake_request)
    source = _source("sbi", "https://www.sbimf.com/factsheets", "https://www.sbimf.com/portfolios")

    docs = AMCDownloader(source, timeout_seconds=1, user_agent="test").list_documents("factsheet")

    assert len(docs) == 1
    assert docs[0].file_ext == ".pdf"
    assert docs[0].report_month == date(2026, 4, 1)
    assert docs[0].title == "All SBIMF Schemes Factsheet April 2026"


def test_ppfas_empty_form_action_posts_to_confirmation_page() -> None:
    assert _ppfas_confirmation_url("https://amc.ppfas.com/downloads/index.php") == "/downloads/ConfirmCitizenship.php"
    assert (
        _ppfas_confirmation_url("https://amc.ppfas.com/statutory-disclosures/index.php")
        == "/statutory-disclosures/ConfirmCitizenship.php"
    )
