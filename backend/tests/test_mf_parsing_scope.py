from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.mf_ingestion.services import parsing_service
from app.mf_ingestion.services.parsing_service import ParsingService, _source_month_from_text
from datetime import date


class _FakeSupabase:
    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs
        self.updated_rows: list[tuple[str, dict, dict]] = []

    def table(self, table_name: str):
        return _FakeTable(self, table_name)


class _FakeTable:
    def __init__(self, root: _FakeSupabase, table_name: str) -> None:
        self.root = root
        self.table_name = table_name
        self._eq_filters: dict[str, object] = {}
        self._in_filters: dict[str, list] = {}
        self._update_payload: dict | None = None

    def select(self, _selected: str):
        return self

    def in_(self, key: str, values):
        self._in_filters[key] = list(values)
        return self

    def eq(self, key: str, value):
        self._eq_filters[key] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, _value: int):
        return self

    def update(self, payload: dict):
        self._update_payload = payload
        return self

    def execute(self):
        if self.table_name == "mf_raw_documents" and self._update_payload is None:
            rows = list(self.root.docs)
            for key, values in self._in_filters.items():
                rows = [row for row in rows if row.get(key) in values]
            for key, value in self._eq_filters.items():
                rows = [row for row in rows if row.get(key) == value]
            return SimpleNamespace(data=rows)

        if self.table_name == "mf_raw_documents" and self._update_payload is not None:
            self.root.updated_rows.append((self.table_name, self._eq_filters, self._update_payload))
            return SimpleNamespace(data=[{"id": self._eq_filters.get("id")}])

        return SimpleNamespace(data=[])


def test_factsheet_document_uses_factsheet_path_and_marks_review_when_empty(monkeypatch, tmp_path: Path):
    fake_file = tmp_path / "factsheet.pdf"
    fake_file.write_bytes(b"%PDF-1.4 fake")
    fake_doc = {
        "id": "doc-factsheet-1",
        "amc_code": "ICICI",
        "document_type": "factsheet",
        "storage_path": str(fake_file),
        "parse_status": "pending",
    }
    fake_supabase = _FakeSupabase([fake_doc])
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    monkeypatch.setattr(parsing_service.FactsheetParser, "parse", lambda *_args, **_kwargs: [])

    service = ParsingService()
    result = service.parse_pending_documents(limit=1, amc_code="ICICI")

    assert result["count"] == 1
    assert result["processed"][0]["status"] == "needs_review"
    assert result["processed"][0]["reason"] == "factsheet_fields_not_extracted"
    assert fake_supabase.updated_rows
    _, eq_filters, update_payload = fake_supabase.updated_rows[0]
    assert eq_filters["id"] == "doc-factsheet-1"
    assert update_payload["parse_status"] == "needs_review"
    assert "factsheet_fields_not_extracted" in update_payload["validation_issues"]


def test_parse_pending_documents_matches_amc_code_case_insensitively(monkeypatch):
    fake_doc = {
        "id": "doc-lower-amc-1",
        "amc_code": "icici",
        "document_type": "factsheet",
        "storage_path": "ignored",
        "parse_status": "pending",
    }
    fake_supabase = _FakeSupabase([fake_doc])
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)

    service = ParsingService()
    result = service.parse_pending_documents(limit=1, amc_code="ICICI")

    assert result["count"] == 1
    assert result["processed"][0]["source_document_id"] == "doc-lower-amc-1"


def test_parse_pending_documents_skips_irrelevant_disclosure_urls(monkeypatch):
    fake_doc = {
        "id": "doc-sai-1",
        "amc_code": "SBI",
        "document_type": "factsheet",
        "source_url": "https://www.sbimf.com/docs/statement-of-additional-information.pdf",
        "storage_path": "ignored",
        "parse_status": "pending",
    }
    fake_supabase = _FakeSupabase([fake_doc])
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)

    service = ParsingService()
    result = service.parse_pending_documents(limit=1, amc_code="SBI")

    assert result["processed"][0]["status"] == "skipped"
    _, eq_filters, update_payload = fake_supabase.updated_rows[0]
    assert eq_filters["id"] == "doc-sai-1"
    assert update_payload["parse_status"] == "skipped_not_supported"
    assert update_payload["validation_issues"][0].startswith("skipped_irrelevant_document")


def test_parse_pending_documents_skips_report_month_mismatch(monkeypatch):
    fake_doc = {
        "id": "doc-old-icici-1",
        "amc_code": "ICICI",
        "document_type": "portfolio_disclosure",
        "report_month": "2024-12-01",
        "source_url": "https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/2020/liquid-portfolio-as-on-03-july-2020.xlsx",
        "file_name": "liquid-portfolio-as-on-03-july-2020.xlsx",
        "storage_path": "ignored",
        "parse_status": "pending",
    }
    fake_supabase = _FakeSupabase([fake_doc])
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)

    service = ParsingService()
    result = service.parse_pending_documents(limit=1, amc_code="ICICI")

    assert result["processed"][0]["status"] == "skipped"
    _, eq_filters, update_payload = fake_supabase.updated_rows[0]
    assert eq_filters["id"] == "doc-old-icici-1"
    assert update_payload["parse_status"] == "skipped_not_supported"
    assert update_payload["validation_issues"] == [
        "skipped_irrelevant_document:report_month_mismatch:2020-07-01!=2024-12-01"
    ]


def test_source_month_prefers_explicit_file_date_over_storage_folder():
    text = (
        "https://files.hdfcfund.com/s3fs-public/2026-05/"
        "Monthly%20HDFC%20Value%20Fund%20-%2030%20April%202026.xlsx"
    )

    assert _source_month_from_text(text) == date(2026, 4, 1)
