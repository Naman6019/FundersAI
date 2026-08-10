import pytest

from app.mf_ingestion.services.promotion_review_service import (
    ALLOWED_RESOLUTIONS,
    ALLOWED_SCOPES,
    _normalize_amc_key,
    upsert_decision,
)


def test_normalize_amc_key_applies_absl_alias():
    assert _normalize_amc_key("ABSL") == "aditya_birla"
    assert _normalize_amc_key(" ICICI ") == "icici"
    assert _normalize_amc_key(None) == ""


def test_allowed_scopes_and_resolutions_match_the_migration_check_constraints():
    # backend/migrations/20260810_add_mf_promotion_review_decisions.sql
    assert ALLOWED_SCOPES == {"risk", "holdings"}
    assert ALLOWED_RESOLUTIONS == {"use_staged", "use_live", "exclude"}


def test_upsert_decision_rejects_invalid_scope_before_touching_the_database():
    with pytest.raises(ValueError, match="invalid_scope"):
        upsert_decision(
            amc="icici",
            report_month="2026-06-01",
            scope="benchmark",
            subject_key="family-1",
            subject_label="Test Fund",
            resolution="use_staged",
            decided_value={},
            source_document_id=None,
            reviewed_by="tester",
        )


def test_upsert_decision_rejects_invalid_resolution_before_touching_the_database():
    with pytest.raises(ValueError, match="invalid_resolution"):
        upsert_decision(
            amc="icici",
            report_month="2026-06-01",
            scope="risk",
            subject_key="family-1",
            subject_label="Test Fund",
            resolution="force_promote",
            decided_value={},
            source_document_id=None,
            reviewed_by="tester",
        )
