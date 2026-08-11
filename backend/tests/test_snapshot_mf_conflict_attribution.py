from __future__ import annotations

from scripts import snapshot_mf_conflict_attribution as snapshot_module


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, store, amc_code=None):
        self._store = store
        self._amc_code = amc_code
        self._insert_payload = None
        self._limit = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        assert column == "amc_code"
        self._amc_code = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, count):
        self._limit = count
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def execute(self):
        if self._insert_payload is not None:
            row = {"id": f"snap-{len(self._store['rows']) + 1}", **self._insert_payload}
            self._store["rows"].append(row)
            return _FakeResult([row])
        matching = [row for row in self._store["rows"] if row["amc_code"] == self._amc_code]
        matching.sort(key=lambda row: row.get("taken_at") or "", reverse=True)
        limited = matching[: self._limit] if self._limit else matching
        return _FakeResult(limited)


class _FakeTable:
    def __init__(self, store):
        self._store = store

    def __call__(self, name):
        assert name == snapshot_module.SNAPSHOT_TABLE
        return _FakeQuery(self._store)


class _FakeSupabase:
    def __init__(self, existing_rows):
        self._store = {"rows": list(existing_rows)}
        self.table = _FakeTable(self._store)


def test_take_snapshot_records_a_row_per_amc_and_reports_none_delta_on_first_run(monkeypatch):
    fake_supabase = _FakeSupabase(existing_rows=[])
    monkeypatch.setattr(snapshot_module, "supabase", fake_supabase)
    monkeypatch.setattr(
        snapshot_module,
        "build_conflict_attribution",
        lambda **_kwargs: {
            "amcs": {
                "kotak": {"total_conflicts": 5, "by_cause": {"holdings_out_of_band_total": 5}, "contributing_tags": {}},
                "hdfc": {"total_conflicts": 0, "by_cause": {}, "contributing_tags": {}},
            }
        },
    )

    results = snapshot_module.take_snapshot(amcs=["kotak", "hdfc"], report_months=["2026-06-01"])

    assert results["kotak"]["total_conflicts"] == 5
    assert results["kotak"]["previous_total_conflicts"] is None
    assert results["kotak"]["delta"] is None
    assert results["hdfc"]["total_conflicts"] == 0
    assert len(fake_supabase._store["rows"]) == 2


def test_take_snapshot_computes_delta_against_most_recent_prior_snapshot(monkeypatch):
    fake_supabase = _FakeSupabase(
        existing_rows=[
            {
                "id": "old-1",
                "amc_code": "kotak",
                "taken_at": "2026-08-01T00:00:00Z",
                "total_conflicts": 12,
                "by_cause": {},
            }
        ]
    )
    monkeypatch.setattr(snapshot_module, "supabase", fake_supabase)
    monkeypatch.setattr(
        snapshot_module,
        "build_conflict_attribution",
        lambda **_kwargs: {
            "amcs": {"kotak": {"total_conflicts": 3, "by_cause": {}, "contributing_tags": {}}}
        },
    )

    results = snapshot_module.take_snapshot(amcs=["kotak"], report_months=["2026-08-01"])

    assert results["kotak"]["previous_total_conflicts"] == 12
    assert results["kotak"]["delta"] == 3 - 12
    # The parser fix landed: this should read as a large negative delta (conflicts shrank).
    assert results["kotak"]["delta"] == -9
