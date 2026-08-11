from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from app.mf_ingestion.downloaders import amc_downloader
from app.mf_ingestion.downloaders.amc_downloader import (
    AMCDownloader,
    _browser_fallback_allowed_for_source,
    _discover_kotak_combined_factsheets,
    _guess_hdfc_combined_factsheets,
    _kotak_candidates_from_payload,
    _kotak_documents_from_candidates,
    _load_hdfc_reviewed_monthly_portfolios,
)
from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.parsers.adapters.axis_adapter import (
    AxisAdapter,
    _axis_factsheet_links_from_payload,
    _axis_render_url,
    _browser_fallback_allowed,
)
from app.mf_ingestion.parsers.adapters.ppfas_adapter import _ppfas_confirmation_url
from app.mf_ingestion.sources.registry import AMCDocumentSource, get_source


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
    source = get_source("hdfc")

    docs = AMCDownloader(source, timeout_seconds=1, user_agent="test").list_documents("portfolio_disclosure")

    assert len(docs) == 108
    live_doc = next(doc for doc in docs if doc.report_month == date(2026, 4, 1))
    assert live_doc.file_ext == ".xlsx"
    assert live_doc.url.endswith(".xlsx")


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

    assert len(docs) == 107
    assert all(doc.file_ext == ".xlsx" for doc in docs)
    assert all("HDFC%20MF%20Factsheet" not in doc.url for doc in docs)


