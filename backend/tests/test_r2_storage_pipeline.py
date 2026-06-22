from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument, DownloadedDocument
from app.mf_ingestion.services.ingestion_service import IngestionService
from app.mf_ingestion.services.parsing_service import ParsingService
from app.mf_ingestion.storage.r2_store import R2Store, build_safe_key


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
        self.root.inserts.append((self.table_name, payload))
        return self

    def upsert(self, payload: dict, on_conflict: str | None = None):
        self.root.upserts.append((self.table_name, payload, on_conflict))
        return self

    def update(self, payload: dict):
        self._update_payload = payload
        return self

    def execute(self):
        if self.table_name == "mf_raw_documents" and self._update_payload is None:
            rows = list(self.root.docs)
            for key, values in self._in.items():
                rows = [row for row in rows if row.get(key) in values]
            for key, value in self._eq.items():
                rows = [row for row in rows if row.get(key) == value]
            return SimpleNamespace(data=rows)
        if self.table_name == "mf_raw_documents" and self._update_payload is not None:
            self.root.updates.append((self.table_name, self._eq, self._update_payload))
            return SimpleNamespace(data=[{"id": self._eq.get("id")}])
        if self.table_name == "mf_amc_sources":
            return SimpleNamespace(data=[{"amc_code": "PPFAS"}])
        return SimpleNamespace(data=[{"id": "doc-1"}] if self.table_name == "mf_raw_documents" else [])


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
                priority_score=100,
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


class _FakeR2Enabled:
    def __init__(self, *args, **kwargs) -> None:
        self.enabled = True
        self.uploads: list[tuple[str, bytes]] = []
        self.downloaded: list[str] = []

    def upload_bytes(self, key: str, content: bytes, *, bucket=None, content_type=None, metadata=None):
        self.uploads.append((key, content))
        return {"bucket": bucket or "raw-bucket", "key": key}

    def download_to_file(self, key: str, local_path: str, *, bucket=None):
        from pathlib import Path

        Path(local_path).write_bytes(b"%PDF fake")
        self.downloaded.append(key)
        return local_path

    def object_exists(self, key: str, *, bucket=None) -> bool:
        return True

    def generate_signed_url(self, key: str, *, bucket=None, expires_seconds=None) -> str:
        return f"https://example.com/{key}"


def test_build_safe_key_sanitizes_path_tokens():
    key = build_safe_key("RAW", "PPFAS", "../2026-04", "factsheet", "ABC 123.pdf")
    assert key == "raw/ppfas/2026-04/factsheet/abc-123.pdf"


def test_ingestion_writes_r2_storage_columns(monkeypatch):
    from app.mf_ingestion.services import ingestion_service

    fake_supabase = _FakeSupabase()
    monkeypatch.setattr(ingestion_service, "supabase", fake_supabase)
    monkeypatch.setattr(ingestion_service, "AMCDownloader", _FakeDownloader)
    monkeypatch.setattr(ingestion_service, "sha256_bytes", lambda _bytes: "fixed-checksum")
    monkeypatch.setattr(ingestion_service, "R2Store", _FakeR2Enabled)

    service = IngestionService()
    result = service.ingest_documents(amc="ppfas", document_type="factsheet", max_documents=1)

    assert result["status"] == "ok"
    raw_insert = [payload for table, payload in fake_supabase.inserts if table == "mf_raw_documents"][0]
    assert raw_insert["storage_backend"] == "r2"
    assert raw_insert["storage_bucket"]
    assert raw_insert["storage_key"].startswith("raw/ppfas/2026-04/factsheet/")
    assert raw_insert["storage_metadata"]["checksum"] == "fixed-checksum"


