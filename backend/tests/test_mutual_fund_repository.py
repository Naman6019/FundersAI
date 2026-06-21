from __future__ import annotations

from types import SimpleNamespace

from app.repositories.mutual_fund_repository import MutualFundRepository


class _FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)
        self.ilike_filters: list[tuple[str, str]] = []
        self.eq_filters: list[tuple[str, object]] = []
        self.limit_value = None

    def select(self, _fields: str, count=None):
        return self

    def ilike(self, key: str, pattern: str):
        self.ilike_filters.append((key, pattern))
        return self

    def eq(self, key: str, value):
        self.eq_filters.append((key, value))
        return self

    def limit(self, value: int):
        self.limit_value = value
        return self

    def execute(self):
        rows = list(self.rows)
        for key, pattern in self.ilike_filters:
            tokens = [token.lower() for token in pattern.split("%") if token]
            rows = [row for row in rows if all(token in str(row.get(key) or "").lower() for token in tokens)]
        for key, value in self.eq_filters:
            rows = [row for row in rows if str(row.get(key)) == str(value)]
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return SimpleNamespace(data=rows)


class _FakeSupabase:
    def __init__(self, tables: dict[str, list[dict]]):
        self.tables = tables

    def table(self, name: str):
        return _FakeQuery(self.tables.get(name, []))


def test_search_mutual_funds_infers_missing_variant_fields_from_scheme_name():
    source_row = {
        "scheme_code": "118955",
        "scheme_name": "HDFC Flexi Cap Fund - Growth Option - Direct Plan",
        "plan_type": None,
        "option_type": None,
    }
    repo = MutualFundRepository(
        _FakeSupabase({"mutual_fund_core_snapshot": [source_row], "mutual_funds": []})
    )

    rows = repo.search_mutual_funds("%HDFC%Flexi%Cap%", plan_type="Direct", option_type="Growth")

    assert rows[0]["plan_type"] == "Direct"
    assert rows[0]["option_type"] == "Growth"
    assert source_row["plan_type"] is None
    assert source_row["option_type"] is None


def test_search_mutual_funds_preserves_existing_variant_fields():
    repo = MutualFundRepository(
        _FakeSupabase(
            {
                "mutual_fund_core_snapshot": [
                    {
                        "scheme_code": "regular-1",
                        "scheme_name": "Axis Large Cap Fund - Regular Plan - IDCW",
                        "plan_type": "Regular",
                        "option_type": "Dividend",
                    }
                ],
                "mutual_funds": [],
            }
        )
    )

    rows = repo.search_mutual_funds("%Axis%Large%Cap%", plan_type="Regular", option_type=None)

    assert rows[0]["plan_type"] == "Regular"
    assert rows[0]["option_type"] == "Dividend"


def test_search_mutual_funds_normalizes_legacy_table_fallback_rows():
    repo = MutualFundRepository(
        _FakeSupabase(
            {
                "mutual_fund_core_snapshot": [],
                "mutual_funds": [
                    {
                        "scheme_code": "legacy-idcw",
                        "scheme_name": "SBI Contra Fund - Direct Plan - IDCW",
                        "plan_type": None,
                        "option_type": None,
                    }
                ],
            }
        )
    )

    rows = repo.search_mutual_funds("%SBI%Contra%", plan_type="Direct", option_type=None)

    assert rows[0]["plan_type"] == "Direct"
    assert rows[0]["option_type"] == "IDCW"
