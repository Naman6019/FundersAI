from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.mf_ingestion.downloaders import amc_downloader
from app.mf_ingestion.downloaders.amc_downloader import AMCDownloader
from app.mf_ingestion.parsers.adapters.axis_adapter import AxisAdapter, _axis_render_url, _browser_fallback_allowed
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


def test_hdfc_factsheet_urls_are_not_reused_for_portfolios_without_flag(monkeypatch) -> None:
    source = _source(
        "hdfc",
        "https://www.hdfcfund.com/factsheets",
        "https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio",
    )
    monkeypatch.setenv(
        "MF_HDFC_FACTSHEET_DOCUMENT_URLS",
        "https://files.hdfcfund.com/s3fs-public/2026-05/HDFC%20MF%20Factsheet%20-%20May%202026.pdf",
    )

    def fail_request(*args, **kwargs):
        raise RuntimeError("listing unavailable")

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fail_request)

    docs = AMCDownloader(source, timeout_seconds=1, user_agent="test").list_documents("portfolio_disclosure")

    assert docs == []


def test_hdfc_factsheet_urls_can_be_reused_for_portfolios_when_enabled(monkeypatch) -> None:
    source = _source(
        "hdfc",
        "https://www.hdfcfund.com/factsheets",
        "https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio",
    )
    monkeypatch.setenv("MF_ALLOW_HDFC_FACTSHEET_AS_PORTFOLIO", "true")
    monkeypatch.setenv(
        "MF_HDFC_FACTSHEET_DOCUMENT_URLS",
        "https://files.hdfcfund.com/s3fs-public/2026-05/HDFC%20MF%20Factsheet%20-%20May%202026.pdf",
    )

    def fail_request(*args, **kwargs):
        raise RuntimeError("listing unavailable")

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fail_request)

    docs = AMCDownloader(source, timeout_seconds=1, user_agent="test").list_documents("portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].document_type == "portfolio_disclosure"
    assert docs[0].url.endswith("May%202026.pdf")


def test_hdfc_generic_factsheet_reuse_flag_is_supported(monkeypatch) -> None:
    source = _source(
        "hdfc",
        "https://www.hdfcfund.com/factsheets",
        "https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio",
    )
    monkeypatch.setenv("MF_ALLOW_FACTSHEET_AS_PORTFOLIO", "true")
    monkeypatch.setenv(
        "MF_HDFC_FACTSHEET_DOCUMENT_URLS",
        "https://files.hdfcfund.com/s3fs-public/2026-05/HDFC%20MF%20Factsheet%20-%20May%202026.pdf",
    )

    def fail_request(*args, **kwargs):
        raise RuntimeError("listing unavailable")

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fail_request)

    docs = AMCDownloader(source, timeout_seconds=1, user_agent="test").list_documents("portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].document_type == "portfolio_disclosure"
    assert docs[0].url.endswith("May%202026.pdf")


def test_axis_manual_urls_are_used_before_dynamic_discovery(monkeypatch) -> None:
    source = _source("axis", "https://www.axismf.com/downloads")
    monkeypatch.setenv(
        "MF_AXIS_PORTFOLIO_DOCUMENT_URLS",
        "https://www.axismf.com/docs/Axis-MF-Monthly-Portfolio-May-2026.xlsx",
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("dynamic discovery should not run when manual URLs are configured")

    monkeypatch.setattr(AxisAdapter, "fetch_from_axis_api_or_page", fail_if_called)
    monkeypatch.setattr(AxisAdapter, "fetch_from_amfi", fail_if_called)
    monkeypatch.setattr(AxisAdapter, "fetch_with_playwright", fail_if_called)

    docs = AxisAdapter().fetch_documents(source, "portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].url.endswith("Axis-MF-Monthly-Portfolio-May-2026.xlsx")


def test_axis_factsheet_urls_can_be_reused_for_portfolios_when_enabled(monkeypatch) -> None:
    source = _source("axis", "https://www.axismf.com/downloads")
    monkeypatch.setenv("MF_ALLOW_FACTSHEET_AS_PORTFOLIO", "true")
    monkeypatch.setenv(
        "MF_AXIS_FACTSHEET_DOCUMENT_URLS",
        "https://www.axismf.com/1/5/1423/1426/2680/AxisFundFactsheetMarch2026.pdf",
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("dynamic discovery should not run when factsheet reuse is configured")

    monkeypatch.setattr(AxisAdapter, "fetch_from_axis_api_or_page", fail_if_called)
    monkeypatch.setattr(AxisAdapter, "fetch_from_amfi", fail_if_called)
    monkeypatch.setattr(AxisAdapter, "fetch_with_playwright", fail_if_called)

    docs = AxisAdapter().fetch_documents(source, "portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].document_type == "portfolio_disclosure"
    assert docs[0].url.endswith("AxisFundFactsheetMarch2026.pdf")


def test_axis_workflow_does_not_generate_dead_cdn_urls() -> None:
    workflow = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "sync-mf-disclosures.yml"
    assert "cdn.axismf.com" not in workflow.read_text(encoding="utf-8")


def test_axis_playwright_fallback_avoids_networkidle_wait() -> None:
    source = Path(__file__).resolve().parents[1] / "app" / "mf_ingestion" / "parsers" / "adapters" / "axis_adapter.py"
    text = source.read_text(encoding="utf-8")

    assert 'wait_until="domcontentloaded"' in text
    assert 'wait_until="networkidle"' not in text


def test_axis_browser_fallback_requires_explicit_enablement(monkeypatch) -> None:
    monkeypatch.delenv("MF_DISCOVERY_BROWSER_ENABLED", raising=False)
    monkeypatch.delenv("MF_DISCOVERY_BROWSER_AMCS", raising=False)
    assert _browser_fallback_allowed("axis") is False

    monkeypatch.setenv("MF_DISCOVERY_BROWSER_ENABLED", "true")
    monkeypatch.setenv("MF_DISCOVERY_BROWSER_AMCS", "axis")
    assert _browser_fallback_allowed("axis") is True


def test_axis_factsheet_render_url_selects_factsheet_filter() -> None:
    assert _axis_render_url("https://www.axismf.com/downloads", "factsheet") == (
        "https://www.axismf.com/downloads/products"
    )
    assert _axis_render_url("https://www.axismf.com/downloads?formType=Factsheet", "factsheet") == (
        "https://www.axismf.com/downloads/products"
    )
    assert _axis_render_url("https://www.axismf.com/downloads", "portfolio_disclosure") == (
        "https://www.axismf.com/downloads"
    )


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


def test_sbi_all_schemes_factsheet_outranks_passive_for_same_month(monkeypatch) -> None:
    html = """
    <a href="/docs/default-source/scheme-factsheets/sbi-passive-factsheet-june-2026.pdf">
      SBI MF Passives (Index ETF FOF) Factsheet June 2026
    </a>
    <a href="/docs/default-source/scheme-factsheets/all-sbimf-schemes-factsheet-june-2026.pdf">
      All SBIMF Schemes Factsheet June 2026
    </a>
    """
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *args, **kwargs: SimpleNamespace(text=html, url="https://www.sbimf.com/ajaxcall/CMS/GetRecentFactSheets"),
    )

    docs = AMCDownloader(
        _source("sbi", "https://www.sbimf.com/factsheets"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("factsheet")

    assert docs[0].title == "All SBIMF Schemes Factsheet June 2026"


def test_mirae_official_api_rejects_how_to_and_ranks_active(monkeypatch) -> None:
    payload = {
        "ReturnCode": "0",
        "Data": [
            {
                "Title": "How to read a Factsheet?",
                "URL": "/docs/default-source/fachsheet/mutual_fund_factsheet_how_to.pdf",
            },
            {
                "Title": "July 2026 - Passive Fund Factsheet",
                "URL": "/docs/default-source/fachsheet/passive-factsheet---july-2026.pdf",
            },
            {
                "Title": "July 2026 - Active Fund Factsheet",
                "URL": "/docs/default-source/fachsheet/active-factsheet---july-2026.pdf",
            },
        ],
    }
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *args, **kwargs: SimpleNamespace(json=lambda: payload),
    )

    docs = AMCDownloader(
        _source("mirae", "https://www.miraeassetmf.co.in/downloads/factsheet"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("factsheet")

    assert [doc.title for doc in docs] == [
        "July 2026 - Active Fund Factsheet",
        "July 2026 - Passive Fund Factsheet",
    ]
    assert all("how_to" not in doc.url for doc in docs)
    assert docs[0].report_month == date(2026, 7, 1)


def test_icici_title_month_overrides_conflicting_api_metadata() -> None:
    item = {
        "title": {"text": "Complete Factsheet June 2026"},
        "applicableMonth": 1777525200000,
    }

    assert amc_downloader._icici_report_month(item) == date(2026, 6, 1)


def test_dsp_official_json_endpoint_maps_latest_factsheet(monkeypatch) -> None:
    payload = {
        "data": [
            {
                "title": "Factsheet June 2026",
                "pdf_url": "https://www.dspim.com/downloads/dsp-factsheet-june-2026.pdf",
                "is_file": True,
            },
            {
                "title": "Factsheet May 2026",
                "pdf_url": "https://www.dspim.com/downloads/dsp-factsheet-may-2026.pdf",
                "is_file": True,
            },
        ]
    }
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *args, **kwargs: SimpleNamespace(json=lambda: payload),
    )

    docs = AMCDownloader(
        _source("dsp", "https://www.dspim.com/downloads"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("factsheet")

    assert docs[0].title == "Factsheet June 2026"
    assert docs[0].report_month == date(2026, 6, 1)
    assert docs[0].url == "https://www.dspim.com/downloads/dsp-factsheet-june-2026.pdf"


def test_uti_official_api_ranks_english_active_before_other_variants(monkeypatch) -> None:
    rows = [
        {
            "name": "UTI Fund Watch (Passive)-July 2026",
            "doc": "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/passive-july-2026.pdf",
            "month": "July",
            "year": "2026",
        },
        {
            "name": "UTI Fund Watch(Active)-July 2026 Hindi",
            "doc": "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/hindi-active-july-2026.pdf",
            "month": "July",
            "year": "2026",
        },
        {
            "name": "UTI Fund Watch(Active)-July 2026",
            "doc": "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/active-july-2026.pdf",
            "month": "July",
            "year": "2026",
        },
    ]
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *args, **kwargs: SimpleNamespace(json=lambda: {"rows": rows}),
    )

    docs = AMCDownloader(
        _source("uti", "https://www.utimf.com/downloads/fact-sheet"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("factsheet")

    assert [doc.title for doc in docs] == [
        "UTI Fund Watch(Active)-July 2026",
        "UTI Fund Watch (Passive)-July 2026",
        "UTI Fund Watch(Active)-July 2026 Hindi",
    ]
    assert docs[0].report_month == date(2026, 7, 1)


def test_ppfas_empty_form_action_posts_to_confirmation_page() -> None:
    assert _ppfas_confirmation_url("https://amc.ppfas.com/downloads/index.php") == "/downloads/ConfirmCitizenship.php"
    assert (
        _ppfas_confirmation_url("https://amc.ppfas.com/statutory-disclosures/index.php")
        == "/statutory-disclosures/ConfirmCitizenship.php"
    )
