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


class _FakeCoreRepository:
    supabase = object()

    def __init__(self) -> None:
        self.upserts: list[dict] = []

    def get_mutual_fund_core_snapshot(self, scheme_code):
        return {
            "scheme_code": str(scheme_code),
            "scheme_name": "ICICI Prudential Multi Asset Fund",
            "provider_payload": {},
        }

    def upsert_mutual_fund_core_snapshot_rows(self, rows):
        self.upserts.extend(rows)


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


def test_r2_required_parser_skips_local_only_raw_documents(monkeypatch):
    from app.mf_ingestion.services import parsing_service

    fake_supabase = _FakeSupabase(
        [
            {
                "id": "axis-local-only",
                "amc_code": "AXIS",
                "document_type": "factsheet",
                "storage_backend": "local",
                "storage_path": "/opt/render/project/src/backend/data/mf_raw_docs/AXIS/missing.pdf",
                "parse_status": "pending",
            }
        ]
    )
    monkeypatch.setenv("MF_REQUIRE_R2_FOR_RAW_STORAGE", "true")
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    monkeypatch.setattr(parsing_service, "R2Store", _FakeR2Disabled)

    result = ParsingService().parse_pending_documents(limit=1, amc_code="AXIS")

    assert result["processed"][0]["status"] == "skipped"
    assert result["processed"][0]["reason"] == "raw_file_unavailable_in_r2_required_runtime"
    assert fake_supabase.updates == [
        (
            "mf_raw_documents",
            {"id": "axis-local-only"},
            {
                "parse_status": "skipped_no_source_data",
                "validation_issues": ["raw_file_unavailable_in_r2_required_runtime"],
                "parsed_at": fake_supabase.updates[0][2]["parsed_at"],
            },
        )
    ]


def test_llm_extractor_uses_openrouter_when_key_is_configured(monkeypatch, tmp_path: Path):
    from app.mf_ingestion.extractors import llm_extractor
    from app.mf_ingestion.extractors.llm_extractor import StrictJSONLLMExtractor

    raw_file = tmp_path / "factsheet.txt"
    raw_file.write_text("scheme benchmark Nifty 500 TRI", encoding="utf-8")
    captured: dict[str, object] = {}

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "source_document_id": "doc-openrouter-1",
                                    "extractor_type": "llm",
                                    "records": [
                                        {
                                            "scheme_name": "ICICI Prudential Multi Asset Fund",
                                            "report_month": "2026-04-01",
                                            "holdings": [],
                                            "aum": 1000.0,
                                            "expense_ratio": 0.8,
                                            "benchmark": "Nifty 500 TRI",
                                            "fund_manager": "Test Manager",
                                            "risk_level": "Very High",
                                            "confidence_score": 95.0,
                                            "validation_issues": [],
                                        }
                                    ],
                                }
                            )
                        }
                    }
                ]
            }

    def fake_post(url, *, headers, timeout, json):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["payload"] = json
        return _FakeResponse()

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-test-key")
    monkeypatch.setenv("MF_LLM_HTTP_REFERER", "https://fundersai.test")
    monkeypatch.setenv("MF_LLM_APP_TITLE", "FundersAI Test")
    monkeypatch.delenv("MF_LLM_BASE_URL", raising=False)
    monkeypatch.setattr(llm_extractor.requests, "post", fake_post)

    extraction = StrictJSONLLMExtractor(
        enabled=True,
        mode="llm_then_deterministic",
        model="nvidia/nemotron-3-ultra-550b-a55b",
    ).extract(str(raw_file), {"id": "doc-openrouter-1", "amc_code": "ICICI", "document_type": "factsheet"})

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer openrouter-test-key"
    assert captured["headers"]["HTTP-Referer"] == "https://fundersai.test"
    assert captured["headers"]["X-Title"] == "FundersAI Test"
    assert captured["payload"]["model"] == "nvidia/nemotron-3-ultra-550b-a55b"
    assert extraction.records[0].benchmark == "Nifty 500 TRI"


def test_llm_response_format_uses_json_object_for_nemotron(monkeypatch):
    from app.mf_ingestion.extractors.llm_extractor import _response_format

    monkeypatch.delenv("MF_LLM_RESPONSE_FORMAT", raising=False)
    response_format = _response_format("nvidia/nemotron-3-ultra-550b-a55b")

    assert response_format == {"type": "json_object"}


