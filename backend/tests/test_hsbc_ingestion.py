from __future__ import annotations

from datetime import date

from app.mf_ingestion.downloaders import amc_downloader
from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.parsers.adapters.hsbc_adapter import (
    HSBC_EXCLUDED_SECURITY_NAMES,
    HSBC_EXTRA_SECURITY_PATTERNS,
    _prepare_hsbc_page,
)
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.combined_factsheet_portfolio import (
    parse_combined_factsheet_page,
)
from app.mf_ingestion.parsers.factsheet_parser import FactsheetParser
from app.mf_ingestion.sources.registry import get_source


def test_hsbc_page_core_fields_use_manager_and_benchmark_labels() -> None:
    page = """12
HSBC Test Fund
An open ended scheme
Fund Details
Benchmark
NIFTY 100 TRI
NAV (as on 31.07.26)
Growth
10.00
AUM (as on 31.07.26)
₹ 100 Cr.
Fund Manager
Test Manager (Equity)
Total Experience
10 Years
Managing Since
Jan 01, 2020
Expense Ratio
Month End Expense Ratios (Annualized)
Regular
1.00%
Direct
0.50%
The risk of the scheme is Very High Risk
"""

    records = FactsheetParser().parse_text(
        page,
        report_month=date(2026, 7, 1),
        page_texts=[page],
    )

    assert len(records) == 1
    record = records[0]
    assert record.scheme_name == "HSBC Test Fund"
    assert record.aum == 100.0
    assert record.expense_ratio == 0.5
    assert record.benchmark == "NIFTY 100 TRI"
    assert record.fund_manager == "Test Manager"
    assert record.risk_level == "Very High"


def test_hsbc_positioned_portfolio_page_is_bounded_at_grand_total() -> None:
    page = """12
HSBC Test Large Cap Fund
Large Cap Fund - An open ended scheme
Fund Details
Issuer
Rating
% to Net Assets
Technology
ABC Limited
AAA
1.25%
DEF Bank Ltd
AAA
2.50%
Total Net Assets as on July 31, 2026
"""

    prepared = _prepare_hsbc_page(page)
    assert prepared is not None
    scheme_name, prepared_text = prepared
    parsed = parse_combined_factsheet_page(
        prepared_text,
        ParseContext("doc", "https://example.test/hsbc.pdf", date(2026, 7, 1)),
        scheme_prefixes=("HSBC",),
        extra_security_patterns=HSBC_EXTRA_SECURITY_PATTERNS,
        excluded_security_names=HSBC_EXCLUDED_SECURITY_NAMES,
    )

    assert scheme_name == "HSBC Test Large Cap Fund"
    assert parsed is not None
    assert parsed.metrics["total_percent_aum"] == 3.75
    assert len(parsed.holdings) == 2
    assert all("Total Net Assets" not in row["instrument_name"] for row in parsed.holdings)


def test_hsbc_discovery_ranks_report_month_from_official_url(monkeypatch) -> None:
    june = DiscoveredDocument(
        amc_name="HSBC Mutual Fund",
        amc_code="HSBC",
        document_type="factsheet",
        title="The Asset June 2026",
        url="https://www.assetmanagement.hsbc.co.in/assets/documents/mutual-funds/en/june/the-asset-june-2026.pdf",
        discovery_page_url=get_source("hsbc").factsheet_page_url,
        file_ext=".pdf",
        report_month=date(2026, 6, 1),
        priority_score=999999,
    )
    july = DiscoveredDocument(
        amc_name="HSBC Mutual Fund",
        amc_code="HSBC",
        document_type="factsheet",
        title="The Asset June 2026",
        url="https://www.assetmanagement.hsbc.co.in/assets/documents/mutual-funds/en/july/the-asset-july-2026.pdf",
        discovery_page_url=get_source("hsbc").factsheet_page_url,
        file_ext=".pdf",
        report_month=date(2026, 6, 1),
        priority_score=1,
    )

    monkeypatch.setattr(
        amc_downloader,
        "_discover_generic_anchor_documents",
        lambda *_args, **_kwargs: [june, july],
    )

    documents = amc_downloader._discover_hsbc_documents(
        get_source("hsbc"),
        "factsheet",
        timeout_seconds=1,
        user_agent="test",
    )

    assert [document.report_month for document in documents] == [
        date(2026, 7, 1),
        date(2026, 6, 1),
    ]
    assert documents[0].url.endswith("the-asset-july-2026.pdf")
