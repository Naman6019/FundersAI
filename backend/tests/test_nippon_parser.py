from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from app.mf_ingestion.downloaders import amc_downloader
from app.mf_ingestion.downloaders.amc_downloader import AMCDownloader
from app.mf_ingestion.parsers.adapters.nippon_adapter import NipponAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.factsheet_parser import FactsheetParser
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser
from app.mf_ingestion.sources.registry import get_source

NIPPON_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "mf_raw_docs"
    / "Nippon"
    / "NIMF-MONTHLY-PORTFOLIO-31-May-26.xls"
)


def _context() -> ParseContext:
    return ParseContext(source_document_id="nippon-may-2026", source_url="local", report_month=None)


@pytest.mark.skipif(not NIPPON_FIXTURE.exists(), reason="Nippon portfolio fixture is not available")
def test_nippon_real_workbook_parses_equity_and_debt_sheets():
    records = HoldingsParser(NipponAdapter()).parse_many(str(NIPPON_FIXTURE), _context())
    by_name = {record.scheme_name.lower(): record for record in records}

    growth = by_name["nippon india growth mid cap fund"]
    assert growth.report_month == date(2026, 5, 1)
    assert len(growth.holdings) >= 50
    assert growth.metrics["total_percent_aum"] == pytest.approx(100.45)
    assert growth.holdings[0]["instrument_name"] == "BSE Limited"
    assert growth.holdings[0]["isin"] == "INE118H01025"
    assert growth.holdings[0]["sector"] == "Capital Markets"
    assert growth.holdings[0]["percent_aum"] == pytest.approx(3.32)

    corporate_bond = by_name["nippon india corporate bond fund"]
    assert corporate_bond.report_month == date(2026, 5, 1)
    assert len(corporate_bond.holdings) >= 50
    assert corporate_bond.metrics["total_percent_aum"] == pytest.approx(93.38)
    assert any(row["sector"] == "CRISIL AAA" for row in corporate_bond.holdings)


def test_nippon_synthetic_frame_scales_percent_and_uses_non_isin_rows_for_total_only():
    frame = pd.DataFrame(
        [
            ["RLMF001", "Nippon India Sample Fund (An open ended equity scheme)", None, None, None, None, None],
            [None, "Monthly Portfolio Statement as on May 31,2026", None, None, None, None, None],
            [None, "ISIN", "Name of the Instrument", "Industry / Rating", "Quantity", "Market/Fair Value ( Rs. in Lacs)", "% to NAV"],
            ["HDFB03", "INE040A01034", "HDFC Bank Limited", "Banks", 1000, 5000.0, 0.0512],
            ["IBCL05", "INE090A01021", "ICICI Bank Limited", "Banks", 2000, 6000.0, 45.0],
            [None, None, "TREPS", None, None, 4800.0, 49.88],
        ]
    )

    parsed = NipponAdapter().parse_holdings([frame], [], "", _context())

    assert parsed.scheme_name == "Nippon India Sample Fund"
    assert parsed.report_month == date(2026, 5, 1)
    assert len(parsed.holdings) == 2
    assert parsed.holdings[0]["percent_aum"] == pytest.approx(5.12)
    assert parsed.metrics["total_percent_aum"] == pytest.approx(100.0)
    assert all(row["isin"] for row in parsed.holdings)


def test_nippon_factsheet_parser_accepts_html_files(tmp_path):
    html = """
    <html><body>
      <h1>Nippon India Small Cap Fund</h1>
      <p>Assets Under Management Rs. 59,456.65 crores</p>
      <p>Direct Plan : 0.67%</p>
      <p>Benchmark</p>
      <p>Nifty Smallcap 250 TRI</p>
      <p>Fund Manager: Mr. Samir Rachh</p>
      <p>Riskometer: Very High</p>
    </body></html>
    """
    path = tmp_path / "small-cap.html"
    path.write_text(html, encoding="utf-8")

    records = FactsheetParser().parse(str(path), ParseContext("doc", "local", date(2026, 6, 1)))

    assert len(records) == 1
    record = records[0]
    assert record.scheme_name == "Nippon India Small Cap Fund"
    assert record.report_month == date(2026, 6, 1)
    assert record.aum == pytest.approx(59456.65)
    assert record.expense_ratio == pytest.approx(0.67)
    assert record.benchmark == "Nifty Smallcap 250 TRI"
    assert record.fund_manager == "Mr. Samir Rachh"
    assert record.risk_level == "Very High"


def test_nippon_discovery_reads_html_and_portfolio_links(monkeypatch):
    source = get_source("nippon")
    html = """
    <a href="/InvestorServices/FactsheetsDocuments/Fundamentals-June-2026/Innerpage/Small-Cap.html">
      Nippon India Small Cap Fund
    </a>
    <a href="/docs/NIMF-MONTHLY-PORTFOLIO-31-May-2026.xls">Monthly Portfolio Disclosure</a>
    """

    def fake_request(*_args, **_kwargs):
        return SimpleNamespace(text=html, url=source.portfolio_disclosure_page_url)

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fake_request)

    downloader = AMCDownloader(source, timeout_seconds=5, user_agent="test")
    portfolio_docs = downloader.list_documents("portfolio_disclosure")
    factsheet_docs = downloader.list_documents("factsheet")

    assert portfolio_docs[0].file_ext == ".xls"
    assert portfolio_docs[0].report_month == date(2026, 5, 1)
    assert factsheet_docs[0].file_ext == ".html"
    assert "Small-Cap.html" in factsheet_docs[0].url


def test_nippon_manual_urls_work_when_listing_fetch_fails(monkeypatch):
    source = get_source("nippon")
    monkeypatch.setenv(
        "MF_NIPPON_PORTFOLIO_DOCUMENT_URLS",
        "https://mf.nipponindiaim.com/docs/NIMF-MONTHLY-PORTFOLIO-May-2026.xls",
    )

    def fail_request(*_args, **_kwargs):
        raise RuntimeError("listing unavailable")

    monkeypatch.setattr(amc_downloader, "_request_with_retry", fail_request)

    docs = AMCDownloader(source, timeout_seconds=5, user_agent="test").list_documents("portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].amc_code == "NIPPON"
    assert docs[0].file_ext == ".xls"
    assert docs[0].report_month == date(2026, 5, 1)