def test_llm_strict_schema_matches_normalized_contract(monkeypatch):
    from app.mf_ingestion.extractors.llm_extractor import _response_format

    monkeypatch.delenv("MF_LLM_RESPONSE_FORMAT", raising=False)
    response_format = _response_format("openai/gpt-4.1-mini")
    schema = response_format["json_schema"]["schema"]
    record_schema = schema["properties"]["records"]["items"]
    holding_schema = record_schema["properties"]["holdings"]["items"]

    assert response_format["type"] == "json_schema"
    assert record_schema["properties"]["fund_manager"] == {"type": ["string", "null"]}
    assert holding_schema["additionalProperties"] is False
    assert set(holding_schema["required"]) == set(holding_schema["properties"])


def test_llm_primary_dry_run_enqueues_review_and_uses_deterministic_fallback(monkeypatch, tmp_path: Path):
    from app.mf_ingestion.parsers.factsheet_parser import FactsheetRecord
    from app.mf_ingestion.services import parsing_service, review_service

    raw_file = tmp_path / "factsheet.txt"
    raw_file.write_text("messy official factsheet text", encoding="utf-8")
    fixture = tmp_path / "llm-output.json"
    fixture.write_text(
        json.dumps(
            {
                "source_document_id": "doc-llm-primary-dry-1",
                "extractor_type": "llm",
                "records": [
                    {
                        "scheme_name": "ICICI Prudential Multi Asset Fund",
                        "report_month": "2026-04-01",
                        "holdings": [],
                        "aum": 1000.0,
                        "expense_ratio": 0.8,
                        "benchmark": "NIFTY 50 Hybrid Composite Debt 50:50 Index",
                        "fund_manager": "Test Manager",
                        "risk_level": "Very High",
                        "confidence_score": 95.0,
                        "validation_issues": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    fake_supabase = _FakeSupabase(
        [
            {
                "id": "doc-llm-primary-dry-1",
                "amc_code": "ICICI",
                "document_type": "factsheet",
                "source_url": "https://example.test/factsheet.pdf",
                "storage_path": str(raw_file),
                "parse_status": "pending",
                "parser_version": "test",
            }
        ]
    )
    repo = _FakeCoreRepository()
    monkeypatch.setenv("MF_EXTRACTOR_MODE", "llm_then_deterministic")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_ENABLED", "true")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_MODEL", "test-model")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_FIXTURE_PATH", str(fixture))
    monkeypatch.setenv("MF_LLM_ALLOW_FINAL_WRITES", "false")
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    monkeypatch.setattr(review_service, "supabase", fake_supabase)
    monkeypatch.setattr(parsing_service, "R2Store", _FakeR2Disabled)
    monkeypatch.setattr(
        parsing_service.FactsheetParser,
        "parse",
        lambda *_args, **_kwargs: [
            FactsheetRecord(
                scheme_name="ICICI Prudential Multi Asset Fund",
                report_month=date(2026, 4, 1),
                benchmark="Nifty 500 TRI",
                confidence_score=95.0,
            )
        ],
    )

    service = ParsingService()
    service.repository = repo
    service._resolve_scheme_code_for_scheme = lambda _name: "101144"
    result = service.parse_pending_documents(limit=1, amc_code="ICICI")

    assert result["processed"][0]["status"] == "parsed"
    assert any(table == "mf_parse_review_queue" for table, _payload in fake_supabase.inserts)
    assert repo.upserts[0]["benchmark"] == "Nifty 500 TRI"


def test_llm_primary_writes_core_fields_when_enabled(monkeypatch, tmp_path: Path):
    from app.mf_ingestion.services import parsing_service, review_service

    raw_file = tmp_path / "factsheet.txt"
    raw_file.write_text("messy official factsheet text", encoding="utf-8")
    fixture = tmp_path / "llm-output.json"
    fixture.write_text(
        json.dumps(
            {
                "source_document_id": "doc-llm-primary-write-1",
                "extractor_type": "llm",
                "records": [
                    {
                        "scheme_name": "ICICI Prudential Multi Asset Fund",
                        "report_month": "2026-04-01",
                        "holdings": [],
                        "aum": 1000.0,
                        "expense_ratio": 0.8,
                        "benchmark": "NIFTY 50 Hybrid Composite Debt 50:50 Index",
                        "fund_manager": "Test Manager",
                        "risk_level": "Very High",
                        "confidence_score": 95.0,
                        "validation_issues": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    fake_supabase = _FakeSupabase(
        [
            {
                "id": "doc-llm-primary-write-1",
                "amc_code": "ICICI",
                "document_type": "factsheet",
                "source_url": "https://example.test/factsheet.pdf",
                "storage_path": str(raw_file),
                "parse_status": "pending",
                "parser_version": "test",
            }
        ]
    )
    repo = _FakeCoreRepository()
    monkeypatch.setenv("MF_EXTRACTOR_MODE", "llm_then_deterministic")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_ENABLED", "true")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_MODEL", "test-model")
    monkeypatch.setenv("MF_LLM_EXTRACTOR_FIXTURE_PATH", str(fixture))
    monkeypatch.setenv("MF_LLM_ALLOW_FINAL_WRITES", "true")
    monkeypatch.setenv("MF_LLM_MIN_WRITE_CONFIDENCE", "90")
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    monkeypatch.setattr(review_service, "supabase", fake_supabase)
    monkeypatch.setattr(parsing_service, "R2Store", _FakeR2Disabled)
    monkeypatch.setattr(parsing_service.FactsheetParser, "parse", lambda *_args, **_kwargs: [])

    service = ParsingService()
    service.repository = repo
    service._resolve_scheme_code_for_scheme = lambda _name: "101144"
    result = service.parse_pending_documents(limit=1, amc_code="ICICI")

    assert result["processed"][0]["status"] == "parsed"
    assert result["processed"][0]["extractor_type"] == "llm"
    row = repo.upserts[0]
    assert row["benchmark"] == "NIFTY 50 Hybrid Composite Debt 50:50 Index"
    trace = row["provider_payload"]["amc_trace"]["benchmark"]
    assert trace["extractor_type"] == "llm"
    assert trace["extractor_model"] == "test-model"
    assert trace["confidence_score"] == 95.0


def test_sync_workflow_does_not_fail_on_needs_review():
    workflow = Path(".github/workflows/sync-mf-disclosures.yml").read_text(encoding="utf-8")

    assert "--fail-on-needs-review" not in workflow
    assert "MF_EXTRACTOR_MODE" in workflow


def test_sync_workflow_has_parse_only_path_for_r2_first_acquisition():
    workflow = Path(".github/workflows/sync-mf-disclosures.yml").read_text(encoding="utf-8")

    assert "parse_only" in workflow
    assert 'PARSE_ONLY="true"' in workflow
    assert "Skipping live AMC ingestion" in workflow


def test_sync_workflow_prints_disclosure_diagnostics_before_coverage_gate():
    workflow = Path(".github/workflows/sync-mf-disclosures.yml").read_text(encoding="utf-8")

    assert "backend/scripts/report_mf_disclosure_diagnostics.py" in workflow
    assert workflow.index("report_mf_disclosure_diagnostics.py") < workflow.index("check_mf_disclosure_coverage.py")


def test_sync_workflow_has_strict_scheduled_coverage_defaults():
    workflow = Path(".github/workflows/sync-mf-disclosures.yml").read_text(encoding="utf-8")

    assert "github.event.inputs.strict_coverage_amcs || 'axis,hdfc,sbi,icici,ppfas,nippon'" in workflow
    assert 'MF_DISCLOSURE_MIN_CORE_FIELD_RATIO: "0.80"' in workflow
    assert 'MF_DISCLOSURE_MIN_PORTFOLIO_FAMILY_RATIO: "0.80"' in workflow


def test_sync_workflow_uses_manifest_and_link_preflight():
    workflow = Path(".github/workflows/sync-mf-disclosures.yml").read_text(encoding="utf-8")

    assert "backend/config/mf_document_sources.json" in workflow
    assert "preflight_mf_document_links.py" in workflow
    assert "--manifest-path \"$MF_SOURCE_MANIFEST_PATH\"" in workflow


def test_reacquire_workflow_runs_reacquire_job():
    workflow = Path(".github/workflows/reacquire-mf-raw-to-r2.yml").read_text(encoding="utf-8")

    assert "reacquire_local_raw_documents" in workflow
    assert "MF_REQUIRE_R2_FOR_RAW_STORAGE" in workflow


def test_supabase_edge_function_acquires_official_docs_to_r2():
    function_source = Path("supabase/functions/mf-acquire-docs/index.ts").read_text(encoding="utf-8")
    config = Path("supabase/config.toml").read_text(encoding="utf-8")

    assert "MF_EDGE_ACQUIRE_KEY" in function_source
    assert "AwsClient" in function_source
    assert "R2_RAW_BUCKET" in function_source
    assert "SUPABASE_SERVICE_ROLE_KEY" in function_source
    assert "mf_raw_documents" in function_source
    assert "storage_backend: \"r2\"" in function_source
    assert "third_party_source_blocked" in function_source
    assert "groww.in" in function_source
    assert "discoverOfficialDocuments" in function_source
    assert "extractAnchorDocumentLinks" in function_source
    assert "MF_EDGE_MAX_DISCOVERED_DOCUMENTS" in function_source
    assert "[functions.mf-acquire-docs]" in config


def test_amc_derived_view_sync_passes_family_id_to_final_tables(monkeypatch):
    from app.mf_ingestion.services import parsing_service

    service = object.__new__(parsing_service.ParsingService)
    calls: list[tuple[str, str | None]] = []

    monkeypatch.setattr(service, "_resolve_scheme_code_for_scheme", lambda _scheme_name: "101")
    monkeypatch.setattr(service, "_resolve_family_id_for_scheme", lambda _scheme_code: "sbi-first")
    monkeypatch.setattr(
        service,
        "_upsert_mutual_fund_holdings",
        lambda *_args: calls.append(("holdings", _args[-1])),
    )
    monkeypatch.setattr(
        service,
        "_upsert_mutual_fund_sectors",
        lambda *_args: calls.append(("sectors", _args[-1])),
    )
    monkeypatch.setattr(service, "_upsert_mutual_fund_core_trace", lambda **_kwargs: None)

    service._sync_amc_derived_views(
        amc_code="sbi",
        scheme_name="SBI First Fund",
        report_month=date(2026, 5, 1),
        source_document_id="doc-sbi-1",
        source_url="local",
        parser_version="test",
        holdings=[{"instrument_name": "HDFC Bank Ltd.", "isin": "INE040A01034", "sector": "Banks", "percent_aum": 100.0}],
    )

    assert calls == [("holdings", "sbi-first"), ("sectors", "sbi-first")]


def test_sync_workflow_can_call_supabase_edge_acquisition():
    workflow = Path(".github/workflows/sync-mf-disclosures.yml").read_text(encoding="utf-8")

    assert "MF_EDGE_ACQUIRE_URL" in workflow
    assert "MF_EDGE_ACQUIRE_KEY" in workflow
    assert "MF_EDGE_ACQUIRED_AMCS" in workflow
    assert 'EDGE_ACQUIRED="true"' in workflow
    assert 'PARSE_ONLY="true"' in workflow
    assert "Skipping GitHub runner link preflight" in workflow
    assert "Requesting Supabase Edge document acquisition" in workflow
    assert '"documents"] = documents' in workflow
    assert "curl -sS -o \"$edge_response_file\"" in workflow
    assert "Supabase Edge acquisition failed for $amc with HTTP $edge_status." in workflow


def test_sync_workflow_discovers_hdfc_factsheet_before_edge_acquisition():
    workflow = Path(".github/workflows/sync-mf-disclosures.yml").read_text(encoding="utf-8")

    assert "discover_hdfc_edge_documents" in workflow
    assert "hdfc_factsheet_docs_from_payload" in workflow
    assert "__NEXT_DATA__" in workflow
    assert "latestInvestorsDocuments" in workflow
    assert "factsheetfile" in workflow
    assert "/_next/data/{build_id}/mutual-funds/factsheets.json" in workflow
    assert "https://www.hdfcfund.com/" in workflow
    assert '"document_type": "factsheet"' in workflow
    assert 'if not documents and amc == "hdfc":' in workflow
    assert "documents.extend(discover_hdfc_edge_documents(factsheet_page_url, max_documents))" in workflow


def test_supabase_edge_function_returns_non_200_when_no_documents_acquired():
    function_source = Path("supabase/functions/mf-acquire-docs/index.ts").read_text(encoding="utf-8")

    assert 'const responseStatus = status === "error" ? 502 : 200;' in function_source
    assert "failed_documents: failed }, responseStatus" in function_source
