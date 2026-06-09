from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import sync_mf_metadata as metadata


class _FakeTable:
    def __init__(self, root, table_name: str):
        self.root = root
        self.table_name = table_name
        self.in_filters = {}
        self.upsert_payload = None

    def select(self, _fields: str):
        return self

    def in_(self, key: str, values):
        self.in_filters[key] = [str(value) for value in values]
        return self

    def upsert(self, payload, on_conflict=None):
        self.upsert_payload = payload
        self.root.upserts.append((self.table_name, payload, on_conflict))
        return self

    def execute(self):
        rows = list(self.root.tables.get(self.table_name, []))
        for key, values in self.in_filters.items():
            rows = [row for row in rows if str(row.get(key)) in values]
        return SimpleNamespace(data=rows)


class _FakeSupabase:
    def __init__(self, existing_core: dict):
        self.tables = {
            "mutual_fund_core_snapshot": [existing_core],
            "mutual_funds": [],
        }
        self.upserts = []

    def table(self, name: str):
        return _FakeTable(self, name)


def _snapshot_upsert(fake: _FakeSupabase) -> dict:
    for table_name, payload, _conflict in fake.upserts:
        if table_name == "mutual_fund_core_snapshot":
            return payload[0]
    raise AssertionError("mutual_fund_core_snapshot was not upserted")


def _existing_core() -> dict:
    return {
        "scheme_code": "120503",
        "scheme_name": "Existing Fund",
        "amc_name": "HDFC Mutual Fund",
        "category": "Equity",
        "sub_category": "Flexi Cap",
        "nav": 123.45,
        "nav_date": "2026-06-04",
        "expense_ratio": 0.52,
        "aum": 1000.0,
        "benchmark": "NIFTY 500 TRI",
        "fund_manager": "Existing Manager",
        "data_source": "amfi_navall+AMFI AUM API",
        "provider_payload": {},
    }


def test_ter_update_preserves_existing_aum():
    fake = _FakeSupabase(_existing_core())

    metadata.update_funds(
        fake,
        [
            {
                "scheme_code": 120503,
                "scheme_name": "Existing Fund",
                "fund_house": "HDFC Mutual Fund",
                "expense_ratio": 0.61,
            }
        ],
        "AMFI TER API",
    )

    snapshot = _snapshot_upsert(fake)
    assert snapshot["expense_ratio"] == 0.61
    assert snapshot["aum"] == 1000.0


def test_aum_update_preserves_existing_expense_ratio():
    fake = _FakeSupabase(_existing_core())

    metadata.update_funds(
        fake,
        [
            {
                "scheme_code": 120503,
                "scheme_name": "Existing Fund",
                "fund_house": "HDFC Mutual Fund",
                "aum": 1200.0,
            }
        ],
        "AMFI AUM API",
    )

    snapshot = _snapshot_upsert(fake)
    assert snapshot["aum"] == 1200.0
    assert snapshot["expense_ratio"] == 0.52


def test_empty_incoming_metadata_does_not_wipe_existing_snapshot_fields():
    fake = _FakeSupabase(_existing_core())
    update = metadata.build_fund_update(
        {
            "scheme_code": 120503,
            "scheme_name": "Existing Fund",
            "fund_house": "Unknown",
            "category": "Unknown",
            "sub_category": "Unknown",
            "nav": 0,
            "nav_date": None,
        },
        {"aum": 1300.0},
    )

    metadata.update_funds(fake, [update], "AMFI AUM API")

    snapshot = _snapshot_upsert(fake)
    assert snapshot["aum"] == 1300.0
    assert snapshot["expense_ratio"] == 0.52
    assert snapshot["category"] == "Equity"
    assert snapshot["sub_category"] == "Flexi Cap"
    assert snapshot["nav"] == 123.45
    assert snapshot["nav_date"] == "2026-06-04"
    assert snapshot["benchmark"] == "NIFTY 500 TRI"
    assert snapshot["fund_manager"] == "Existing Manager"
