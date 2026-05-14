from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from app.mf_ingestion.downloaders.base_downloader import DownloadedDocument, DiscoveredDocument
from app.mf_ingestion.parsers.adapters import ppfas_adapter
from app.mf_ingestion.parsers.adapters.ppfas_adapter import (
    PPFASAdapter,
    build_confirmation_payload,
    classify_documents,
    extract_anchor_links,
)
from app.mf_ingestion.services.ingestion_service import IngestionService
from app.mf_ingestion.sources.registry import AMCDocumentSource


def _ppfas_source() -> AMCDocumentSource:
    return AMCDocumentSource(
        amc_name="Parag Parikh Mutual Fund",
        amc_code="PPFAS",
        adapter_key="ppfas",
        factsheet_page_url="https://amc.ppfas.com/downloads/index.php",
        portfolio_disclosure_page_url="https://amc.ppfas.com/statutory-disclosures/index.php",
        requires_confirmation=True,
        confirmation_type="indian_citizen_confirmation",
        confirmation_notes="test",
        enabled=True,
    )


def test_confirmation_detection_from_sample_html():
    adapter = PPFASAdapter()
    html = "<html><body><h1>Confirm you are an Indian citizen</h1></body></html>"
    assert adapter.has_indian_citizen_confirmation(html) is True


def test_confirmation_form_payload_preserves_hidden_and_checked_inputs():
    soup = ppfas_adapter.BeautifulSoup(
        """
        <form method='post' action='/confirm'>
          <input type='hidden' name='token' value='abc123'>
          <input type='radio' name='eligible' value='yes' checked>
          <input type='radio' name='eligible' value='no'>
          <input type='submit' name='submit' value='Proceed'>
        </form>
        """,
        "html.parser",
    )
    form = soup.find("form")
    payload = build_confirmation_payload(form)
    assert payload == {"token": "abc123", "eligible": "yes", "submit": "Proceed"}


def test_relative_url_resolution_from_anchors():
    html = """
    <html><body>
      <a href="../docs/factsheet-apr-2026.xlsx">Monthly Factsheet Apr 2026</a>
    </body></html>
    """
    links = extract_anchor_links("https://amc.ppfas.com/downloads/index.php", html)
    assert links[0]["url"] == "https://amc.ppfas.com/docs/factsheet-apr-2026.xlsx"


def test_factsheet_link_classification():
    source = _ppfas_source()
    links = [
        {
            "title": "Monthly Factsheet Apr 2026",
            "href": "factsheet-apr-2026.xlsx",
            "url": "https://amc.ppfas.com/downloads/factsheet-apr-2026.xlsx",
            "file_ext": ".xlsx",
        },
        {
            "title": "Notice",
            "href": "notice.pdf",
            "url": "https://amc.ppfas.com/downloads/notice.pdf",
            "file_ext": ".pdf",
        },
    ]
    docs = classify_documents(source, "factsheet", links, source.factsheet_page_url)
    assert len(docs) == 1
    assert docs[0].document_type == "factsheet"
    assert docs[0].report_month == date(2026, 4, 1)


def test_portfolio_link_classification():
    source = _ppfas_source()
    links = [
        {
            "title": "Monthly Portfolio Disclosure Apr 2026",
            "href": "portfolio-apr-2026.xls",
            "url": "https://amc.ppfas.com/statutory-disclosures/portfolio-apr-2026.xls",
            "file_ext": ".xls",
        },
        {
            "title": "Press Release",
            "href": "press.pdf",
            "url": "https://amc.ppfas.com/statutory-disclosures/press.pdf",
            "file_ext": ".pdf",
        },
    ]
    docs = classify_documents(source, "portfolio_disclosure", links, source.portfolio_disclosure_page_url)
    assert len(docs) == 1
    assert docs[0].document_type == "portfolio_disclosure"


