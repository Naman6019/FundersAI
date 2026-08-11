from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from app.mf_ingestion.parsers.adapters.aditya_birla_adapter import AdityaBirlaAdapter
from app.mf_ingestion.parsers.adapters.axis_adapter import AxisAdapter
from app.mf_ingestion.parsers.adapters.dsp_adapter import DSPAdapter
from app.mf_ingestion.parsers.adapters.hdfc_adapter import HDFCAdapter
from app.mf_ingestion.parsers.adapters.icici_adapter import ICICIAdapter
from app.mf_ingestion.parsers.adapters.kotak_adapter import KotakAdapter
from app.mf_ingestion.parsers.adapters.mirae_adapter import MiraeAdapter
from app.mf_ingestion.parsers.adapters.motilal_adapter import MotilalAdapter
from app.mf_ingestion.parsers.adapters.nippon_adapter import NipponAdapter
from app.mf_ingestion.parsers.adapters.ppfas_adapter import PPFASAdapter
from app.mf_ingestion.parsers.adapters.sbi_adapter import SBIAdapter
from app.mf_ingestion.parsers.adapters.uti_adapter import UTIAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser
from app.mf_ingestion.parsers.pdf_table_parser import PDFTableParser


REPO_ROOT = Path(__file__).resolve().parents[2]
AMC_DATA = REPO_ROOT / "AMC Data"
APRIL_2026 = date(2026, 4, 1)


def _require_golden_fixture(path: Path) -> None:
    if os.getenv("RUN_MF_GOLDEN_TESTS", "").strip().lower() not in {"1", "true", "yes", "on"}:
        pytest.skip("set RUN_MF_GOLDEN_TESTS=true to run local AMC Data golden tests")
    if not path.exists():
        pytest.skip(f"local fixture not found: {path}")


def _context(source_document_id: str, report_month: date = APRIL_2026) -> ParseContext:
    return ParseContext(source_document_id=source_document_id, source_url="local://golden-fixture", report_month=report_month)


def _find_doc(docs: list[ParsedDocument], scheme_fragment: str) -> ParsedDocument:
    fragment = scheme_fragment.lower()
    for doc in docs:
        if fragment in str(doc.scheme_name or "").lower():
            return doc
    raise AssertionError(f"scheme not parsed: {scheme_fragment}")


def _has_holding(doc: ParsedDocument, instrument_fragment: str) -> bool:
    fragment = instrument_fragment.lower()
    return any(fragment in str(row.get("instrument_name") or "").lower() for row in doc.holdings)


def test_hdfc_factsheet_parses_portfolio_pages_after_index() -> None:
    fixture = AMC_DATA / "HDFC" / "HDFC MF Factsheet - April 2026.pdf"
    _require_golden_fixture(fixture)

    frames = PDFTableParser().extract_tables(str(fixture), page_numbers={7, 9, 11})
    docs = HoldingsParser(HDFCAdapter())._parse_pdf_frames_individually(frames, _context("golden-hdfc"))

    assert len(docs) >= 3
    assert {doc.report_month for doc in docs} == {APRIL_2026}
    large_cap = _find_doc(docs, "HDFC Large Cap Fund")
    assert len(large_cap.holdings) >= 30
    assert _has_holding(large_cap, "ICICI Bank")
    assert _has_holding(large_cap, "HDFC Bank")
    assert not _has_holding(large_cap, "performance")
    assert not _has_holding(large_cap, "glossary")


def test_icici_april_2026_scheme_workbook_parses_holdings() -> None:
    fixture = (
        AMC_DATA
        / "ICICI"
        / "Monthly-Portfolio-Disclosure-April-2026"
        / "ICICI Prudential Banking & Financial Services Fund.xlsx"
    )
    _require_golden_fixture(fixture)

    docs = HoldingsParser(ICICIAdapter()).parse_many(str(fixture), _context("golden-icici"))

    assert len(docs) == 1
    doc = docs[0]
    assert doc.scheme_name == "ICICI Prudential Banking & Financial Services Fund"
    assert doc.report_month == APRIL_2026
    assert len(doc.holdings) >= 40
    assert _has_holding(doc, "ICICI Bank")
    assert 90.0 <= float(doc.metrics["total_percent_aum"]) <= 110.0


def test_sbi_april_2026_monthly_workbook_parses_multiple_schemes() -> None:
    fixture = AMC_DATA / "SBI" / "All-Schemes-Monthly-Portfolio---as-on-30th-April-2026.xlsx"
    _require_golden_fixture(fixture)

    docs = HoldingsParser(SBIAdapter()).parse_many(str(fixture), _context("golden-sbi"))

    assert len(docs) >= 50
    large_mid = _find_doc(docs, "SBI Large and Midcap Fund")
    assert large_mid.report_month == APRIL_2026
    assert len(large_mid.holdings) >= 70
    assert _has_holding(large_mid, "HDFC Bank")
    assert all(row.get("isin") for row in large_mid.holdings[:10])


def test_ppfas_april_2026_portfolio_workbook_parses_expected_rows() -> None:
    fixture = AMC_DATA / "PPFA" / "PPFAS_Monthly_Portfolio_Report_April_30_2026.xls"
    _require_golden_fixture(fixture)

    docs = HoldingsParser(PPFASAdapter()).parse_many(str(fixture), _context("golden-ppfas"))

    assert len(docs) >= 7
    flexi_cap = _find_doc(docs, "Parag Parikh Flexi Cap Fund")
    assert flexi_cap.report_month == APRIL_2026
    assert len(flexi_cap.holdings) >= 100
    assert _has_holding(flexi_cap, "HDFC Bank")
    assert 90.0 <= float(flexi_cap.metrics["total_percent_aum"]) <= 110.0


