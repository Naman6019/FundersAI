from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.repositories.stock_repository import StockRepository


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.cutoff = None
        self.null_field = None
        self.limit_value = None
        self.update_payload = None

    def select(self, _fields):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def is_(self, field, value):
        if value == "null":
            self.null_field = field
        return self

    def lte(self, field, value):
        self.cutoff = (field, value)
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def update(self, payload):
        self.update_payload = payload
        return self

    def execute(self):
        matched = list(self.rows)
        for field, value in self.filters:
            matched = [row for row in matched if row.get(field) == value]
        if self.null_field:
            matched = [row for row in matched if row.get(self.null_field) is None]
        if self.cutoff:
            field, value = self.cutoff
            matched = [row for row in matched if str(row.get(field) or "") <= value]
        if self.limit_value is not None:
            matched = matched[: self.limit_value]
        if self.update_payload is not None:
            for row in matched:
                row.update(self.update_payload)
        return SimpleNamespace(data=[dict(row) for row in matched])


class Client:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        assert name == "data_provider_runs"
        return Query(self.rows)


def test_only_stale_unfinished_running_provider_runs_are_reconciled():
    now = datetime(2026, 8, 5, 12, tzinfo=timezone.utc)
    rows = [
        {"id": "stale", "status": "running", "started_at": "2026-08-05T01:00:00+00:00", "finished_at": None, "metadata": {"source": "test"}},
        {"id": "fresh", "status": "running", "started_at": "2026-08-05T11:00:00+00:00", "finished_at": None, "metadata": {}},
        {"id": "finished", "status": "running", "started_at": "2026-08-05T01:00:00+00:00", "finished_at": "2026-08-05T02:00:00+00:00", "metadata": {}},
        {"id": "failed", "status": "failed", "started_at": "2026-08-05T01:00:00+00:00", "finished_at": None, "metadata": {}},
    ]
    repo = StockRepository(client=Client(rows))

    assert repo.reconcile_stale_provider_runs(stale_after=timedelta(hours=6), now=now) == 1
    stale = rows[0]
    assert stale["status"] == "timed_out"
    assert stale["finished_at"] == now.isoformat()
    assert stale["metadata"]["source"] == "test"
    assert stale["metadata"]["reconciliation_reason"] == "stale_running_timeout"
    assert rows[1]["status"] == "running"
    assert rows[2]["status"] == "running"
    assert rows[3]["status"] == "failed"

    assert repo.reconcile_stale_provider_runs(stale_after=timedelta(hours=6), now=now) == 0
