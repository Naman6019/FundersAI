from datetime import date
from pathlib import Path

from app.mf_ingestion.jobs.reconcile_raw_document_report_month import (
    _parse_month,
    _validate_document,
)


def test_report_month_reconciliation_validation_requires_exact_body_evidence() -> None:
    document = {
        "amc_code": "uti",
        "report_month": "2026-07-01",
        "checksum": "abc123",
        "storage_backend": "r2",
        "storage_key": "uti/factsheet.pdf",
    }

    assert _validate_document(
        document,
        expected_amc="uti",
        expected_current_month=date(2026, 7, 1),
        corrected_month=date(2026, 6, 1),
        expected_checksum="abc123",
        observed_checksum="abc123",
        observed_body_month=date(2026, 6, 1),
        has_applied_promotion=False,
    ) == []

    assert "observed_body_month_mismatch" in _validate_document(
        document,
        expected_amc="uti",
        expected_current_month=date(2026, 7, 1),
        corrected_month=date(2026, 6, 1),
        expected_checksum="abc123",
        observed_checksum="abc123",
        observed_body_month=date(2026, 5, 1),
        has_applied_promotion=False,
    )


def test_report_month_reconciliation_rejects_promoted_or_changed_source() -> None:
    issues = _validate_document(
        {
            "amc_code": "absl",
            "report_month": "2026-07-01",
            "checksum": "database-checksum",
            "storage_backend": "local",
            "storage_key": None,
        },
        expected_amc="absl",
        expected_current_month=date(2026, 7, 1),
        corrected_month=date(2026, 6, 1),
        expected_checksum="reviewed-checksum",
        observed_checksum="downloaded-checksum",
        observed_body_month=date(2026, 6, 1),
        has_applied_promotion=True,
    )

    assert issues == [
        "r2_checksum_mismatch",
        "source_checksum_mismatch",
        "source_has_applied_promotion",
        "source_not_stored_in_r2",
        "source_r2_key_missing",
    ]


def test_report_month_reconciliation_contract_is_protected_and_audited() -> None:
    root = Path(__file__).resolve().parents[2]
    migration = (
        root / "backend" / "migrations" / "20260728_add_mf_report_month_reconciliation.sql"
    ).read_text(encoding="utf-8")
    workflow = (
        root / ".github" / "workflows" / "reconcile-mf-report-month.yml"
    ).read_text(encoding="utf-8")

    assert _parse_month("2026-06") == date(2026, 6, 1)
    assert "source_has_applied_promotion" in migration
    assert "mf_report_month_corrections" in migration
    assert "parse_status = 'needs_reparse'" in migration
    assert "environment: production-data" in workflow
    assert "RECONCILE ${SOURCE_DOCUMENT_ID}" in workflow
    assert "R2_SECRET_ACCESS_KEY" in workflow
