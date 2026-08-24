from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes import mf_ingestion


def test_internal_mf_auth_accepts_only_configured_admin_or_webhook_credentials(monkeypatch):
    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "admin-secret")
    monkeypatch.setenv("MF_INGESTION_WEBHOOK_TOKEN", "webhook-secret")

    with pytest.raises(HTTPException) as exc:
        mf_ingestion._require_admin_auth("wrong", "wrong")
    assert exc.value.status_code == 403
    assert exc.value.detail == "admin_auth_required"

    mf_ingestion._require_admin_auth(" admin-secret ")
    mf_ingestion._require_admin_auth(None, "webhook-secret")
    mf_ingestion._require_admin_auth(None, "admin-secret")


def test_acquire_documents_requires_auth_and_forwards_the_validated_payload(monkeypatch):
    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "admin-secret")
    captured: dict = {}

    class _Service:
        def acquire_documents(self, **kwargs):
            captured.update(kwargs)
            return {"status": "ok"}

    monkeypatch.setattr(mf_ingestion, "IngestionService", _Service)
    payload = mf_ingestion.AcquireDocumentsRequest(
        amc="ppfas",
        report_month="2026-07-01",
        documents=[
            mf_ingestion.AcquireDocumentItem(
                source_url="https://amc.ppfas.com/factsheet.pdf",
                document_type="factsheet",
                reuse_as_portfolio=True,
            )
        ],
    )

    with pytest.raises(HTTPException):
        mf_ingestion.acquire_documents(payload, x_admin_key="wrong")

    assert mf_ingestion.acquire_documents(payload, x_admin_key="admin-secret") == {"status": "ok"}
    assert captured == {
        "amc": "ppfas",
        "report_month": "2026-07-01",
        "documents": [
            {
                "source_url": "https://amc.ppfas.com/factsheet.pdf",
                "document_type": "factsheet",
                "expected_file_type": None,
                "report_month": None,
                "title": None,
                "discovery_page_url": None,
                "reuse_as_portfolio": True,
            }
        ],
    }


def test_upload_document_rejects_missing_file_after_authentication(monkeypatch):
    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "admin-secret")

    class _Request:
        async def form(self):
            return {"amc": "ppfas"}

    with pytest.raises(HTTPException) as exc:
        asyncio.run(mf_ingestion.upload_document(_Request(), x_admin_key="admin-secret"))

    assert exc.value.status_code == 400
    assert exc.value.detail == "file_required"


def test_scheme_holdings_returns_expected_api_errors_and_normalized_result():
    with pytest.raises(HTTPException) as missing_repository:
        mf_ingestion.get_scheme_holdings("Fund", repository=None)
    assert missing_repository.value.status_code == 500

    class _MissingRepository:
        def get_scheme_by_normalized_name(self, _name):
            return None

    with pytest.raises(HTTPException) as missing_scheme:
        mf_ingestion.get_scheme_holdings(" Fund ", repository=_MissingRepository())
    assert missing_scheme.value.status_code == 404

    class _Repository:
        def get_scheme_by_normalized_name(self, name):
            assert name == "fund"
            return {"id": "scheme-1", "name": "Fund"}

        def get_scheme_holdings(self, scheme_id, *, report_month, limit):
            assert (scheme_id, report_month, limit) == ("scheme-1", "2026-07-01", 10)
            return [{"instrument_name": "Example Ltd"}]

    assert mf_ingestion.get_scheme_holdings(
        " Fund ",
        report_month="2026-07-01",
        limit=10,
        repository=_Repository(),
    )["count"] == 1


def test_signed_url_requires_r2_backed_storage_and_returns_signed_raw_url(monkeypatch):
    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "admin-secret")
    config = SimpleNamespace(
        r2_endpoint="https://r2.example.test",
        r2_access_key_id="key",
        r2_secret_access_key="secret",
        r2_raw_bucket="raw-bucket",
        r2_cold_bucket="cold-bucket",
        r2_signed_url_ttl_seconds=120,
    )
    monkeypatch.setattr(mf_ingestion, "get_config", lambda: config)

    class _Store:
        enabled = True

        def __init__(self, **_kwargs):
            pass

        def object_exists(self, key, *, bucket):
            return key == "raw/ppfas/2026-07/factsheet/example.pdf" and bucket == "raw-bucket"

        def generate_signed_url(self, *, key, bucket, expires_seconds):
            return f"https://signed.example.test/{bucket}/{key}?ttl={expires_seconds}"

    monkeypatch.setattr(mf_ingestion, "R2Store", _Store)

    class _Repository:
        def __init__(self, row):
            self.row = row

        def get_raw_document_storage(self, _source_document_id):
            return self.row

    with pytest.raises(HTTPException) as missing_r2:
        mf_ingestion.get_document_signed_url(
            "doc-1",
            artifact="raw",
            x_admin_key="admin-secret",
            repository=_Repository({"storage_backend": "local"}),
        )
    assert missing_r2.value.status_code == 404
    assert missing_r2.value.detail == "raw_r2_object_not_found"

    response = mf_ingestion.get_document_signed_url(
        "doc-1",
        artifact="raw",
        x_admin_key="admin-secret",
        repository=_Repository(
            {
                "storage_backend": "r2",
                "storage_key": "RAW/PPFAS/2026-07/factsheet/Example.pdf",
            }
        ),
    )
    assert response == {
        "source_document_id": "doc-1",
        "artifact": "raw",
        "bucket": "raw-bucket",
        "key": "raw/ppfas/2026-07/factsheet/example.pdf",
        "signed_url": "https://signed.example.test/raw-bucket/raw/ppfas/2026-07/factsheet/example.pdf?ttl=120",
        "expires_in_seconds": 120,
    }
