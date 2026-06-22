from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument, DownloadedDocument
from app.mf_ingestion.services.document_classifier import classify_raw_document
from app.mf_ingestion.services.ingestion_service import IngestionService
from app.mf_ingestion.services.parsing_service import ParsingService
from app.mf_ingestion.services.source_manifest import load_source_manifest_documents


class _FakeSupabase:
    def __init__(self, docs: list[dict] | None = None) -> None:
        self.docs = docs or []
        self.inserts: list[tuple[str, dict]] = []
        self.upserts: list[tuple[str, dict, str | None]] = []
        self.updates: list[tuple[str, dict, dict]] = []

    def table(self, table_name: str):
        return _FakeTable(self, table_name)


class _FakeTable:
    def __init__(self, root: _FakeSupabase, table_name: str) -> None:
        self.root = root
        self.table_name = table_name
        self._eq: dict[str, object] = {}
        self._in: dict[str, list[object]] = {}
        self._update_payload: dict | None = None
        self._insert_payload: dict | None = None

    def select(self, _selected: str):
        return self

    def eq(self, key: str, value):
        self._eq[key] = value
        return self

    def in_(self, key: str, values):
        self._in[key] = list(values)
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, _value: int):
        return self

    def insert(self, payload: dict):
        self._insert_payload = payload
        self.root.inserts.append((self.table_name, payload))
        return self

    def upsert(self, payload: dict, on_conflict: str | None = None):
        self.root.upserts.append((self.table_name, payload, on_conflict))
        return self

    def update(self, payload: dict):
        self._update_payload = payload
        return self

    def delete(self):
        return self

    def execute(self):
        if self._insert_payload is not None:
            return SimpleNamespace(data=[{"id": "review-1", **self._insert_payload}])
        if self.table_name == "mf_raw_documents" and self._update_payload is None:
            rows = list(self.root.docs)
            for key, values in self._in.items():
                rows = [row for row in rows if row.get(key) in values]
            for key, value in self._eq.items():
                rows = [row for row in rows if row.get(key) == value]
            if "checksum" in self._eq:
                return SimpleNamespace(data=[])
            return SimpleNamespace(data=rows)
        if self.table_name == "mf_raw_documents" and self._update_payload is not None:
            self.root.updates.append((self.table_name, dict(self._eq), dict(self._update_payload)))
            return SimpleNamespace(data=[{"id": self._eq.get("id")}])
        return SimpleNamespace(data=[])


class _FakeR2Enabled:
    enabled = True

    def upload_bytes(self, key: str, content: bytes, *, bucket=None, content_type=None, metadata=None):
        return {"bucket": bucket or "raw-bucket", "key": key}


class _FakeR2Disabled:
    enabled = False

    def __init__(self, *args, **kwargs) -> None:
        pass


class _ManifestDownloader:
    def __init__(self, source, timeout_seconds: float, user_agent: str) -> None:
        self.source = source

    def list_documents(self, document_type: str):
        raise RuntimeError("live_discovery_blocked")

    def download(self, discovered: DiscoveredDocument):
        return DownloadedDocument(
            amc_name=discovered.amc_name,
            amc_code=discovered.amc_code,
            document_type=discovered.document_type,
            source_url=discovered.url,
            discovery_page_url=discovered.discovery_page_url,
            file_name="ppfas-apr-2026.xlsx",
            file_ext=discovered.file_ext,
            report_month=discovered.report_month,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size_bytes=4,
            file_bytes=b"test",
        )


def test_source_manifest_loads_exact_official_documents(tmp_path: Path):
    manifest = tmp_path / "mf-source-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "amc": "PPFAS",
                        "document_type": "portfolio_disclosure",
                        "report_month": "2026-04",
                        "source_url": "https://amc.ppfas.com/official/portfolio-apr-2026.xlsx",
                        "expected_file_type": ".xlsx",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    from app.mf_ingestion.sources.registry import get_source

    docs = load_source_manifest_documents(str(manifest), get_source("ppfas"), "portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].url.endswith("portfolio-apr-2026.xlsx")
    assert docs[0].report_month == date(2026, 4, 1)
    assert docs[0].file_ext == ".xlsx"


def test_ingestion_prefers_manifest_when_live_discovery_fails(monkeypatch, tmp_path: Path):
    from app.mf_ingestion.services import ingestion_service

    manifest = tmp_path / "mf-source-manifest.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "amc": "PPFAS",
                    "document_type": "factsheet",
                    "report_month": "2026-04-01",
                    "source_url": "https://amc.ppfas.com/official/factsheet-apr-2026.xlsx",
                    "expected_file_type": ".xlsx",
                }
            ]
        ),
        encoding="utf-8",
    )
    fake_supabase = _FakeSupabase()
    monkeypatch.setenv("MF_SOURCE_MANIFEST_PATH", str(manifest))
    monkeypatch.setattr(ingestion_service, "supabase", fake_supabase)
    monkeypatch.setattr(ingestion_service, "AMCDownloader", _ManifestDownloader)
    monkeypatch.setattr(ingestion_service, "R2Store", lambda *args, **kwargs: _FakeR2Enabled())
    monkeypatch.setattr(ingestion_service, "sha256_bytes", lambda _bytes: "manifest-checksum")

    result = IngestionService().ingest_documents("ppfas", "factsheet", max_documents=1)

    assert result["status"] == "ok"
    raw_insert = [payload for table, payload in fake_supabase.inserts if table == "mf_raw_documents"][0]
    source_manifest = raw_insert["storage_metadata"]["source_manifest"]
    assert source_manifest["source_url"].endswith("factsheet-apr-2026.xlsx")
    assert source_manifest["checksum"] == "manifest-checksum"
    assert source_manifest["acquisition_status"] == "acquired"