def test_acquire_documents_inserts_exact_url_with_r2_metadata(monkeypatch):
    from app.mf_ingestion.services import ingestion_service

    fake_supabase = _FakeSupabase()
    monkeypatch.setattr(ingestion_service, "supabase", fake_supabase)
    monkeypatch.setattr(ingestion_service, "AMCDownloader", _FakeDownloader)
    monkeypatch.setattr(ingestion_service, "sha256_bytes", lambda _bytes: "fixed-checksum")
    monkeypatch.setattr(ingestion_service, "R2Store", _FakeR2Enabled)

    result = IngestionService().acquire_documents(
        amc="ppfas",
        report_month="2026-04",
        documents=[
            {
                "document_type": "factsheet",
                "source_url": "https://amc.ppfas.com/downloads/factsheet-apr-2026.xlsx",
                "expected_file_type": ".xlsx",
            }
        ],
    )

    assert result["status"] == "ok"
    raw_insert = [payload for table, payload in fake_supabase.inserts if table == "mf_raw_documents"][0]
    assert raw_insert["source_url"].endswith("factsheet-apr-2026.xlsx")
    assert raw_insert["storage_backend"] == "r2"
    assert raw_insert["storage_metadata"]["source_manifest"]["acquisition_status"] == "acquired"


def test_acquire_documents_returns_download_403_without_parser_failure(monkeypatch):
    from app.mf_ingestion.services import ingestion_service

    class _ForbiddenDownloader(_FakeDownloader):
        def download(self, discovered):
            raise RuntimeError("http_request_failed method=GET url=https://example.test/hdfc.pdf reason=403 Forbidden")

    fake_supabase = _FakeSupabase()
    monkeypatch.setattr(ingestion_service, "supabase", fake_supabase)
    monkeypatch.setattr(ingestion_service, "AMCDownloader", _ForbiddenDownloader)
    monkeypatch.setattr(ingestion_service, "R2Store", _FakeR2Enabled)

    result = IngestionService().acquire_documents(
        amc="hdfc",
        report_month="2026-05",
        documents=[
            {
                "document_type": "factsheet",
                "source_url": "https://files.hdfcfund.com/s3fs-public/2026-06/HDFC%20MF%20Factsheet%20-%20May%202026.pdf",
            }
        ],
    )

    assert result["status"] == "error"
    assert result["failed_documents"][0]["reason"] == "download_403"
    assert not any(table == "mf_raw_documents" for table, _payload in fake_supabase.inserts)


def test_upload_document_reuse_creates_factsheet_and_portfolio_rows(monkeypatch):
    from app.mf_ingestion.services import ingestion_service

    fake_supabase = _FakeSupabase()
    monkeypatch.setattr(ingestion_service, "supabase", fake_supabase)
    monkeypatch.setattr(ingestion_service, "sha256_bytes", lambda _bytes: "shared-checksum")
    monkeypatch.setattr(ingestion_service, "R2Store", _FakeR2Enabled)

    result = IngestionService().upload_document(
        amc="hdfc",
        document_type="factsheet",
        report_month="2026-05",
        source_url="https://files.hdfcfund.com/s3fs-public/2026-06/HDFC%20MF%20Factsheet%20-%20May%202026.pdf",
        file_name="hdfc-factsheet-may-2026.pdf",
        content_type="application/pdf",
        file_bytes=b"%PDF fake",
        reuse_as_portfolio=True,
    )

    assert result["status"] == "ok"
    raw_inserts = [payload for table, payload in fake_supabase.inserts if table == "mf_raw_documents"]
    assert [row["document_type"] for row in raw_inserts] == ["factsheet", "portfolio_disclosure"]
    assert raw_inserts[0]["checksum"] == raw_inserts[1]["checksum"] == "shared-checksum"


