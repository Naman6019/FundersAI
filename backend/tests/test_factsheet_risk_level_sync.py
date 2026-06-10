from __future__ import annotations

from datetime import date

from app.mf_ingestion.services import parsing_service


class _FakeRepository:
    supabase = object()

    def __init__(self, existing: dict | None = None):
        self.existing = existing or {
            "scheme_code": "122639",
            "scheme_name": "Parag Parikh Flexi Cap Fund",
            "provider_payload": {},
        }
        self.upserts: list[dict] = []

    def get_mutual_fund_core_snapshot(self, scheme_code):
        return dict(self.existing)

    def upsert_mutual_fund_core_snapshot_rows(self, rows):
        self.upserts.extend(rows)


def _service(repo: _FakeRepository):
    service = object.__new__(parsing_service.ParsingService)
    service.repository = repo
    service._resolve_scheme_code_for_scheme = lambda _name: "122639"
    return service


def test_amc_core_field_sync_writes_risk_level_and_trace():
    repo = _FakeRepository()
    service = _service(repo)

    written = service._upsert_amc_core_fields(
        amc_code="ppfas",
        scheme_name="Parag Parikh Flexi Cap Fund",
        report_month=date(2026, 4, 1),
        source_document_id="doc-1",
        source_url="https://example.test/factsheet.pdf",
        parser_version="factsheet-v1",
        aum=None,
        expense_ratio=None,
        benchmark=None,
        fund_manager=None,
        risk_level="Very High",
    )

    assert written is True
    row = repo.upserts[0]
    assert row["risk_level"] == "Very High"
    trace = row["provider_payload"]["amc_trace"]["risk_level"]
    assert trace["source_document_id"] == "doc-1"
    assert trace["source_url"] == "https://example.test/factsheet.pdf"
    assert trace["report_month"] == "2026-04-01"
    assert trace["parser_version"] == "factsheet-v1"
    assert trace["value"] == "Very High"


def test_amc_core_field_sync_does_not_replace_newer_official_risk_level():
    repo = _FakeRepository(
        {
            "scheme_code": "122639",
            "scheme_name": "Parag Parikh Flexi Cap Fund",
            "risk_level": "High",
            "provider_payload": {
                "amc_trace": {
                    "risk_level": {
                        "value": "High",
                        "report_month": "2026-05-01",
                    }
                }
            },
        }
    )
    service = _service(repo)

    written = service._upsert_amc_core_fields(
        amc_code="ppfas",
        scheme_name="Parag Parikh Flexi Cap Fund",
        report_month=date(2026, 4, 1),
        source_document_id="doc-1",
        source_url="https://example.test/factsheet.pdf",
        parser_version="factsheet-v1",
        aum=None,
        expense_ratio=None,
        benchmark=None,
        fund_manager=None,
        risk_level="Very High",
    )

    assert written is True
    assert repo.upserts == []
