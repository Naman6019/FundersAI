from __future__ import annotations

from backend.scripts.sync_mf import (
    _build_core_snapshot_row,
    _build_missing_etf_family_mappings,
    main,
    parse_amfi_nav_payload,
)


def test_parse_amfi_nav_payload_keeps_direct_growth_and_eight_column_etf_rows():
    payload = "\n".join(
        [
            "1|INF000A00001|-|Example Fund - Direct Growth|10.0|21-Aug-2026",
            "154535;INF754K01XI7;-;Edelweiss BSE LargeMid (60:40) Stable dividend 50 ETF;;;36.835;21-Aug-2026",
            "2|INF000A00002|-|Example Fund - Regular Growth|11.0|21-Aug-2026",
        ]
    )

    rows = parse_amfi_nav_payload(payload)

    assert [row["scheme_code"] for row in rows] == [1, 154535]
    assert rows[1]["isin"] == "INF754K01XI7"
    assert rows[1]["amc_name"] == "Edelweiss Mutual Fund"
    assert rows[1]["nav"] == 36.835
    assert rows[1]["nav_date"] == "2026-08-21"


def test_parse_amfi_nav_payload_keeps_current_amfi_direct_plan_growth_rows():
    rows = parse_amfi_nav_payload(
        "122639;INF879O01027;-;Parag Parikh Flexi Cap Fund;Direct Plan;Growth;90.6349;03-Sep-2026"
    )

    assert len(rows) == 1
    assert rows[0]["scheme_code"] == 122639
    assert rows[0]["scheme_name"] == "Parag Parikh Flexi Cap Fund - Direct Plan - Growth"
    assert rows[0]["isin"] == "INF879O01027"
    assert rows[0]["nav"] == 90.6349
    assert rows[0]["nav_date"] == "2026-09-03"


def test_parse_amfi_nav_payload_rejects_rows_without_an_official_nav_date():
    rows = parse_amfi_nav_payload(
        "1|INF000A00001|-|Example Fund - Direct Growth|10.0|not-a-date"
    )

    assert rows == []


def test_core_snapshot_backfills_missing_amc_name_without_overwriting_existing_value():
    update = {
        "scheme_code": 154535,
        "scheme_name": "Edelweiss BSE LargeMid (60:40) Stable dividend 50 ETF",
        "amc_name": "Edelweiss Mutual Fund",
        "nav": 36.835,
        "nav_date": "2026-08-21",
    }

    repaired = _build_core_snapshot_row(update, {"amc_name": None})
    retained = _build_core_snapshot_row(update, {"amc_name": "Existing AMC Label"})

    assert repaired["amc_name"] == "Edelweiss Mutual Fund"
    assert retained["amc_name"] == "Existing AMC Label"


def test_missing_etf_family_mapping_does_not_overwrite_existing_mapping():
    rows = [
        {"scheme_code": 154535, "scheme_name": "Edelweiss BSE LargeMid (60:40) Stable dividend 50 ETF"},
        {"scheme_code": 154347, "scheme_name": "Edelweiss Nifty Next 50 ETF"},
    ]

    mappings = _build_missing_etf_family_mappings(rows, {"154347": {"family_id": "existing"}})

    assert mappings == [
        {
            "scheme_code": "154535",
            "family_id": "edelweiss-bse-largemid-60-40-stable-dividend-50-etf",
            "confidence": 0.9,
            "source": "amfi-navall-etf-v1",
        }
    ]


def test_nav_only_mode_skips_family_mapping_writes(monkeypatch):
    monkeypatch.setattr("backend.scripts.sync_mf.SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr("backend.scripts.sync_mf.SUPABASE_KEY", "test-key")
    monkeypatch.setattr(
        "backend.scripts.sync_mf.fetch_amfi_nav",
        lambda: [{"scheme_code": 1, "scheme_name": "Example Fund - Direct Growth", "nav": 10.0, "nav_date": "2026-09-03"}],
    )

    calls: list[str] = []

    class _Query:
        data: list[dict] = []

        def select(self, _fields):
            return self

        def in_(self, _field, _values):
            return self

        def upsert(self, _rows, **_kwargs):
            return self

        def execute(self):
            return self

    class _Client:
        def table(self, name):
            calls.append(name)
            return _Query()

    monkeypatch.setattr("backend.scripts.sync_mf.create_client", lambda *_args: _Client())

    main(["--nav-only"])

    assert "mutual_fund_family_mapping" not in calls
