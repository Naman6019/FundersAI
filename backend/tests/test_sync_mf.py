from __future__ import annotations

from backend.scripts.sync_mf import (
    _MUTUAL_FUNDS_MIRROR_COLUMNS,
    _build_core_snapshot_row,
    _build_missing_etf_family_mappings,
    main,
    parse_amfi_nav_payload,
)
from app.services.mf_catalog_service import CATEGORIES


# ─── Category capture from AMFI section headers ──────────────────────────────
#
# AMFI publishes the SEBI category as a header above each scheme group, not as a column. These
# headers were previously discarded, which left `category` NULL and blocked fund pages.

_CATEGORY_PAYLOAD = "\n".join(
    [
        "Open Ended Schemes(Debt Scheme - Gilt Fund)",
        "",
        "Bajaj Finserv Mutual Fund",
        "",
        "153206;INF0QA701AP9;-;Bajaj Finserv Gilt Fund;Direct Plan;Growth;1076.1554;21-Sep-2026",
        "Open Ended Schemes(Equity Scheme - Flexi Cap Fund)",
        "",
        "Parag Parikh Mutual Fund",
        "",
        "122639;INF879O01019;-;Parag Parikh Flexi Cap Fund;Direct Plan;Growth;89.7169;21-Sep-2026",
    ]
)


def test_rows_carry_the_amfi_category_header_above_them():
    rows = parse_amfi_nav_payload(_CATEGORY_PAYLOAD)
    by_code = {row["scheme_code"]: row for row in rows}

    assert by_code[153206]["amfi_category"] == "Debt - Gilt"
    assert by_code[122639]["amfi_category"] == "Flexi Cap"
    # The raw AMFI text is retained so a published category traces back to its source.
    assert by_code[122639]["amfi_category_label"] == "Equity Scheme - Flexi Cap Fund"


def test_equity_category_capture_lands_on_a_publishable_value():
    """What makes the newly-covered equity schemes eligible without touching the gate."""
    rows = parse_amfi_nav_payload(_CATEGORY_PAYLOAD)
    equity = next(row for row in rows if row["scheme_code"] == 122639)

    assert equity["amfi_category"] in CATEGORIES


def test_debt_category_is_captured_but_is_not_publishable():
    """Populating the column must not silently widen what the gate accepts."""
    rows = parse_amfi_nav_payload(_CATEGORY_PAYLOAD)
    debt = next(row for row in rows if row["scheme_code"] == 153206)

    assert debt["amfi_category"] == "Debt - Gilt"
    assert debt["amfi_category"] not in CATEGORIES


def test_row_without_a_preceding_header_has_no_category():
    """Absent evidence must stay absent; it must not be guessed."""
    rows = parse_amfi_nav_payload(
        "122639;INF879O01019;-;Parag Parikh Flexi Cap Fund;Direct Plan;Growth;89.7169;21-Sep-2026"
    )

    assert rows[0]["amfi_category"] is None
    assert rows[0]["amfi_category_label"] is None


def test_core_snapshot_fills_an_absent_category():
    update = {
        "scheme_code": 122639,
        "scheme_name": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
        "nav": 89.7169,
        "nav_date": "2026-09-21",
        "amfi_category": "Flexi Cap",
    }

    row = _build_core_snapshot_row(update, {"category": None})

    assert row["category"] == "Flexi Cap"


def test_core_snapshot_never_overwrites_an_existing_category():
    """The regression this guards is severe: overwriting de-indexes live pages.

    SBI Contra (119835), Quant Multi Cap (120823) and ICICI Prudential Value (120323) are live
    under "Flexi Cap" while AMFI now files them as Contra / Multi Cap / Value. Those replacement
    values are not in CATEGORIES, so writing them would flip `is_published` to false and drop
    three ranking pages out of the index.
    """
    update = {
        "scheme_code": 119835,
        "scheme_name": "SBI CONTRA FUND - Direct Plan - Growth",
        "nav": 1.0,
        "nav_date": "2026-09-21",
        "amfi_category": "Contra",
    }

    row = _build_core_snapshot_row(update, {"category": "Flexi Cap"})

    assert "category" not in row


def test_core_snapshot_does_not_write_a_null_category():
    update = {
        "scheme_code": 1,
        "scheme_name": "Unknown Fund - Direct Plan - Growth",
        "nav": 10.0,
        "nav_date": "2026-09-21",
        "amfi_category": None,
    }

    row = _build_core_snapshot_row(update, {"category": None})

    assert "category" not in row


def test_legacy_mirror_receives_only_its_declared_columns():
    """Parser-internal keys must not reach the mirror, whose schema does not define them.

    PostgREST rejects an unknown column for the whole batch, so a passthrough here would stop
    the legacy mirror from updating at all while the core snapshot kept succeeding.
    """
    update = {
        "scheme_code": 122639,
        "scheme_name": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
        "nav": 89.7169,
        "nav_date": "2026-09-21",
        "isin": "INF879O01019",
        "amfi_category": "Flexi Cap",
        "amfi_category_label": "Equity Scheme - Flexi Cap Fund",
        "updated_at": "2026-09-21T00:00:00+00:00",
    }
    mirror = {key: update[key] for key in _MUTUAL_FUNDS_MIRROR_COLUMNS if key in update}

    assert "amfi_category" not in mirror
    assert "amfi_category_label" not in mirror
    assert "updated_at" not in mirror
    assert mirror["scheme_code"] == 122639


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


def test_nav_only_mode_persists_core_snapshot_when_legacy_mirror_is_missing(monkeypatch):
    monkeypatch.setattr("backend.scripts.sync_mf.SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr("backend.scripts.sync_mf.SUPABASE_KEY", "test-key")
    monkeypatch.setattr(
        "backend.scripts.sync_mf.fetch_amfi_nav",
        lambda: [{"scheme_code": 1, "scheme_name": "Example Fund - Direct Growth", "nav": 10.0, "nav_date": "2026-09-03"}],
    )

    writes: list[str] = []

    class _Query:
        data: list[dict] = []

        def __init__(self, table_name: str):
            self.table_name = table_name
            self.is_upsert = False

        def select(self, _fields):
            return self

        def in_(self, _field, _values):
            return self

        def upsert(self, _rows, **_kwargs):
            self.is_upsert = True
            writes.append(self.table_name)
            return self

        def execute(self):
            if self.table_name == "mutual_funds" and self.is_upsert:
                raise RuntimeError("PGRST205: missing mutual_funds")
            return self

    class _Client:
        def table(self, name):
            return _Query(name)

    monkeypatch.setattr("backend.scripts.sync_mf.create_client", lambda *_args: _Client())

    main(["--nav-only"])

    assert writes == ["mutual_fund_core_snapshot", "mutual_funds"]
