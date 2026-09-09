from __future__ import annotations

import pandas as pd
import pytest

from app.mf_ingestion.parsers.pdf_table_parser import (
    DEFAULT_MAX_SECONDS,
    PDFTableParser,
)


def test_default_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("MF_PDF_TABLE_MAX_SECONDS", "3.5")

    assert PDFTableParser().max_seconds == 3.5


@pytest.mark.parametrize("value", ["0", "-5", "", "not-a-number"])
def test_unusable_environment_values_fall_back_to_the_default(monkeypatch, value):
    """A misconfigured bound must not disable the bound -- an unbounded scan is the
    failure mode this limit exists to prevent."""
    monkeypatch.setenv("MF_PDF_TABLE_MAX_SECONDS", value)

    assert PDFTableParser().max_seconds == DEFAULT_MAX_SECONDS


def test_the_default_sits_clear_of_the_slowest_observed_successful_parse():
    """Pages are scanned in order, so a cut drops every scheme after it -- and the
    slowest documents are the large multi-scheme ones where that costs most. The
    slowest successful parse measured across R2 was LIC at 249.7s, so the bound has to
    sit well above that or it will cut documents that were about to finish."""
    assert DEFAULT_MAX_SECONDS >= 500.0


def test_there_is_no_page_cap():
    """Page count does not predict cost (0.1s-2.8s per page on the same corpus), so a
    page limit binds on cheap documents while missing expensive ones."""
    assert not hasattr(PDFTableParser(), "max_pages")


def test_explicit_arguments_win_over_the_environment(monkeypatch):
    monkeypatch.setenv("MF_PDF_TABLE_MAX_SECONDS", "500")

    assert PDFTableParser(max_seconds=7).max_seconds == 7


def test_a_long_document_is_scanned_in_full_when_it_fits_the_budget(monkeypatch):
    """A 258-page factsheet must not be cut merely for being long."""
    parser = PDFTableParser(max_seconds=600)
    _install_fake_pdf(monkeypatch, page_count=258)

    result = parser.extract_tables_with_status("fake.pdf")

    assert result.pages_scanned == 258
    assert not result.is_truncated


def test_time_limit_stops_the_scan_and_says_so(monkeypatch):
    parser = PDFTableParser(max_seconds=5)
    _install_fake_pdf(monkeypatch, page_count=10)
    # Each page costs two seconds of the budget.
    clock = iter([0.0] + [float(n) for n in range(0, 200, 2)])
    monkeypatch.setattr(
        "app.mf_ingestion.parsers.pdf_table_parser.time.monotonic",
        lambda: next(clock),
    )

    result = parser.extract_tables_with_status("fake.pdf")

    assert result.is_truncated
    assert result.truncated_reason.startswith("time_limit_reached:")
    assert result.pages_scanned < 10


def test_a_document_inside_both_bounds_is_not_reported_as_truncated(monkeypatch):
    parser = PDFTableParser(max_seconds=600)
    _install_fake_pdf(monkeypatch, page_count=4)

    result = parser.extract_tables_with_status("fake.pdf")

    assert result.pages_scanned == 4
    assert not result.is_truncated
    assert result.truncated_reason is None


def test_extract_tables_still_returns_a_plain_frame_list(monkeypatch):
    """The original signature stays intact for existing callers."""
    parser = PDFTableParser(max_seconds=600)
    _install_fake_pdf(monkeypatch, page_count=2)

    frames = parser.extract_tables("fake.pdf")

    assert isinstance(frames, list)
    assert all(isinstance(frame, pd.DataFrame) for frame in frames)


class _FakePage:
    def __init__(self, number: int) -> None:
        self.page_number = number

    def extract_words(self, **_kwargs):
        return []

    def extract_tables(self):
        return []


class _FakePdf:
    def __init__(self, page_count: int) -> None:
        self.pages = [_FakePage(n + 1) for n in range(page_count)]

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class _FakeFitzPage:
    def get_text(self, _kind):
        return "text"


class _FakeFitzDoc:
    def __getitem__(self, _index):
        return _FakeFitzPage()

    def close(self):
        return None


def _install_fake_pdf(monkeypatch, *, page_count: int) -> None:
    import fitz

    monkeypatch.setattr(
        "app.mf_ingestion.parsers.pdf_table_parser.pdfplumber.open",
        lambda _path: _FakePdf(page_count),
    )
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeFitzDoc())


def test_truncated_extraction_forces_the_document_into_review(monkeypatch):
    """A bounded scan that stopped early has seen only part of the document, so
    anything it parsed is an incomplete portfolio. ParseBatchResult.has_failures is
    what routes a document to review, and a partial holdings table must never be
    staged as a complete one."""
    from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
    from app.mf_ingestion.parsers.holdings_parser import HoldingsParser
    from app.mf_ingestion.parsers.pdf_table_parser import TableExtractionResult

    class _Adapter:
        amc_code = "TEST"

        def parse_pdf_frame_many(self, _frame, _context):
            return [
                ParsedDocument(
                    scheme_name="Test Fund",
                    report_month=None,
                    holdings=[{"instrument_name": "HDFC Bank Ltd", "percent_aum": 5.0}],
                )
            ]

        def parse_holdings(self, *_args, **_kwargs):
            raise AssertionError("not reached")

    parser = HoldingsParser(_Adapter())
    frame = pd.DataFrame({"Name of Instrument": ["HDFC Bank Ltd"]})
    monkeypatch.setattr(
        parser.pdf_table_parser,
        "extract_tables_with_status",
        lambda *_a, **_k: TableExtractionResult(
            frames=[frame],
            truncated_reason="time_limit_reached:240s",
            pages_scanned=90,
            pages_total=170,
        ),
    )

    batch = parser.parse_batch("fake.pdf", ParseContext(source_document_id="d", source_url="u", report_month=None))

    assert batch.records, "rows parsed before the cut-off are still returned"
    assert batch.has_failures, "a truncated scan must route the document to review"
    assert "pdf_table_extraction_truncated" in {d.code for d in batch.diagnostics}


def test_untruncated_extraction_does_not_add_a_failure(monkeypatch):
    from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
    from app.mf_ingestion.parsers.holdings_parser import HoldingsParser
    from app.mf_ingestion.parsers.pdf_table_parser import TableExtractionResult

    class _Adapter:
        amc_code = "TEST"

        def parse_pdf_frame_many(self, _frame, _context):
            return [ParsedDocument(scheme_name="Test Fund", report_month=None, holdings=[{"instrument_name": "X", "percent_aum": 1.0}])]

        def parse_holdings(self, *_args, **_kwargs):
            raise AssertionError("not reached")

    parser = HoldingsParser(_Adapter())
    monkeypatch.setattr(
        parser.pdf_table_parser,
        "extract_tables_with_status",
        lambda *_a, **_k: TableExtractionResult(
            frames=[pd.DataFrame({"Name of Instrument": ["X"]})],
            truncated_reason=None,
            pages_scanned=12,
            pages_total=12,
        ),
    )

    batch = parser.parse_batch("fake.pdf", ParseContext(source_document_id="d", source_url="u", report_month=None))

    assert batch.records
    assert not batch.has_failures