# --- Pending golden fixtures -------------------------------------------------
# mirae, uti and aditya_birla are in PRODUCTION_TARGET_AMC_KEYS (see
# sources/registry.py) but have no dedicated parser test yet -- these were
# never exercised against a real document. Fixture path/filename below is a
# placeholder; once the current AMC document is dropped into `AMC Data/<AMC>/`,
# fix the path and tighten the assertions (exact scheme name, real holding
# count/name) the same way test_hdfc_factsheet_parses_portfolio_pages_after_index
# etc. above do -- they're deliberately generic (band + shape only) until then.
PENDING_REPORT_MONTH = date(2026, 6, 1)  # placeholder -- match the real document's report month


def test_mirae_portfolio_workbook_parses_holdings() -> None:
    fixture = AMC_DATA / "MIRAE" / "TODO-fill-in-actual-filename.xlsx"
    _require_golden_fixture(fixture)

    docs = HoldingsParser(MiraeAdapter()).parse_many(
        str(fixture), _context("golden-mirae", PENDING_REPORT_MONTH)
    )

    assert docs
    for doc in docs:
        assert doc.holdings
        assert 90.0 <= float(doc.metrics.get("total_percent_aum") or 0.0) <= 110.0


def test_uti_portfolio_workbook_parses_holdings() -> None:
    fixture = AMC_DATA / "UTI" / "TODO-fill-in-actual-filename.xlsx"
    _require_golden_fixture(fixture)

    docs = HoldingsParser(UTIAdapter()).parse_many(
        str(fixture), _context("golden-uti", PENDING_REPORT_MONTH)
    )

    assert docs
    for doc in docs:
        assert doc.holdings
        assert 90.0 <= float(doc.metrics.get("total_percent_aum") or 0.0) <= 110.0


def test_aditya_birla_portfolio_workbook_parses_holdings() -> None:
    fixture = AMC_DATA / "ABSL" / "TODO-fill-in-actual-filename.xlsx"
    _require_golden_fixture(fixture)

    docs = HoldingsParser(AdityaBirlaAdapter()).parse_many(
        str(fixture), _context("golden-aditya-birla", PENDING_REPORT_MONTH)
    )

    assert docs
    for doc in docs:
        assert doc.holdings
        assert 90.0 <= float(doc.metrics.get("total_percent_aum") or 0.0) <= 110.0


# axis, nippon and dsp already have dedicated parser tests (test_axis_parser_prod_ready.py,
# test_nippon_parser.py, test_dsp_holdings_parser.py) but only against hand-built/synthetic
# frames, never a real current-format document -- adding them here too so a stale AMC
# template shows up here first instead of only surfacing later as a promotion-review
# conflict.
def test_axis_factsheet_parses_holdings() -> None:
    fixture = AMC_DATA / "AXIS" / "TODO-fill-in-actual-filename.pdf"
    _require_golden_fixture(fixture)

    docs = HoldingsParser(AxisAdapter()).parse_many(
        str(fixture), _context("golden-axis", PENDING_REPORT_MONTH)
    )

    assert docs
    for doc in docs:
        assert doc.holdings
        assert 90.0 <= float(doc.metrics.get("total_percent_aum") or 0.0) <= 110.0


def test_nippon_portfolio_workbook_parses_holdings() -> None:
    fixture = AMC_DATA / "NIPPON" / "TODO-fill-in-actual-filename.xlsx"
    _require_golden_fixture(fixture)

    docs = HoldingsParser(NipponAdapter()).parse_many(
        str(fixture), _context("golden-nippon", PENDING_REPORT_MONTH)
    )

    assert docs
    for doc in docs:
        assert doc.holdings
        assert 90.0 <= float(doc.metrics.get("total_percent_aum") or 0.0) <= 110.0


def test_dsp_portfolio_workbook_parses_holdings() -> None:
    fixture = AMC_DATA / "DSP" / "TODO-fill-in-actual-filename.xlsx"
    _require_golden_fixture(fixture)

    docs = HoldingsParser(DSPAdapter()).parse_many(
        str(fixture), _context("golden-dsp", PENDING_REPORT_MONTH)
    )

    assert docs
    for doc in docs:
        assert doc.holdings
        assert 90.0 <= float(doc.metrics.get("total_percent_aum") or 0.0) <= 110.0


# motilal and kotak stage holdings straight off the factsheet PDF via
# combined_factsheet_portfolio.parse_combined_factsheet_pdf (see
# test_combined_factsheet_portfolio.py for the parser-internals-level regression
# coverage of that path) -- this is the missing real-document, adapter-level layer
# on top of it.
def test_motilal_factsheet_parses_holdings() -> None:
    fixture = AMC_DATA / "MOTILAL" / "TODO-fill-in-actual-filename.pdf"
    _require_golden_fixture(fixture)

    docs = MotilalAdapter().parse_pdf_file_many(
        str(fixture), _context("golden-motilal", PENDING_REPORT_MONTH)
    )

    assert docs
    for doc in docs:
        assert doc.holdings
        assert 90.0 <= float(doc.metrics.get("total_percent_aum") or 0.0) <= 110.0


def test_kotak_factsheet_parses_holdings() -> None:
    fixture = AMC_DATA / "KOTAK" / "TODO-fill-in-actual-filename.pdf"
    _require_golden_fixture(fixture)

    docs = KotakAdapter().parse_pdf_file_many(
        str(fixture), _context("golden-kotak", PENDING_REPORT_MONTH)
    )

    assert docs
    for doc in docs:
        assert doc.holdings
        assert 90.0 <= float(doc.metrics.get("total_percent_aum") or 0.0) <= 110.0
