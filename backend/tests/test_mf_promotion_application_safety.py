from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.mf_ingestion.jobs import promote_mf_disclosures


def test_unpromotable_report_cannot_write_to_supabase(monkeypatch):
    class _Supabase:
        def rpc(self, *_args, **_kwargs):
            raise AssertionError("a rejected report must not reach Supabase")

    monkeypatch.setattr(promote_mf_disclosures, "supabase", _Supabase())

    with pytest.raises(ValueError, match="promotion_report_not_promotable"):
        promote_mf_disclosures.apply_promotable_report(
            {"status": "rejected"},
            ["risk", "holdings"],
            date(2026, 7, 1),
            requested_by="test",
        )


def test_promotion_applies_only_reviewed_candidates_and_requested_portfolio_scopes(monkeypatch):
    calls: list[tuple[str, dict]] = []

    class _Rpc:
        def __init__(self, name, params):
            self.name = name
            self.params = params

        def execute(self):
            return SimpleNamespace(data={"procedure": self.name})

    class _Supabase:
        def rpc(self, name, params):
            calls.append((name, params))
            return _Rpc(name, params)

    monkeypatch.setattr(promote_mf_disclosures, "supabase", _Supabase())
    monkeypatch.setattr(
        promote_mf_disclosures,
        "build_family_invariant_propagation_plan",
        lambda *_args, **_kwargs: {"status": "not_applicable", "updates": [], "conflicts": {}},
    )
    monkeypatch.setattr(
        promote_mf_disclosures,
        "apply_family_invariant_propagation",
        lambda plan: {"status": plan["status"], "applied": 0},
    )
    report = {
        "status": "promotable",
        "source_document": {"id": "document-1"},
        "candidate_reports": [
            {"candidate_id": "candidate-good", "eligible_scopes": ["risk"], "issues": []},
            {"candidate_id": "candidate-rejected", "eligible_scopes": ["benchmark"], "issues": ["mapping_changed"]},
            {"candidate_id": "candidate-empty", "eligible_scopes": [], "issues": []},
        ],
    }

    applied = promote_mf_disclosures.apply_promotable_report(
        report,
        ["risk", "holdings"],
        date(2026, 7, 1),
        requested_by="coverage-test",
    )

    assert calls == [
        (
            "promote_mf_factsheet_candidate",
            {
                "p_candidate_id": "candidate-good",
                "p_scopes": ["risk"],
                "p_requested_by": "coverage-test",
                "p_expected_report_month": "2026-07-01",
            },
        ),
        (
            "promote_mf_holdings_document_v2",
            {
                "p_source_document_id": "document-1",
                "p_scopes": ["holdings"],
                "p_requested_by": "coverage-test",
                "p_expected_report_month": "2026-07-01",
            },
        ),
    ]
    assert applied == [
        {"candidate_id": "candidate-good", "result": {"procedure": "promote_mf_factsheet_candidate"}},
        {"candidate_id": "candidate-good", "family_invariant_propagation": {"status": "not_applicable", "applied": 0}},
        {"source_document_id": "document-1", "result": {"procedure": "promote_mf_holdings_document_v2"}},
    ]
