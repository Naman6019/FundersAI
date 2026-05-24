import pytest
from fastapi import HTTPException


class _FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class _FakeQuery:
    def __init__(self, table_name, rows):
        self.table_name = table_name
        self.rows = rows
        self.filters = {}
        self.update_payload = None
        self.limit_value = None

    def select(self, _fields, count=None):
        return self

    def update(self, payload):
        self.update_payload = payload
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def execute(self):
        matched = [
            row for row in self.rows
            if all(str(row.get(key)) == str(value) for key, value in self.filters.items())
        ]
        if self.update_payload is not None:
            for row in matched:
                row.update(self.update_payload)
            return _FakeResponse(data=matched)
        if self.limit_value is not None:
            matched = matched[: self.limit_value]
        return _FakeResponse(data=matched)


class _FakeSupabase:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _FakeQuery(name, self.tables.setdefault(name, []))


def test_request_reparse_marks_document_for_existing_flow(monkeypatch):
    from app import main as app_main

    fake_supabase = _FakeSupabase({
        "mf_raw_documents": [
            {"id": "doc-1", "parse_status": "needs_review", "validation_issues": ["low_confidence"]},
        ],
        "mf_parse_review_queue": [
            {"source_document_id": "doc-1", "status": "pending_review"},
        ],
    })
    monkeypatch.setattr(app_main, "supabase", fake_supabase)

    payload = app_main._request_mf_document_reparse("doc-1", "try parser again")

    document = fake_supabase.tables["mf_raw_documents"][0]
    review_item = fake_supabase.tables["mf_parse_review_queue"][0]
    assert payload["action"] == "reparse_requested"
    assert document["parse_status"] == "needs_reparse"
    assert document["validation_issues"] == []
    assert "updated_at" in document
    assert review_item["status"] == "reparse_requested"
    assert review_item["reviewer_notes"] == "try parser again"


def test_resolve_review_marks_document_parsed_and_approves_queue(monkeypatch):
    from app import main as app_main

    fake_supabase = _FakeSupabase({
        "mf_raw_documents": [
            {"id": "doc-1", "parse_status": "needs_review", "validation_issues": ["manual_check"]},
        ],
        "mf_parse_review_queue": [
            {"source_document_id": "doc-1", "status": "pending_review"},
        ],
    })
    monkeypatch.setattr(app_main, "supabase", fake_supabase)

    payload = app_main._resolve_mf_document_review("doc-1", "safe to clear")

    document = fake_supabase.tables["mf_raw_documents"][0]
    review_item = fake_supabase.tables["mf_parse_review_queue"][0]
    assert payload["action"] == "resolved"
    assert document["parse_status"] == "parsed"
    assert document["validation_issues"] == []
    assert "parsed_at" in document
    assert review_item["status"] == "approved"
    assert review_item["reviewer_notes"] == "safe to clear"


def test_skip_review_marks_document_skipped_and_clears_queue(monkeypatch):
    from app import main as app_main

    fake_supabase = _FakeSupabase({
        "mf_raw_documents": [
            {"id": "doc-1", "parse_status": "failed", "validation_issues": ["parse_exception:RuntimeError"]},
        ],
        "mf_parse_review_queue": [
            {"source_document_id": "doc-1", "status": "pending_review"},
        ],
    })
    monkeypatch.setattr(app_main, "supabase", fake_supabase)

    payload = app_main._skip_mf_document_review("doc-1", "not a parseable disclosure")

    document = fake_supabase.tables["mf_raw_documents"][0]
    review_item = fake_supabase.tables["mf_parse_review_queue"][0]
    assert payload["action"] == "skipped"
    assert document["parse_status"] == "skipped_not_supported"
    assert "skipped_irrelevant_document" in document["validation_issues"]
    assert "parsed_at" in document
    assert review_item["status"] == "skipped"
    assert review_item["reviewer_notes"] == "not a parseable disclosure"


def test_review_action_rejects_non_review_document(monkeypatch):
    from app import main as app_main

    fake_supabase = _FakeSupabase({
        "mf_raw_documents": [
            {"id": "doc-1", "parse_status": "parsed", "validation_issues": []},
        ],
        "mf_parse_review_queue": [],
    })
    monkeypatch.setattr(app_main, "supabase", fake_supabase)

    with pytest.raises(HTTPException) as exc:
        app_main._request_mf_document_reparse("doc-1")

    assert exc.value.status_code == 409
    assert exc.value.detail == "document_not_actionable"


def test_admin_review_endpoint_requires_admin_key(monkeypatch):
    from app import main as app_main

    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "expected-secret")

    with pytest.raises(HTTPException) as exc:
        app_main.admin_request_mf_document_reparse("doc-1", x_admin_key="wrong-secret")

    assert exc.value.status_code == 403
