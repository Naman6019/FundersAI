from __future__ import annotations

from app.mf_ingestion.jobs.reconcile_staged_mappings import _candidate_mapping_payload, _mapping_payload


def test_mapping_payload_updates_staging_identity_only():
    payload = _mapping_payload(
        scheme_code="149464",
        family_id="icici-prudential-silver-etf",
        confidence=100.0,
    )

    assert payload == {
        "mapped_scheme_code": "149464",
        "mapped_family_id": "icici-prudential-silver-etf",
        "mapping_confidence": 100.0,
        "mapping_status": "mapped",
    }
    assert "risk_level" not in payload
    assert "expense_ratio" not in payload


def test_candidate_reconciliation_cannot_retarget_promoted_scopes():
    row = {
        "mapped_scheme_code": "100640",
        "mapped_family_id": "sbi-medium-to-long-duration",
        "mapping_confidence": 100.0,
        "promotion_status": "staged",
        "promoted_scopes": ["risk"],
        "validation_issues": [],
    }

    payload, changed = _candidate_mapping_payload(
        row=row,
        scheme_code="100639",
        family_id="sbi-medium-to-long-duration",
        confidence=100.0,
    )

    assert changed is True
    assert payload["mapped_scheme_code"] == "100640"
    assert payload["mapping_status"] == "needs_review"
    assert payload["promotion_status"] == "needs_review"
