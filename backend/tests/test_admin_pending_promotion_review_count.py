import pytest
from app.exceptions import AppServiceError


class _FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.null_filters = {}

    def select(self, _fields):
        return self

    def is_(self, key, value):
        self.null_filters[key] = value
        return self

    def execute(self):
        data = list(self.rows)
        for key, value in self.null_filters.items():
            if value == "null":
                data = [row for row in data if row.get(key) is None]
        return _FakeResponse(data=data)


class _FakeSupabase:
    def __init__(self, decision_rows):
        self.decision_rows = decision_rows

    def table(self, name):
        if name == "mf_promotion_review_decisions":
            return _FakeQuery(self.decision_rows)
        return _FakeQuery([])


def test_require_admin_key_rejects_wrong_key(monkeypatch):
    from app.services import admin_service as app_main

    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "expected-secret")
    with pytest.raises(AppServiceError) as exc:
        app_main._require_admin_key("wrong-secret")
    assert exc.value.status_code == 403


def test_pending_promotion_review_count_groups_by_amc_and_resolution(monkeypatch):
    from app.services import admin_service as app_main

    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "expected-secret")

    decision_rows = [
        {"amc_code": "icici", "scope": "risk", "resolution": "use_staged", "promoted_at": None},
        {"amc_code": "icici", "scope": "risk", "resolution": "use_staged", "promoted_at": None},
        {"amc_code": "icici", "scope": "risk", "resolution": "use_live", "promoted_at": None},
        {"amc_code": "kotak", "scope": "holdings", "resolution": "use_staged", "promoted_at": None},
        # already promoted -- excluded by the promoted_at is null filter
        {"amc_code": "kotak", "scope": "holdings", "resolution": "use_staged", "promoted_at": "2026-08-10T00:00:00Z"},
    ]
    app_main._current_admin_repository.set(_FakeSupabase(decision_rows))

    payload = app_main.admin_pending_promotion_review_count(x_admin_key="expected-secret")

    assert payload["status"] == "ok"
    assert payload["total_pending"] == 4
    assert payload["actionable_pending"] == 3  # use_staged only
    by_amc = {row["amc_code"]: row for row in payload["pending_by_amc"]}
    assert by_amc["icici"] == {"amc_code": "icici", "use_staged": 2, "use_live": 1, "exclude": 0}
    assert by_amc["kotak"] == {"amc_code": "kotak", "use_staged": 1, "use_live": 0, "exclude": 0}


def test_pending_promotion_review_count_empty_when_nothing_pending(monkeypatch):
    from app.services import admin_service as app_main

    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "expected-secret")
    app_main._current_admin_repository.set(_FakeSupabase([]))

    payload = app_main.admin_pending_promotion_review_count(x_admin_key="expected-secret")

    assert payload == {
        "status": "ok",
        "total_pending": 0,
        "actionable_pending": 0,
        "pending_by_amc": [],
    }