def test_file_preference_ordering_xlsx_then_xls_then_csv_then_pdf():
    source = _ppfas_source()
    links = [
        {
            "title": "Monthly Factsheet Apr 2026 PDF",
            "href": "factsheet-apr-2026.pdf",
            "url": "https://amc.ppfas.com/downloads/factsheet-apr-2026.pdf",
            "file_ext": ".pdf",
        },
        {
            "title": "Monthly Factsheet Apr 2026 XLSX",
            "href": "factsheet-apr-2026.xlsx",
            "url": "https://amc.ppfas.com/downloads/factsheet-apr-2026.xlsx",
            "file_ext": ".xlsx",
        },
        {
            "title": "Monthly Factsheet Apr 2026 CSV",
            "href": "factsheet-apr-2026.csv",
            "url": "https://amc.ppfas.com/downloads/factsheet-apr-2026.csv",
            "file_ext": ".csv",
        },
        {
            "title": "Monthly Factsheet Apr 2026 XLS",
            "href": "factsheet-apr-2026.xls",
            "url": "https://amc.ppfas.com/downloads/factsheet-apr-2026.xls",
            "file_ext": ".xls",
        },
    ]
    docs = classify_documents(source, "factsheet", links, source.factsheet_page_url)
    docs.sort(key=lambda item: item.priority_score, reverse=True)
    assert [doc.file_ext for doc in docs] == [".xlsx", ".xls", ".csv", ".pdf"]


class _FakeSupabase:
    def __init__(self) -> None:
        self.inserts = []
        self.upserts = []

    def table(self, table_name: str):
        return _FakeTable(self, table_name)


class _FakeTable:
    def __init__(self, root: _FakeSupabase, table_name: str) -> None:
        self.root = root
        self.table_name = table_name
        self._selected = None
        self._eq_filters = {}

    def select(self, selected: str):
        self._selected = selected
        return self

    def eq(self, key: str, value):
        self._eq_filters[key] = value
        return self

    def limit(self, value: int):
        return self

    def upsert(self, payload, on_conflict=None):
        self.root.upserts.append((self.table_name, payload, on_conflict))
        return self

    def insert(self, payload):
        self.root.inserts.append((self.table_name, payload))
        return self

    def execute(self):
        if self.table_name == "mf_raw_documents" and self._eq_filters.get("checksum") == "dup-checksum":
            return SimpleNamespace(data=[{"id": "existing-doc-id"}])
        if self.table_name == "mf_raw_documents" and self.root.inserts:
            return SimpleNamespace(data=[{"id": "new-doc-id"}])
        return SimpleNamespace(data=[])


class _FakeDownloader:
    def __init__(self, source, timeout_seconds: float, user_agent: str) -> None:
        self.source = source

    def list_documents(self, document_type: str):
        return [
            DiscoveredDocument(
                amc_name="Parag Parikh Mutual Fund",
                amc_code="PPFAS",
                document_type=document_type,
                title="Monthly Factsheet Apr 2026",
                url="https://amc.ppfas.com/downloads/factsheet-apr-2026.xlsx",
                discovery_page_url="https://amc.ppfas.com/downloads/index.php",
                file_ext=".xlsx",
                report_month=date(2026, 4, 1),
                priority_score=999,
            )
        ]

    def download(self, discovered: DiscoveredDocument):
        return DownloadedDocument(
            amc_name=discovered.amc_name,
            amc_code=discovered.amc_code,
            document_type=discovered.document_type,
            source_url=discovered.url,
            discovery_page_url=discovered.discovery_page_url,
            file_name="factsheet-apr-2026.xlsx",
            file_ext=".xlsx",
            report_month=discovered.report_month,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size_bytes=4,
            file_bytes=b"test",
        )


