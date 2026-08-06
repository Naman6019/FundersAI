from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.mf_ingestion.services import parsing_service


class _FakeQuery:
    def __init__(self, root, table):
        self.root = root
        self.table = table

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        return SimpleNamespace(data=[])

    def upsert(self, payload, on_conflict=None):
        self.root.upserts.append((self.table, payload, on_conflict))
        return self


class _FakeSupabase:
    def __init__(self):
        self.upserts = []

    def table(self, table):
        return _FakeQuery(self, table)


class _FakeRepository:
    supabase = object()

    def get_mutual_fund_core_snapshot(self, _scheme_code):
        return {
            "scheme_code": "122639",
            "scheme_name": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
            "amc_name": "Parag Parikh Mutual Fund",
        }


def test_factsheet_extraction_stages_risk_without_runtime_write(monkeypatch):
    fake_supabase = _FakeSupabase()
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    service = object.__new__(parsing_service.ParsingService)
    service.repository = _FakeRepository()
    service._resolve_scheme_code_for_scheme = lambda _name: "122639"
    service._resolve_family_id_for_scheme = lambda _code: "ppfas-flexi-cap"

    staged = service._stage_amc_core_fields(
        amc_code="ppfas",
        scheme_name="Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
        report_month=date(2026, 4, 1),
        source_document_id="00000000-0000-0000-0000-000000000001",
        source_url="https://example.test/factsheet.pdf",
        parser_version="factsheet-v1",
        aum=None,
        expense_ratio=None,
        benchmark=None,
        fund_manager=None,
        risk_level="Very High",
    )

    assert staged is True
    assert len(fake_supabase.upserts) == 1
    table, payload, conflict = fake_supabase.upserts[0]
    assert table == "mf_factsheet_candidates"
    assert conflict == "source_document_id,normalized_scheme_name"
    assert payload["raw_scheme_name"] == "Parag Parikh Flexi Cap Fund - Direct Plan - Growth"
    assert payload["mapped_scheme_code"] == "122639"
    assert payload["mapped_family_id"] == "ppfas-flexi-cap"
    assert payload["risk_level"] == "Very High"
    assert all(table != "mutual_fund_core_snapshot" for table, *_ in fake_supabase.upserts)


def test_factsheet_extraction_preserves_unmapped_raw_name(monkeypatch):
    fake_supabase = _FakeSupabase()
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    service = object.__new__(parsing_service.ParsingService)
    service.repository = _FakeRepository()
    service._resolve_scheme_code_for_scheme = lambda _name: None

    staged = service._stage_amc_core_fields(
        amc_code="ppfas",
        scheme_name="AMC abbreviated scheme spelling",
        report_month=date(2026, 4, 1),
        source_document_id="00000000-0000-0000-0000-000000000002",
        source_url="https://example.test/factsheet.pdf",
        parser_version="factsheet-v1",
        aum=100.0,
        expense_ratio=None,
        benchmark=None,
        fund_manager=None,
        risk_level=None,
    )

    assert staged is False
    payload = fake_supabase.upserts[0][1]
    assert payload["raw_scheme_name"] == "AMC abbreviated scheme spelling"
    assert payload["mapped_scheme_code"] is None
    assert payload["mapping_status"] == "unmapped"
    assert payload["promotion_status"] == "needs_review"


def test_factsheet_extraction_preserves_uti_raw_label_but_normalizes_mapping_name(monkeypatch):
    fake_supabase = _FakeSupabase()
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    service = object.__new__(parsing_service.ParsingService)
    service.repository = _FakeRepository()
    service._resolve_scheme_code_for_scheme = lambda _name: None

    service._stage_amc_core_fields(
        amc_code="uti",
        scheme_name="SCHEME: UTI - Flexi Cap Fund.",
        report_month=date(2026, 6, 1),
        source_document_id="00000000-0000-0000-0000-000000000003",
        source_url="https://example.test/uti-portfolio.zip",
        parser_version="portfolio-v1",
        aum=100.0,
        expense_ratio=None,
        benchmark=None,
        fund_manager=None,
        risk_level=None,
    )

    payload = fake_supabase.upserts[0][1]
    assert payload["raw_scheme_name"] == "SCHEME: UTI - Flexi Cap Fund."
    assert payload["normalized_scheme_name"] == "uti - flexi cap fund"


def test_promoted_candidate_mapping_change_is_sent_to_review():
    payload = {
        "mapped_scheme_code": "100639",
        "mapped_family_id": "sbi-medium-to-long-duration",
        "mapping_confidence": 100.0,
        "mapping_status": "mapped",
        "promotion_status": "staged",
        "validation_issues": [],
    }
    existing = {
        "mapped_scheme_code": "100639",
        "mapped_family_id": "sbi-medium-to-long-duration",
        "mapping_confidence": 100.0,
        "promotion_status": "staged",
        "promoted_scopes": ["risk"],
        "promoted_scheme_code": "100640",
        "validation_issues": [],
    }

    guarded, changed = parsing_service.guard_promoted_mapping_change(existing, payload)

    assert changed is True
    assert guarded["mapped_scheme_code"] == "100640"
    assert guarded["mapping_status"] == "needs_review"
    assert guarded["promotion_status"] == "needs_review"
    assert "promoted_mapping_changed" in guarded["validation_issues"]


def test_reviewed_promoted_mapping_is_preserved_without_reopening_review():
    payload = {
        "mapped_scheme_code": "100639",
        "mapped_family_id": "sbi-medium-to-long-duration-fund",
        "mapping_confidence": 100.0,
        "mapping_status": "mapped",
        "promotion_status": "staged",
        "validation_issues": [],
    }
    existing = {
        "mapped_scheme_code": "100640",
        "mapped_family_id": "sbi-medium-to-long-duration-fund",
        "mapping_confidence": 100.0,
        "promotion_status": "promoted",
        "promoted_scopes": ["benchmark", "manager", "risk", "ter_aum"],
        "promoted_scheme_code": "100640",
        "validation_issues": [parsing_service.MAPPING_REVIEW_KEEP_PROMOTED_TARGET],
    }

    guarded, changed = parsing_service.guard_promoted_mapping_change(existing, payload)

    assert changed is False
    assert guarded["mapped_scheme_code"] == "100640"
    assert guarded["mapping_status"] == "mapped"
    assert guarded["promotion_status"] == "promoted"
    assert "promoted_mapping_changed" not in guarded["validation_issues"]
