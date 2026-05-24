from __future__ import annotations

from datetime import datetime, timezone

from app.mf_ingestion.jobs import reparse_needs_review


class _FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class _FakeQuery:
    def __init__(self, root, table_name):
        self.root = root
        self.table_name = table_name
        self.in_filters = {}
        self.eq_filters = {}
        self.update_payload = None
        self.limit_value = None
        self.delete_mode = False

    def select(self, _fields):
        return self

    def in_(self, key, values):
        self.in_filters[key] = list(values)
        return self

    def eq(self, key, value):
        self.eq_filters[key] = value
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
        for key, values in self.in_filters.items():
            rows = [row for row in rows if row.get(key) in values]
        for key, value in self.eq_filters.items():
            rows = [row for row in rows if str(row.get(key)) == str(value)]

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
    def __init__(self, docs):
        self.tables = {
            "mf_raw_documents": docs,
            "mf_parse_review_queue": [],
        }
        self.updates = []
        self.deletes = []

    def table(self, name):
        return _FakeQuery(self, name)


class _FakeService:
    def __init__(self, status_by_id):
        self.status_by_id = status_by_id

    def _parse_one(self, document):
        doc_id = document["id"]
        return {"source_document_id": doc_id, "status": self.status_by_id.get(doc_id, "needs_review")}


def test_load_retry_documents_filters_by_amc_status_age_and_limit():
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    fake_supabase = _FakeSupabase(
        [
            {
                "id": "old-sbi-review",
                "amc_code": "SBI",
                "parse_status": "needs_review",
                "parsed_at": "2026-05-25T01:00:00+00:00",
                "downloaded_at": "2026-05-24T23:00:00+00:00",
            },
            {
                "id": "fresh-sbi-review",
                "amc_code": "SBI",
                "parse_status": "needs_review",
                "parsed_at": "2026-05-25T10:00:00+00:00",
            },
            {
                "id": "old-hdfc-review",
                "amc_code": "HDFC",
                "parse_status": "needs_review",
                "parsed_at": "2026-05-25T01:00:00+00:00",
            },
            {
                "id": "old-sbi-parsed",
                "amc_code": "SBI",
                "parse_status": "parsed",
                "parsed_at": "2026-05-25T01:00:00+00:00",
            },
        ]
    )

    docs = reparse_needs_review.load_retry_documents(
        supabase_client=fake_supabase,
        statuses=["needs_review", "failed"],
        amc="sbi",
        limit=1,
        min_age_hours=6,
        now=now,
    )

    assert [doc["id"] for doc in docs] == ["old-sbi-review"]


def test_reparse_documents_returns_zero_runtime_errors_for_still_review(monkeypatch):
    fake_supabase = _FakeSupabase(
        [
            {"id": "doc-1", "amc_code": "SBI", "parse_status": "needs_review"},
            {"id": "doc-2", "amc_code": "SBI", "parse_status": "failed"},
        ]
    )
    monkeypatch.setattr(reparse_needs_review, "supabase", fake_supabase)

    summary = reparse_needs_review.reparse_documents(
        fake_supabase.tables["mf_raw_documents"],
        _FakeService({"doc-1": "needs_review", "doc-2": "parsed"}),
    )

    assert summary == {
        "success_count": 1,
        "still_actionable_count": 1,
        "runtime_error_count": 0,
    }
    assert fake_supabase.tables["mf_raw_documents"][0]["parse_status"] == "needs_reparse"
    assert fake_supabase.deletes == [("mf_parse_review_queue", {"source_document_id": "doc-2"})]
