from __future__ import annotations

from datetime import date

from app.mf_ingestion.agents.validation import validate_candidate
from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.sources.registry import get_source


def _candidate(source, *, document_type: str, url: str, report_month: date | None) -> DiscoveredDocument:
    return DiscoveredDocument(
        amc_name=source.amc_name,
        amc_code=source.amc_code,
        document_type=document_type,
        title="Download",
        url=url,
        discovery_page_url=source.portfolio_disclosure_page_url or "",
        file_ext=".pdf",
        report_month=report_month,
        priority_score=1,
    )


def test_a_portfolio_with_no_detectable_month_is_rejected():
    """Observed live: PGIM's AMFI Ready Reckoner, Commission Payout Framework and GST
    Invoice guide all sit under a /Portfolios/ URL and were accepted as portfolio
    disclosures; Bajaj's "Invest in Quality Portfolio backed by Strong Fundamentals"
    marketing leaflet was too, and parsed to zero holdings. None identified a month,
    and no legitimate portfolio disclosure across a full 42-AMC run lacked one."""
    source = get_source("pgim")
    candidate = _candidate(
        source,
        document_type="portfolio_disclosure",
        url="https://www.pgimindia.com/mutual-funds/disclosures/Portfolios/assets/pdf/Readyrecknoner.pdf",
        report_month=None,
    )

    errors, _warnings = validate_candidate(source, candidate, expected_month=date(2026, 7, 1))

    assert "portfolio_disclosure_report_month_unknown" in errors


def test_a_portfolio_that_states_its_month_is_accepted():
    source = get_source("pgim")
    candidate = _candidate(
        source,
        document_type="portfolio_disclosure",
        url="https://www.pgimindia.com/mutual-funds/disclosures/Portfolios/monthly-portfolio-july-2026.pdf",
        report_month=date(2026, 7, 1),
    )

    errors, _warnings = validate_candidate(source, candidate, expected_month=date(2026, 7, 1))

    assert errors == []


def test_a_factsheet_with_no_month_is_still_only_a_warning():
    """Several AMCs publish a factsheet whose month is confirmable only from the PDF
    body, and the Edelweiss discovery path clears report_month deliberately for that
    reason -- so the gate must not extend to factsheets."""
    source = get_source("edelweiss")
    candidate = _candidate(
        source,
        document_type="factsheet",
        url="https://www.edelweissmf.com/downloads/Edelweiss_Factsheet.pdf",
        report_month=None,
    )

    errors, warnings = validate_candidate(source, candidate, expected_month=date(2026, 7, 1))

    assert errors == []
    assert "report_month_unknown" in warnings