def test_classifier_marks_supported_factsheet_and_unsupported_adapter():
    factsheet = classify_raw_document(
        {"amc_code": "ICICI", "document_type": "factsheet", "file_name": "factsheet.pdf"},
        {"icici"},
    )
    missing_adapter = classify_raw_document(
        {"amc_code": "UNKNOWN", "document_type": "portfolio_disclosure", "file_name": "portfolio.xlsx"},
        {"icici"},
    )

    assert factsheet.supported_parser is True
    assert factsheet.file_shape == "pdf"
    assert missing_adapter.supported_parser is False
    assert "adapter_not_found:unknown" in missing_adapter.issues


def test_llm_fallback_creates_review_only_payload(monkeypatch, tmp_path: Path):
    from app.mf_ingestion.services import parsing_service, review_service

    raw_file = tmp_path / "factsheet.txt"
    raw_file.write_text("messy official factsheet text", encoding="utf-8")
    fixture = tmp_path / "llm-output.json"
    fixture.write_text(
        json.dumps(
            {
                "scheme_name": "ICICI Prudential Multi Asset Fund",
                "report_month": "2026-04-01",
                "holdings": [{"instrument_name": "HDFC Bank Ltd", "percent_aum": 100.0}],
                "aum": 1000.0,
                "expense_ratio": 0.8,
                "benchmark": "NIFTY 50 Hybrid Composite Debt 50:50 Index",
                "fund_manager": "Test Manager",
                "risk_level": "Very High",
                "source_document_id": "doc-llm-1",
                "extractor_type": "llm",
                "confidence_score": 95.0,
                "validation_issues": [],
            }
        ),
        encoding="utf-8",
    )
    fake_supabase = _FakeSupabase(
        [
            {
                "id": "doc-llm-1",
                "amc_code": "ICICI",
                "document_type": "factsheet",
                "storage_path": str(raw_file),
                "parse_status": "pending",
                "parser_version": "test",
            }
        ]
    )
    monkeypatch.setenv("MF_EXTRACTOR_MODE", "deterministic_then_llm")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_ENABLED", "true")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_MODEL", "test-model")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_FIXTURE_PATH", str(fixture))
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    monkeypatch.setattr(review_service, "supabase", fake_supabase)
    monkeypatch.setattr(parsing_service, "R2Store", _FakeR2Disabled)
    monkeypatch.setattr(parsing_service.FactsheetParser, "parse", lambda *_args, **_kwargs: [])

    result = ParsingService().parse_pending_documents(limit=1, amc_code="ICICI")

    assert result["processed"][0]["status"] == "fallback_needs_review"
    assert result["processed"][0]["extractor_type"] == "llm"
    assert any(table == "mf_parse_review_queue" for table, _payload in fake_supabase.inserts)
    assert not any(table in {"mutual_fund_holdings", "mutual_fund_core_snapshot"} for table, *_ in fake_supabase.upserts)


def test_invalid_llm_payload_falls_back_to_needs_review(monkeypatch, tmp_path: Path):
    from app.mf_ingestion.services import parsing_service, review_service

    raw_file = tmp_path / "factsheet.txt"
    raw_file.write_text("messy official factsheet text", encoding="utf-8")
    fixture = tmp_path / "bad-llm-output.json"
    fixture.write_text(json.dumps({"scheme_name": "", "extractor_type": "llm"}), encoding="utf-8")
    fake_supabase = _FakeSupabase(
        [
            {
                "id": "doc-bad-llm-1",
                "amc_code": "ICICI",
                "document_type": "factsheet",
                "storage_path": str(raw_file),
                "parse_status": "pending",
            }
        ]
    )
    monkeypatch.setenv("MF_EXTRACTOR_MODE", "deterministic_then_llm")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_ENABLED", "true")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_MODEL", "test-model")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_FIXTURE_PATH", str(fixture))
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    monkeypatch.setattr(review_service, "supabase", fake_supabase)
    monkeypatch.setattr(parsing_service, "R2Store", _FakeR2Disabled)
    monkeypatch.setattr(parsing_service.FactsheetParser, "parse", lambda *_args, **_kwargs: [])

    result = ParsingService().parse_pending_documents(limit=1, amc_code="ICICI")

    assert result["processed"][0]["status"] == "needs_review"
    assert not any(table in {"mutual_fund_holdings", "mutual_fund_core_snapshot"} for table, *_ in fake_supabase.upserts)


def test_sync_workflow_does_not_fail_on_needs_review():
    workflow = Path(".github/workflows/sync-mf-disclosures.yml").read_text(encoding="utf-8")

    assert "--fail-on-needs-review" not in workflow
    assert "MF_EXTRACTOR_MODE" in workflow
