from __future__ import annotations

from datetime import date
from io import BytesIO
from zipfile import ZipFile

from openpyxl import Workbook

from app.mf_ingestion.agents.validation import inspect_parser_smoke
from app.mf_ingestion.downloaders.amc_downloader import _discover_uti_documents
from app.mf_ingestion.downloaders.base_downloader import DownloadedDocument
from app.mf_ingestion.sources.registry import get_source


def _uti_workbook(*, report_month: date | None, portfolio_disclosure: bool) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    if portfolio_disclosure:
        sheet.append(["SCHEME: UTI - Large Cap Fund"])
    else:
        sheet.append(["Risk-o-meter for UTI funds"])
    if report_month and portfolio_disclosure:
        sheet.append(
            [
                "PROVISIONAL AND UNAUDITED PORTFOLIO DISCLOSURE AS OF "
                f"31/{report_month.month:02d}/{report_month.year}"
            ]
        )
    excel = BytesIO()
    workbook.save(excel)
    return excel.getvalue()


def _uti_portfolio_zip(*, report_month: date | None) -> bytes:
    holdings_workbook = _uti_workbook(report_month=report_month, portfolio_disclosure=True)
    unrelated_workbook = _uti_workbook(report_month=None, portfolio_disclosure=False)

    archive = BytesIO()
    with ZipFile(archive, "w") as zip_file:
        zip_file.writestr("Divmast.xls", unrelated_workbook)
        zip_file.writestr("Futures Disclosure.xls", unrelated_workbook)
        zip_file.writestr("Risk-o-meter.xlsx", unrelated_workbook)
        zip_file.writestr("Sebi Exposure as on 31 Jul 2026.xlsx", holdings_workbook)
    return archive.getvalue()


def _downloaded_zip(payload: bytes) -> DownloadedDocument:
    return DownloadedDocument(
        amc_name="UTI Mutual Fund",
        amc_code="UTI",
        document_type="portfolio_disclosure",
        source_url="https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-08/uti-july.zip",
        discovery_page_url="https://www.utimf.com/downloads",
        file_name="uti-july.zip",
        file_ext=".zip",
        report_month=date(2026, 7, 1),
        content_type="application/zip",
        file_size_bytes=len(payload),
        file_bytes=payload,
    )


def test_uti_portfolio_zip_smoke_confirms_the_embedded_holdings_month() -> None:
    errors, detected = inspect_parser_smoke(
        _downloaded_zip(_uti_portfolio_zip(report_month=date(2026, 7, 1))),
        expected_report_month=date(2026, 7, 1),
    )

    assert errors == []
    assert detected == date(2026, 7, 1)


def test_uti_portfolio_zip_smoke_rejects_a_package_without_holdings_disclosure() -> None:
    archive = BytesIO()
    with ZipFile(archive, "w") as zip_file:
        zip_file.writestr(
            "Risk-o-meter.xlsx",
            _uti_workbook(report_month=None, portfolio_disclosure=False),
        )

    errors, detected = inspect_parser_smoke(
        _downloaded_zip(archive.getvalue()),
        expected_report_month=date(2026, 7, 1),
    )

    assert errors == ["parser_smoke_uti_zip_portfolio_member_missing"]
    assert detected is None


def test_uti_discovery_keeps_english_factsheets_and_the_consolidated_portfolio_only(monkeypatch) -> None:
    class _Response:
        def __init__(self, rows: list[dict]) -> None:
            self._rows = rows

        def json(self) -> dict:
            return {"rows": self._rows}

    factsheet_rows = [
        {
            "name": "UTI Fund Watch(Active)-July 2026",
            "doc": "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-07/active.pdf",
        },
        {
            "name": "UTI Fund Watch(Passive)-July 2026",
            "doc": "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-07/passive.pdf",
        },
        {
            "name": "UTI Fund Watch(Active)-July 2026 Hindi",
            "doc": "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-07/active-hindi.pdf",
        },
    ]
    portfolio_rows = [
        {
            "name": "Risk-o-meter July 2026",
            "category": "Risk disclosure",
            "doc": "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-08/risk.zip",
        },
        {
            "name": "Consolidated Portfolio July 2026",
            "category": "Consolidate portfolio disclosure",
            "doc": "https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-08/portfolio.zip",
        },
    ]

    def _request(_method: str, endpoint: str, **_kwargs):
        return _Response(factsheet_rows if endpoint.endswith("get-fact-sheet") else portfolio_rows)

    monkeypatch.setattr("app.mf_ingestion.downloaders.amc_downloader._request_with_retry", _request)
    monkeypatch.setattr(
        "app.mf_ingestion.downloaders.amc_downloader._recent_month_starts",
        lambda *_args, **_kwargs: [date(2026, 7, 1)],
    )
    source = get_source("uti")

    factsheets = _discover_uti_documents(source, "factsheet", 5, "test")
    portfolios = _discover_uti_documents(source, "portfolio_disclosure", 5, "test")

    assert [document.title for document in factsheets] == [
        "UTI Fund Watch(Active)-July 2026",
        "UTI Fund Watch(Passive)-July 2026",
    ]
    assert {document.report_month for document in factsheets} == {date(2026, 6, 1)}
    assert [document.title for document in portfolios] == ["Consolidated Portfolio July 2026"]
    assert portfolios[0].report_month == date(2026, 7, 1)
