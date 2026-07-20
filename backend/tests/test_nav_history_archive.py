from __future__ import annotations

from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

from app.mf_ingestion.jobs import archive_mf_nav_history
from backend.scripts import check_nav_cache_drop_readiness


ROWS = [
    {"scheme_code": "100", "nav_date": "2025-12-31", "nav": 10},
    {"scheme_code": "100", "nav_date": "2026-01-01", "nav": 11},
    {"scheme_code": "200", "nav_date": "2026-01-01", "nav": 20},
]


class Query:
    def __init__(self, rows, database_count):
        self.rows = rows
        self.database_count = database_count
        self.start = 0
        self.end = 0
        self.count_requested = False

    def select(self, _fields, count=None):
        self.count_requested = count == "exact"
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, start, end):
        self.start = start
        self.end = end
        return self

    def execute(self):
        data = self.rows[self.start:self.end + 1]
        count = self.database_count if self.count_requested else None
        return SimpleNamespace(data=data, count=count)


class FakeSupabase:
    def __init__(self, rows, database_count):
        self.rows = rows
        self.database_count = database_count

    def table(self, name):
        assert name == "mutual_fund_nav_history"
        return Query(self.rows, self.database_count)


class FakeStore:
    enabled = True

    def __init__(self):
        self.objects = {}

    def upload_bytes(self, key, content, **_kwargs):
        self.objects[key] = content

    def object_exists(self, key, **_kwargs):
        return key in self.objects


def _setup(monkeypatch, database_count):
    store = FakeStore()
    manifests = []
    monkeypatch.setattr(archive_mf_nav_history, "supabase", FakeSupabase(ROWS, database_count))
    monkeypatch.setattr(
        archive_mf_nav_history,
        "get_config",
        lambda: SimpleNamespace(r2_cold_bucket="cold"),
    )
    monkeypatch.setattr(archive_mf_nav_history, "build_r2_store", lambda _config: store)
    monkeypatch.setattr(archive_mf_nav_history, "encode_rows_as_archive", lambda rows: (str(rows).encode(), "application/gzip"))
    monkeypatch.setattr(archive_mf_nav_history, "write_manifest", lambda **kwargs: manifests.append(kwargs))
    return store, manifests


def test_full_archive_groups_by_scheme_and_year_and_verifies_counts(monkeypatch):
    store, manifests = _setup(monkeypatch, database_count=len(ROWS))

    report = archive_mf_nav_history.run_archive(page_size=2, verify=True)

    assert report["archive_verified"] is True
    assert report["database_row_count"] == report["archived_row_count"] == 3
    assert report["object_count"] == 3
    assert len(store.objects) == len(manifests) == 3
    assert all(item.get("checksum") for item in manifests)


def test_archive_count_mismatch_blocks_drop(monkeypatch):
    _setup(monkeypatch, database_count=len(ROWS) + 1)

    report = archive_mf_nav_history.run_archive(page_size=2, verify=True)

    assert report["archive_verified"] is False
    assert any(error.startswith("row_count_mismatch") for error in report["failures"])


def test_drop_readiness_requires_observation_hits_refreshes_and_archive(monkeypatch):
    now = datetime(2026, 7, 17, tzinfo=timezone.utc)
    rows = [
        {
            "endpoint": "nav_cache/refresh" if index == 0 else "nav_cache/hit",
            "created_at": (now - timedelta(days=8) + timedelta(hours=index)).isoformat(),
            "success": True,
        }
        for index in range(10)
    ]
    monkeypatch.setattr(check_nav_cache_drop_readiness, "get_usage_rows", lambda *_args, **_kwargs: rows)
    monkeypatch.setattr(check_nav_cache_drop_readiness, "get_first_usage_row", lambda *_args, **_kwargs: rows[0])
    monkeypatch.setattr(check_nav_cache_drop_readiness, "_runtime_legacy_references", lambda: [])

    report = check_nav_cache_drop_readiness.build_readiness_report({"archive_verified": True}, now=now)

    assert report["drop_ready"] is True
    assert report["metrics"]["hits"] == 9
    assert report["metrics"]["refreshes"] == 1


def test_drop_readiness_fails_before_seven_day_window(monkeypatch):
    now = datetime(2026, 7, 17, tzinfo=timezone.utc)
    rows = [
        {
            "endpoint": "nav_cache/refresh" if index == 0 else "nav_cache/hit",
            "created_at": (now - timedelta(days=2) + timedelta(hours=index)).isoformat(),
            "success": True,
        }
        for index in range(10)
    ]
    monkeypatch.setattr(check_nav_cache_drop_readiness, "get_usage_rows", lambda *_args, **_kwargs: rows)
    monkeypatch.setattr(check_nav_cache_drop_readiness, "get_first_usage_row", lambda *_args, **_kwargs: rows[0])
    monkeypatch.setattr(check_nav_cache_drop_readiness, "_runtime_legacy_references", lambda: [])

    report = check_nav_cache_drop_readiness.build_readiness_report({"archive_verified": True}, now=now)

    assert report["drop_ready"] is False
    assert report["checks"]["observation_window_complete"] is False