def test_upload_document_duplicate_checksum_is_idempotent(monkeypatch):
    from app.mf_ingestion.services import ingestion_service

    fake_supabase = _FakeSupabase(
        [
            {
                "id": "existing-doc-1",
                "checksum": "fixed-checksum",
                "amc_code": "HDFC",
                "document_type": "factsheet",
                "report_month": "2026-05-01",
            }
        ]
    )
    monkeypatch.setattr(ingestion_service, "supabase", fake_supabase)
    monkeypatch.setattr(ingestion_service, "sha256_bytes", lambda _bytes: "fixed-checksum")
    monkeypatch.setattr(ingestion_service, "R2Store", _FakeR2Enabled)

    result = IngestionService().upload_document(
        amc="hdfc",
        document_type="factsheet",
        report_month="2026-05",
        source_url="https://files.hdfcfund.com/factsheet.pdf",
        file_name="factsheet.pdf",
        content_type="application/pdf",
        file_bytes=b"%PDF fake",
    )

    assert result["status"] == "ok"
    assert result["acquired_documents"][0]["status"] == "skipped"
    assert result["acquired_documents"][0]["source_document_id"] == "existing-doc-1"
    assert not any(table == "mf_raw_documents" for table, _payload in fake_supabase.inserts)


def test_upload_document_rejects_non_pdf_non_excel(monkeypatch):
    from app.mf_ingestion.services import ingestion_service

    fake_supabase = _FakeSupabase()
    monkeypatch.setattr(ingestion_service, "supabase", fake_supabase)
    monkeypatch.setattr(ingestion_service, "R2Store", _FakeR2Enabled)

    result = IngestionService().upload_document(
        amc="hdfc",
        document_type="factsheet",
        report_month="2026-05",
        source_url="https://files.hdfcfund.com/factsheet.txt",
        file_name="factsheet.txt",
        content_type="text/plain",
        file_bytes=b"not a pdf",
    )

    assert result == {"status": "error", "reason": "unsupported_file_type", "file_ext": ".txt"}
    assert not any(table == "mf_raw_documents" for table, _payload in fake_supabase.inserts)


def test_parser_downloads_r2_file_before_parsing(monkeypatch):
    from app.mf_ingestion.services import parsing_service

    fake_doc = {
        "id": "doc-r2-1",
        "amc_code": "ICICI",
        "document_type": "factsheet",
        "storage_backend": "r2",
        "storage_bucket": "raw-bucket",
        "storage_key": "raw/icici/2026-04/factsheet/fixed.pdf",
        "storage_path": "",
        "parse_status": "pending",
    }
    fake_supabase = _FakeSupabase([fake_doc])
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    monkeypatch.setattr(parsing_service, "R2Store", _FakeR2Enabled)
    monkeypatch.setattr(parsing_service.FactsheetParser, "parse", lambda *_args, **_kwargs: [])

    service = ParsingService()
    result = service.parse_pending_documents(limit=1, amc_code="ICICI")

    assert result["count"] == 1
    assert result["processed"][0]["status"] == "needs_review"
    assert service.r2_store.downloaded == ["raw/icici/2026-04/factsheet/fixed.pdf"]


def test_r2_store_signed_url_and_exists(monkeypatch):
    from app.mf_ingestion.storage import r2_store

    class _FakeClient:
        def upload_fileobj(self, *_args, **_kwargs):
            return None

        def download_fileobj(self, *_args, **_kwargs):
            return None

        def head_object(self, **_kwargs):
            return {"ok": True}

        def generate_presigned_url(self, _method, Params=None, ExpiresIn=0):
            return f"https://signed/{Params['Key']}?e={ExpiresIn}"

    monkeypatch.setattr(r2_store, "boto3", SimpleNamespace(client=lambda *_args, **_kwargs: _FakeClient()))
    store = R2Store(
        endpoint="https://example.r2.cloudflarestorage.com",
        access_key_id="a",
        secret_access_key="b",
        raw_bucket="raw",
        cold_bucket="cold",
    )
    assert store.object_exists("raw/ppfas/2026-04/factsheet/a.pdf", bucket="raw") is True
    assert "signed" in store.generate_signed_url("raw/ppfas/2026-04/factsheet/a.pdf", bucket="raw", expires_seconds=120)
