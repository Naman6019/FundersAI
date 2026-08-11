from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.mf_ingestion.services import parsing_service


class _FakeQuery:
    def __init__(self, root, table: str):
        self.root = root
        self.table = table

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def upsert(self, payload, on_conflict=None):
        self.root.upserts.append((self.table, payload, on_conflict))
        return self

    def execute(self):
        return SimpleNamespace(data=[])


class _FakeSupabase:
    def __init__(self):
        self.upserts = []

    def table(self, table: str):
        return _FakeQuery(self, table)


class _KotakRepository:
    supabase = object()

    def get_mutual_fund_core_snapshot(self, scheme_code: str):
        assert scheme_code == "123456"
        return {
            "scheme_code": scheme_code,
            "scheme_name": "Kotak Multi Asset Allocation Fund - Direct Plan - Growth",
            "amc_name": "Kotak Mahindra Mutual Fund",
        }


def test_kotak_scheme_isin_mapping_uses_internal_exact_lookup_not_name_fuzzy_match(monkeypatch):
    fake_supabase = _FakeSupabase()
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)
    service = object.__new__(parsing_service.ParsingService)
    service.repository = _KotakRepository()
    service._resolve_scheme_code_for_scheme = lambda _name: (_ for _ in ()).throw(
        AssertionError("Kotak source ISIN must bypass fuzzy name resolution")
    )
    service._resolve_scheme_code_for_scheme_isin = lambda isin: "123456" if isin == "INF123456789" else None
    service._resolve_family_id_for_scheme = lambda _code: "kotak-multi-asset-allocation"

    staged = service._stage_amc_core_fields(
        amc_code="kotak",
        scheme_name="Kotak Multi Asset Allocation Fund - Direct Growth",
        report_month=date(2026, 7, 1),
        source_document_id="00000000-0000-0000-0000-000000000011",
        source_url="https://www.kotakmf.com/Information/forms-and-downloads/Factsheet/Factsheet_for_July_2026/KotakMFFactsheetJuly2026.pdf",
        parser_version="factsheet-v1",
        aum=100.0,
        expense_ratio=None,
        benchmark=None,
        fund_manager=None,
        risk_level=None,
        scheme_isin="INF123456789",
    )

    assert staged is True
    payload = fake_supabase.upserts[0][1]
    assert payload["scheme_isin"] == "INF123456789"
    assert payload["mapped_scheme_code"] == "123456"
    assert payload["mapping_confidence"] == 100.0


def test_kotak_missing_internal_scheme_isin_is_review_not_fuzzy_fallback():
    service = object.__new__(parsing_service.ParsingService)
    service._resolve_scheme_code_for_scheme = lambda _name: (_ for _ in ()).throw(
        AssertionError("an unresolved source ISIN must not fall back to fuzzy mapping")
    )
    service._resolve_scheme_code_for_scheme_isin = lambda _isin: None

    assert service._resolve_staged_mapping(
        "kotak",
        "Kotak Multi Asset Allocation Fund - Direct Growth",
        scheme_isin="INF123456789",
    ) == (None, None, 0.0, "needs_review")