def test_duplicate_checksum_skip_behavior(monkeypatch):
    from app.mf_ingestion.services import ingestion_service

    fake_supabase = _FakeSupabase()
    monkeypatch.setattr(ingestion_service, "supabase", fake_supabase)
    monkeypatch.setattr(ingestion_service, "AMCDownloader", _FakeDownloader)
    monkeypatch.setattr(ingestion_service, "sha256_bytes", lambda b: "dup-checksum")

    service = IngestionService()
    service.raw_store = SimpleNamespace(save=lambda document, checksum: "C:/tmp/mock.bin")

    result = service.ingest_documents(amc="ppfas", document_type="factsheet", max_documents=1)

    assert result["skipped_documents"]
    assert result["skipped_documents"][0]["reason"] == "duplicate_checksum"
    assert not any(table == "mf_raw_documents" for table, _ in fake_supabase.inserts)


def test_confirmation_detected_without_form_raises_clear_error():
    adapter = PPFASAdapter()
    html = "<html><body><h2>Confirm you are an Indian citizen</h2></body></html>"
    with pytest.raises(RuntimeError) as exc:
        adapter.handle_confirmation(adapter.session, "https://amc.ppfas.com/downloads/index.php", html)
    assert "no standard HTML form was found" in str(exc.value)


def test_parse_holdings_extracts_real_rows_from_ppfas_style_excel_frame():
    frame = pd.DataFrame(
        [
            [None, None, None, None, None, None],
            [None, "Monthly Portfolio Statement as on April 30, 2026", None, None, None, None],
            [
                None,
                "Name of the Instrument",
                "ISIN",
                "Industry / Rating",
                "Market/Fair Value\n (Rs. in Lakhs)",
                "% to Net\n Assets",
            ],
            [None, "Equity & Equity related", None, None, None, None],
            [None, "HDFC Bank Limited", "INE040A01034", "Banks", 1119020.59, 0.0794],
            [None, "Coal India Limited", "INE522F01014", "Consumable Fuels", 838408.67, 0.0595],
            [None, "Sub Total", None, None, 1957429.26, 0.1389],
        ],
        columns=[
            "Unnamed: 0",
            "Parag Parikh Flexi Cap Fund (An open-ended dynamic equity scheme investing across large cap, mid-cap, small-cap stocks)",
            "Unnamed: 2",
            "Unnamed: 3",
            "Unnamed: 4",
            "Unnamed: 5",
        ],
    )
    adapter = PPFASAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-1", source_url="https://amc.ppfas.com", report_month=None),
    )

    assert parsed.scheme_name == "Parag Parikh Flexi Cap Fund"
    assert parsed.report_month == date(2026, 4, 1)
    assert len(parsed.holdings) == 2
    assert parsed.holdings[0]["isin"] == "INE040A01034"
    assert parsed.holdings[0]["percent_aum"] == 7.94
    assert parsed.metrics["total_percent_aum"] == 13.89
    assert parsed.confidence_score > 70


def test_parse_holdings_prefers_flexi_cap_sheet_when_document_has_multiple_sheets():
    flexi_cap = pd.DataFrame(
        [
            [None, "Monthly Portfolio Statement as on April 30, 2026", None, None, None],
            [None, "Name of the Instrument", "ISIN", "Industry / Rating", "% to Net Assets"],
            [None, "HDFC Bank Limited", "INE040A01034", "Banks", 0.0794],
        ],
        columns=["Unnamed: 0", "Parag Parikh Flexi Cap Fund", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4"],
    )
    liquid = pd.DataFrame(
        [
            [None, "Monthly Portfolio Statement as on April 30, 2026", None, None, None],
            [None, "Name of the Instrument", "ISIN", "Industry / Rating", "% to Net Assets"],
            [None, "7.4% National Housing Bank (16/07/2026)", "INE557F08FS6", "CRISIL AAA", 0.95],
        ],
        columns=["Unnamed: 0", "Parag Parikh Liquid Fund", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4"],
    )

    adapter = PPFASAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[liquid, flexi_cap],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-2", source_url="https://amc.ppfas.com", report_month=None),
    )

    assert parsed.scheme_name == "Parag Parikh Flexi Cap Fund"
    assert parsed.holdings[0]["instrument_name"] == "HDFC Bank Limited"
