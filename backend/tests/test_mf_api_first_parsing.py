from __future__ import annotations

from app.mf_ingestion.services import parsing_service


class _FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class _FakeQuery:
    def __init__(self, root, table_name):
        self.root = root
        self.table_name = table_name
        self.eq_filters = {}
        self.in_filters = {}
        self.ilike_filters = {}
        self.update_payload = None
        self.delete_mode = False
        self.limit_value = None

    def select(self, _fields):
        return self

    def eq(self, key, value):
        self.eq_filters[key] = value
        return self

    def in_(self, key, values):
        self.in_filters[key] = list(values)
        return self

    def ilike(self, key, pattern):
        self.ilike_filters[key] = str(pattern).replace("%", "").lower()
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def update(self, payload):
        self.update_payload = payload
        return self

    def delete(self):
        self.delete_mode = True
        return self

    def execute(self):
        rows = list(self.root.tables.setdefault(self.table_name, []))
        for key, value in self.eq_filters.items():
            rows = [row for row in rows if str(row.get(key)) == str(value)]
        for key, values in self.in_filters.items():
            rows = [row for row in rows if row.get(key) in values or str(row.get(key)) in {str(value) for value in values}]
        for key, needle in self.ilike_filters.items():
            rows = [row for row in rows if needle in str(row.get(key) or "").lower()]

        if self.update_payload is not None:
            for row in rows:
                row.update(self.update_payload)
            self.root.updates.append((self.table_name, dict(self.eq_filters), dict(self.update_payload)))
            return _FakeResponse(rows)

        if self.delete_mode:
            self.root.deletes.append((self.table_name, dict(self.eq_filters)))
            return _FakeResponse(rows)

        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return _FakeResponse(rows)


class _FakeSupabase:
    def __init__(self):
        self.tables = {
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "120503",
                    "amc_name": "HDFC Mutual Fund",
                    "data_source": "mfapi+AMFI TER API",
                    "provider_payload": {
                        "official_source_trace": {
                            "amfi_ter_api": {
                                "source": "AMFI TER API",
                                "fields": ["expense_ratio"],
                            },
                        }
                    },
                    "aum": 1000,
                    "expense_ratio": 0.52,
                }
            ],
            "mutual_fund_holdings": [
                {
                    "scheme_code": 120503,
                    "as_of_date": "2026-04-01",
                    "source": "AMFI scheme-wise disclosure: HDFC Mutual Fund",
                    "security_name": "HDFC Bank Ltd.",
                }
            ],
            "mf_raw_documents": [{"id": "doc-1"}],
            "mf_parse_review_queue": [{"source_document_id": "doc-1"}],
        }
        self.updates = []
        self.deletes = []

    def table(self, name):
        return _FakeQuery(self, name)


class _FakeRepo:
    def __init__(self, client):
        self.supabase = client


def _service(fake_supabase):
    service = object.__new__(parsing_service.ParsingService)
    service.repository = _FakeRepo(fake_supabase)
    return service


def test_official_source_covered_portfolio_document_skips_parser_and_review_queue(monkeypatch):
    fake = _FakeSupabase()
    monkeypatch.setattr(parsing_service, "supabase", fake)
    service = _service(fake)

    result = service._parse_one(
        {
            "id": "doc-1",
            "amc_code": "hdfc",
            "document_type": "portfolio_disclosure",
            "report_month": "2026-04-01",
        }
    )

    assert result["status"] == "official_source_covered"
    assert result["reason"] == "skipped_official_source_covered:holdings"
    assert fake.tables["mf_raw_documents"][0]["parse_status"] == "official_source_covered"
    assert fake.tables["mf_raw_documents"][0]["validation_issues"] == ["skipped_official_source_covered:holdings"]
    assert fake.deletes == [("mf_parse_review_queue", {"source_document_id": "doc-1"})]


def test_missing_api_coverage_falls_back_to_existing_parser_path(monkeypatch):
    fake = _FakeSupabase()
    fake.tables["mutual_fund_holdings"] = []
    monkeypatch.setattr(parsing_service, "supabase", fake)
    service = _service(fake)
    service.r2_store = None
    service.config = None

    result = service._parse_one(
        {
            "id": "doc-1",
            "amc_code": "hdfc",
            "document_type": "portfolio_disclosure",
            "report_month": "2026-04-01",
            "storage_backend": "local",
            "storage_path": "missing.xlsx",
        }
    )

    assert result["status"] == "failed"
    assert result["reason"] == "raw_file_missing"
    assert fake.tables["mf_raw_documents"][0]["parse_status"] == "failed"


def test_mf_workflow_does_not_schedule_indianapi_or_mf_engine_for_mutual_funds():
    from pathlib import Path

    workflow = Path(".github/workflows/mf-sync.yml").read_text()

    assert "sync_mf_enrichment_unified" in workflow
    assert "sync_mf_engine_enrichment" not in workflow
    assert "sync_mf_from_indianapi" not in workflow
