from __future__ import annotations

from app.mf_ingestion.jobs.reconcile_staged_mappings import _mapping_payload


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
