from datetime import datetime, timezone
from types import SimpleNamespace

from app.services import provider_usage


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def lt(self, *_args, **_kwargs):
        return self

    def like(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


def test_usage_queries_return_rows_when_supabase_is_configured(monkeypatch):
    rows = [{"endpoint": "nav_cache/hit", "created_at": "2026-07-20T00:00:00+00:00", "request_cost": 0}]
    monkeypatch.setattr(provider_usage, "supabase", SimpleNamespace(table=lambda _name: _Query(rows)))
    start = datetime(2026, 7, 1, tzinfo=timezone.utc)
    end = datetime(2026, 8, 1, tzinfo=timezone.utc)

    assert provider_usage.get_usage_rows("mfapi", start, end) == rows
    assert provider_usage.get_first_usage_row("mfapi", start, end, endpoint_prefix="nav_cache/") == rows[0]