def test_hdfc_reviewed_xlsx_inventory_replaces_pdf_fallback_when_page_fails(
    monkeypatch,
) -> None:
    def fail_request(*args, **kwargs):
        raise RuntimeError("listing unavailable")

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fail_request)

    docs = AMCDownloader(
        get_source("hdfc"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("portfolio_disclosure")

    assert len(docs) == 107
    assert all(doc.file_ext == ".xlsx" for doc in docs)


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

    assert any(doc.url.endswith("May%202026.pdf") for doc in docs)
    assert any(doc.file_ext == ".xlsx" for doc in docs)


def test_hdfc_official_bucket_fallback_builds_prior_month_combined_factsheet() -> None:
    source = get_source("hdfc")

    factsheets = _guess_hdfc_combined_factsheets(
        source,
        "factsheet",
        now_utc=datetime(2026, 7, 28, tzinfo=UTC),
    )
    portfolios = _guess_hdfc_combined_factsheets(
        source,
        "portfolio_disclosure",
        now_utc=datetime(2026, 7, 28, tzinfo=UTC),
    )

    assert factsheets[0].report_month == date(2026, 6, 1)
    assert factsheets[0].url == (
        "https://files.hdfcfund.com/s3fs-public/2026-07/"
        "HDFC%20MF%20Factsheet%20-%20June%202026_1.pdf"
    )
    assert factsheets[1].url == (
        "https://files.hdfcfund.com/s3fs-public/2026-07/"
        "HDFC%20MF%20Index%20Solutions%20Factsheet%20-%20June%202026_1.pdf"
    )
    assert factsheets[2].url.endswith(
        "HDFC%20MF%20Factsheet%20-%20June%202026.pdf"
    )
    assert portfolios[0].url == factsheets[0].url
    assert portfolios[1].url == factsheets[1].url
    assert portfolios[0].document_type == "portfolio_disclosure"


def test_kotak_dropdown_month_remains_the_report_month_after_publication() -> None:
    docs = _discover_kotak_combined_factsheets(
        get_source("kotak"),
        now_utc=datetime(2026, 8, 10, tzinfo=UTC),
    )

    assert docs[0].report_month == date(2026, 7, 1)
    assert docs[0].url == (
        "https://vatseelabs-s3.kotakmf.com/FormsDownloads/Factsheet/"
        "Factsheet-for-July-2026/KotakMFFactsheetJuly2026.pdf"
    )
    assert docs[0].discovery_page_url == "https://www.kotakmf.com/Information/forms-and-downloads"


def test_hdfc_reviewed_inventory_builds_exact_june_portfolio_urls() -> None:
    docs = _load_hdfc_reviewed_monthly_portfolios(
        get_source("hdfc"),
        "portfolio_disclosure",
    )

    assert len(docs) == 107
    assert all(doc.report_month == date(2026, 6, 1) for doc in docs)
    assert all(doc.file_ext == ".xlsx" for doc in docs)
    assert all(
        doc.discovery_page_url
        == "https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio"
        for doc in docs
    )
    assert any(
        doc.url.endswith(
            "Monthly%20HDFC%20Nifty100%20Quality%2030%20ETF%20-%2030%20June%202026.xlsx"
        )
        for doc in docs
    )
    assert not any("Banking%20Financial%20Services" in doc.url for doc in docs)


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

    assert any(doc.url.endswith("May%202026.pdf") for doc in docs)
    assert any(doc.file_ext == ".xlsx" for doc in docs)


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


def test_kotak_browser_fallback_requires_registry_and_explicit_approval(
    monkeypatch,
) -> None:
    source = get_source("kotak")
    monkeypatch.delenv("MF_DISCOVERY_BROWSER_ENABLED", raising=False)
    monkeypatch.delenv("MF_DISCOVERY_BROWSER_AMCS", raising=False)
    assert _browser_fallback_allowed_for_source(source) is False

    monkeypatch.setenv("MF_DISCOVERY_BROWSER_ENABLED", "true")
    monkeypatch.setenv("MF_DISCOVERY_BROWSER_AMCS", "axis")
    assert _browser_fallback_allowed_for_source(source) is False

    monkeypatch.setenv("MF_DISCOVERY_BROWSER_AMCS", "axis,kotak")
    assert _browser_fallback_allowed_for_source(source) is True


def test_kotak_payload_maps_extensionless_monthly_portfolio_download() -> None:
    source = get_source("kotak")
    candidates = _kotak_candidates_from_payload(
        {
            "documents": [
                {
                    "title": "Monthly Portfolio June 2026",
                    "downloadUrl": "/kotakmf/reportupload/download/Monthly/6000/2026/6",
                }
            ]
        },
        source.portfolio_disclosure_page_url or "",
    )

    documents = _kotak_documents_from_candidates(
        source,
        "portfolio_disclosure",
        source.portfolio_disclosure_page_url or "",
        candidates,
    )

    assert len(documents) == 1
    assert documents[0].file_ext == ".xlsx"
    assert documents[0].report_month == date(2026, 6, 1)
    assert documents[0].url.endswith("/reportupload/download/Monthly/6000/2026/6")


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
    assert _axis_render_url(
        "https://www.axismf.com/downloads",
        "portfolio_disclosure",
        factsheet_contains_holdings=True,
    ) == "https://www.axismf.com/downloads/products"


def test_axis_factsheet_api_payload_maps_official_documents() -> None:
    links = _axis_factsheet_links_from_payload(
        {
            "data": {
                "productFactSheetData": [
                    {
                        "name": "Axis Fund Factsheet June-2026",
                        "documentUrl": "https://www.axismf.com/docs/axis-june-2026.pdf",
                    },
                    {
                        "name": "Axis Passive Factsheet June-2026",
                        "documentUrl": "https://www.axismf.com/docs/axis-passive-june-2026.pdf",
                    },
                ]
            }
        }
    )

    assert [link["title"] for link in links] == [
        "Axis Fund Factsheet June-2026",
        "Axis Passive Factsheet June-2026",
    ]
    assert all(link["file_ext"] == ".pdf" for link in links)


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


def test_motilal_official_api_uses_report_month_from_title(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    payload = {
        "results": [
            {
                "path": "/content/dam/motilal-mf/downloads/mf/factsheet/2026/jun/Factsheet May 2026 Active.pdf",
                "title": "Factsheet May 2026 Active",
                "year": "2026",
                "month": "jun",
                "category": "factsheet",
                "publishDate": "08-06-2026",
                "mimeType": "application/pdf",
            }
        ]
    }

    def fake_request(*args, **kwargs):
        calls.append(kwargs["params"])
        return SimpleNamespace(json=lambda: payload)

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fake_request)
    docs = AMCDownloader(
        _source("motilal", "https://www.motilaloswalmf.com/downloads/factsheets"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("factsheet")

    assert len(docs) == 1
    assert docs[0].url == (
        "https://www.motilaloswalmf.com/content/dam/motilal-mf/downloads/mf/"
        "factsheet/2026/jun/Factsheet May 2026 Active.pdf"
    )
    assert docs[0].report_month == date(2026, 5, 1)
    assert all(call["category"] == "factsheet" for call in calls)
    assert calls[0]["year"] == ""
    assert calls[0]["month"] == ""
    assert len(calls) == amc_downloader.MOTILAL_DISCOVERY_LOOKBACK_MONTHS + 1


def test_motilal_official_api_maps_month_end_portfolio(monkeypatch) -> None:
    payload = {
        "results": [
            {
                "path": "/content/dam/motilal-mf/downloads/mf/month-end-portfolio/2026/jun/"
                "ForthNightly report for 15th June 2026.xlsx",
                "title": "ForthNightly report for 15th June 2026",
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
            {
                "path": "/content/dam/motilal-mf/downloads/mf/month-end-portfolio/2026/jun/"
                "Month End Portfolio June 2026.xlsx",
                "title": "Month End Portfolio June 2026",
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        ]
    }
    calls: list[dict[str, object]] = []

    def fake_request(*args, **kwargs):
        calls.append(kwargs["params"])
        return SimpleNamespace(json=lambda: payload)

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fake_request)
    docs = AMCDownloader(
        get_source("motilal"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].file_ext == ".xlsx"
    assert docs[0].report_month == date(2026, 6, 1)
    assert all(call["category"] == "month end portfolio" for call in calls)
    assert calls[0]["year"] == ""
    assert calls[0]["month"] == ""


def test_absl_official_api_maps_june_portfolio_to_amc_host(monkeypatch) -> None:
    payload = {
        "AccordionList": [
            {
                "ResourceLink": "Monthly Portfolios as on June 30, 2026",
                "pdfUrl": (
                    "https://abcscprod.azureedge.net/-/media/bsl/files/resources/"
                    "monthly-portfolio/2026/monthly-portfolio-30-june-2026.zip"
                ),
            },
            {
                "ResourceLink": "Fortnightly Portfolio as on June 15, 2026",
                "pdfUrl": (
                    "https://abcscprod.azureedge.net/-/media/bsl/files/resources/"
                    "monthly-portfolio/2026/fortnightly-portfolio-15-june-2026.zip"
                ),
            },
        ]
    }
    calls: list[dict[str, object]] = []

    def fake_request(*args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(json=lambda: payload)

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fake_request)
    docs = AMCDownloader(
        get_source("aditya_birla"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].url == (
        "https://mutualfund.adityabirlacapital.com/-/media/bsl/files/resources/"
        "monthly-portfolio/2026/monthly-portfolio-30-june-2026.zip"
    )
    assert docs[0].report_month == date(2026, 6, 1)
    assert calls[0]["params"]["id"] == amc_downloader.ABSL_PORTFOLIO_RESOURCE_ID


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


def test_dsp_official_portfolio_page_discovers_month_end_zip(monkeypatch) -> None:
    page_url = "https://www.dspim.com/mandatory-disclosures/portfolio-disclosures"
    zip_url = (
        "https://www.dspim.com/media/pages/mandatory-disclosures/portfolio-disclosures/"
        "ee5dc05630-1784285969/monthend-portfolios_30_june_2026.zip"
    )
    html = f"""
    <a href="{zip_url}">Portfolio Details as on June 30, 2026</a>
    <a href="/downloads/fortnightly-portfolio-june-2026.xlsx">
      Fortnightly Portfolios as on June 30, 2026
    </a>
    <a href="/downloads/fund-performance-june-2026.xlsx">
      Scheme Performance as on June 30, 2026
    </a>
    """
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *args, **kwargs: SimpleNamespace(text=html, url=page_url),
    )

    docs = AMCDownloader(
        get_source("dsp"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].title == "Portfolio Details as on June 30, 2026"
    assert docs[0].url == zip_url
    assert docs[0].file_ext == ".zip"
    assert docs[0].report_month == date(2026, 6, 1)


def test_uti_official_api_keeps_english_active_and_passive_variants(monkeypatch) -> None:
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
    ]
    assert docs[0].report_month == date(2026, 6, 1)


def test_uti_official_api_keeps_exact_prior_month_when_newer_rows_exist(monkeypatch) -> None:
    july_rows = [
        {
            "name": "UTI Fund Watch(Active)-July 2026",
            "doc": "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/active-july-2026.pdf",
            "month": "July",
            "year": "2026",
        }
    ]
    june_rows = [
        {
            "name": "UTI Fund Watch(Active)-June 2026",
            "doc": "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/active-june-2026.pdf",
            "month": "June",
            "year": "2026",
        }
    ]

    def fake_request(*args, **kwargs):
        month = kwargs["params"]["month"]
        rows = july_rows if month == "July" else june_rows if month == "June" else []
        return SimpleNamespace(json=lambda: {"rows": rows})

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fake_request)

    docs = AMCDownloader(
        _source("uti", "https://www.utimf.com/downloads/fact-sheet"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("factsheet")

    assert [doc.report_month for doc in docs] == [
        date(2026, 6, 1),
        date(2026, 5, 1),
    ]
    assert docs[1].title == "UTI Fund Watch(Active)-June 2026"


def test_nippon_discovery_excludes_inner_html_pages(monkeypatch) -> None:
    listing_url = (
        "https://mf.nipponindiaim.com/InvestorServices/"
        "FactsheetsDocuments/Fundamentals-June-2026/index.html"
    )
    html = """
    <a href="Nippon-FS-JUNE-2026.pdf">Nippon Fund Factsheet June 2026</a>
    <a href="Innerpage/Large-Cap.html">Nippon Large Cap Fund</a>
    """
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *args, **kwargs: SimpleNamespace(text=html, url=listing_url),
    )

    docs = AMCDownloader(
        _source("nippon", listing_url),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("factsheet")

    assert len(docs) == 1
    assert docs[0].url.endswith("Nippon-FS-JUNE-2026.pdf")


def test_nippon_portfolio_uses_surrounding_month_label(monkeypatch) -> None:
    listing_url = "https://mf.nipponindiaim.com/investor-service/downloads/disclosures"
    html = """
    <ul>
      <li>Monthly portfolio for the month of June 2026
        <a href="/InvestorServices/FactsheetsDocuments/monthly-portfolio.xls">Download</a>
      </li>
      <li>Debt Schemes Fortnightly Portfolio as on 15th June 2026
        <a href="/InvestorServices/FactsheetsDocuments/fortnightly-portfolio.xls">Download</a>
      </li>
    </ul>
    """
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *args, **kwargs: SimpleNamespace(text=html, url=listing_url),
    )

    docs = AMCDownloader(
        get_source("nippon"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].title == "Monthly portfolio for the month of June 2026 Download"
    assert docs[0].report_month == date(2026, 6, 1)


def test_nippon_factsheet_uses_publication_month_as_prior_report_month(monkeypatch) -> None:
    listing_url = (
        "https://mf.nipponindiaim.com/investor-service/downloads/"
        "factsheet-portfolio-and-other-disclosures"
    )
    html = """
    <ul>
      <li>E- Factsheet: July 2026
        <a href="/InvestorServices/FactSheetsDocuments/Nippon-FS-JULY-2026.pdf">
          \u200bDownload\u200b
        </a>
      </li>
      <li>E- Factsheet: June 2026
        <a href="/InvestorServices/FactSheetsDocuments/Nippon-FS-JUNE-2026.pdf">
          Download
        </a>
      </li>
    </ul>
    """
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *args, **kwargs: SimpleNamespace(text=html, url=listing_url),
    )

    docs = AMCDownloader(
        get_source("nippon"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("factsheet")

    assert [doc.report_month for doc in docs] == [
        date(2026, 6, 1),
        date(2026, 5, 1),
    ]
    assert docs[0].title == "E- Factsheet: July 2026 Download"
    assert "\u200b" not in docs[0].title


def test_uti_factsheet_uses_publication_month_as_prior_report_month(monkeypatch) -> None:
    payload = {
        "rows": [
            {
                "name": "UTI Fund Watch Active July 2026",
                "doc": (
                    "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-07/"
                    "uti_fund_watch_active_july_2026.pdf"
                ),
                "month": "July",
                "year": "2026",
            }
        ]
    }
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *args, **kwargs: SimpleNamespace(json=lambda: payload),
    )

    docs = AMCDownloader(
        get_source("uti"),
        timeout_seconds=1,
        user_agent="test",
    ).list_documents("factsheet")

    assert docs[0].report_month == date(2026, 6, 1)


def test_nippon_mislabeled_openxml_workbook_is_normalized(monkeypatch) -> None:
    source = get_source("nippon")
    document = DiscoveredDocument(
        amc_name=source.amc_name,
        amc_code=source.amc_code,
        document_type="portfolio_disclosure",
        title="Monthly portfolio for the month of June 2026",
        url="https://mf.nipponindiaim.com/docs/monthly-portfolio-june-2026.xls",
        discovery_page_url=source.portfolio_disclosure_page_url or "",
        file_ext=".xls",
        report_month=date(2026, 6, 1),
        priority_score=1,
    )
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *args, **kwargs: SimpleNamespace(
            content=b"PK\x03\x04" + b"\x00" * 64,
            headers={"Content-Type": "application/vnd.ms-excel"},
            url=document.url,
        ),
    )

    downloaded = AMCDownloader(source, timeout_seconds=1, user_agent="test").probe_download(document)

    assert downloaded.file_ext == ".xlsx"


def test_hdfc_file_probe_uses_public_browser_user_agent(monkeypatch) -> None:
    source = get_source("hdfc")
    document = DiscoveredDocument(
        amc_name=source.amc_name,
        amc_code=source.amc_code,
        document_type="factsheet",
        title="HDFC MF Factsheet - June 2026",
        url=(
            "https://files.hdfcfund.com/s3fs-public/2026-07/"
            "HDFC%20MF%20Factsheet%20-%20June%202026.pdf"
        ),
        discovery_page_url=source.factsheet_page_url or "",
        file_ext=".pdf",
        report_month=date(2026, 6, 1),
        priority_score=1,
    )
    captured: dict[str, object] = {}

    def fake_request(*_args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            content=b"%PDF-1.7 official",
            headers={"Content-Type": "application/pdf"},
            url=document.url,
        )

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fake_request)

    AMCDownloader(source, timeout_seconds=1, user_agent="FundersAIResearchBot/1.0").probe_download(
        document
    )

    assert str(captured["headers"]["User-Agent"]).startswith("Mozilla/5.0")


def test_probe_download_falls_back_to_unranged_get_on_416(monkeypatch) -> None:
    """Some AMC CDNs (observed: sbimf.com) reject the ranged probe GET with
    416 Requested Range Not Satisfiable instead of a partial/full response.
    The probe must retry without the Range header rather than failing discovery."""
    source = get_source("sbi")
    document = DiscoveredDocument(
        amc_name=source.amc_name,
        amc_code=source.amc_code,
        document_type="factsheet",
        title="SBI MF Factsheet - June 2026",
        url="https://www.sbimf.com/docs/default-source/scheme-factsheets/all-sbimf-schemes-factsheet-june-2026.pdf",
        discovery_page_url=source.factsheet_page_url or "",
        file_ext=".pdf",
        report_month=date(2026, 6, 1),
        priority_score=1,
    )
    calls: list[dict[str, object]] = []

    def fake_request(method, url, *, timeout_seconds, headers=None, **_kwargs):
        calls.append({"headers": dict(headers or {})})
        if "Range" in (headers or {}):
            raise RuntimeError(
                f"http_request_failed method={method} url={url} "
                "reason=416 Client Error: Requested Range Not Satisfiable for url: " + url
            )
        return SimpleNamespace(content=b"%PDF-1.7 official", headers={"Content-Type": "application/pdf"}, url=url)

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fake_request)

    downloaded = AMCDownloader(source, timeout_seconds=1, user_agent="FundersAIResearchBot/1.0").probe_download(
        document
    )

    assert downloaded.file_bytes == b"%PDF-1.7 official"
    assert len(calls) == 2
    assert "Range" in calls[0]["headers"]
    assert "Range" not in calls[1]["headers"]


def test_probe_download_reraises_non_range_failures(monkeypatch) -> None:
    source = get_source("sbi")
    document = DiscoveredDocument(
        amc_name=source.amc_name,
        amc_code=source.amc_code,
        document_type="factsheet",
        title="SBI MF Factsheet - June 2026",
        url="https://www.sbimf.com/docs/default-source/scheme-factsheets/all-sbimf-schemes-factsheet-june-2026.pdf",
        discovery_page_url=source.factsheet_page_url or "",
        file_ext=".pdf",
        report_month=date(2026, 6, 1),
        priority_score=1,
    )

    def fake_request(method, url, *, timeout_seconds, headers=None, **_kwargs):
        raise RuntimeError(f"http_request_failed method={method} url={url} reason=404 Client Error: Not Found for url: {url}")

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fake_request)

    try:
        AMCDownloader(source, timeout_seconds=1, user_agent="FundersAIResearchBot/1.0").probe_download(document)
    except RuntimeError as exc:
        assert "reason=404" in str(exc)
    else:
        raise AssertionError("expected a non-416 probe failure to propagate")


def test_ppfas_empty_form_action_posts_to_confirmation_page() -> None:
    assert _ppfas_confirmation_url("https://amc.ppfas.com/downloads/index.php") == "/downloads/ConfirmCitizenship.php"
    assert (
        _ppfas_confirmation_url("https://amc.ppfas.com/statutory-disclosures/index.php")
        == "/statutory-disclosures/ConfirmCitizenship.php"
    )
