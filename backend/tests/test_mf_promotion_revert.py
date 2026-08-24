from pathlib import Path
from types import SimpleNamespace

import pytest

from app.mf_ingestion.jobs import revert_mf_promotion
from app.mf_ingestion.jobs.revert_mf_promotion import (
    _parse_run_id,
    apply_revert,
    build_revert_plan,
)

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "20260824_add_mf_promotion_revert.sql"
)

RUN_ID = "ad4ac081-eb76-4147-9004-e3da10133d07"
CANDIDATE_ID = "02bc8db4-6a67-4728-a04d-82297e40938c"


def _core_run(**overrides) -> dict:
    run = {
        "id": RUN_ID,
        "candidate_id": CANDIDATE_ID,
        "source_document_id": "6f2a1f3c-2f1e-4c1a-9f3d-1d2b3c4d5e6f",
        "amc_code": "TATA",
        "scopes": ["ter_aum", "benchmark"],
        "status": "applied",
        "requested_by": "operator",
        "reverted_at": None,
        "completed_at": "2026-08-24T10:00:00+00:00",
        "before_snapshot": {
            "scheme_code": "120503",
            "expense_ratio": 0.62,
            "aum": 4821.5,
            "benchmark": "NIFTY 500 TRI",
        },
    }
    run.update(overrides)
    return run


def _portfolio_run(**overrides) -> dict:
    run = {
        "id": RUN_ID,
        "candidate_id": None,
        "source_document_id": "6f2a1f3c-2f1e-4c1a-9f3d-1d2b3c4d5e6f",
        "amc_code": "TATA",
        "scopes": ["holdings", "sectors"],
        "status": "applied",
        "requested_by": "operator",
        "reverted_at": None,
        "completed_at": "2026-08-24T10:00:00+00:00",
        "before_snapshot": {
            "revertable": True,
            "report_month": "2026-07-01",
            "holdings": [{"scheme_code": 120503, "security_name": "HDFC Bank"}],
            "holdings_scheme_codes": [120503, 120504],
            "sectors": [{"scheme_code": "120503", "sector": "Financials"}],
            "sectors_scheme_codes": ["120503"],
        },
    }
    run.update(overrides)
    return run


def test_core_run_with_captured_snapshot_is_revertable() -> None:
    plan = build_revert_plan(_core_run())

    assert plan["status"] == "revertable"
    assert plan["revert_kind"] == "core"
    assert plan["issues"] == []
    assert plan["restores"]["scheme_code"] == "120503"
    assert plan["restores"]["fields"] == ["benchmark", "ter_aum"]


def test_portfolio_run_reports_rows_and_scheme_codes_it_would_restore() -> None:
    plan = build_revert_plan(_portfolio_run())

    assert plan["status"] == "revertable"
    assert plan["revert_kind"] == "portfolio"
    assert plan["restores"]["report_month"] == "2026-07-01"
    assert plan["restores"]["holdings_rows"] == 1
    # The promotion touched two schemes but only one had prior rows; a revert must
    # still clear the added scheme, so the code set is tracked separately.
    assert plan["restores"]["holdings_scheme_codes"] == 2
    assert plan["restores"]["sectors_rows"] == 1


def test_portfolio_run_promoted_before_capture_existed_is_refused() -> None:
    plan = build_revert_plan(_portfolio_run(before_snapshot={}))

    assert plan["status"] == "blocked"
    assert "promotion_run_before_snapshot_unavailable" in plan["issues"]


def test_portfolio_run_without_revertable_marker_is_refused() -> None:
    stale = {"report_month": "2026-07-01", "holdings": [], "sectors": []}
    plan = build_revert_plan(_portfolio_run(before_snapshot=stale))

    assert plan["status"] == "blocked"
    assert "promotion_run_before_snapshot_unavailable" in plan["issues"]


def test_core_run_without_scheme_code_is_refused() -> None:
    plan = build_revert_plan(_core_run(before_snapshot={"expense_ratio": 0.62}))

    assert plan["status"] == "blocked"
    assert "promotion_run_before_snapshot_unavailable" in plan["issues"]


def test_already_reverted_run_is_refused() -> None:
    plan = build_revert_plan(_core_run(reverted_at="2026-08-24T11:00:00+00:00"))

    assert plan["status"] == "blocked"
    assert "promotion_run_already_reverted" in plan["issues"]


def test_dry_run_only_status_is_refused() -> None:
    plan = build_revert_plan(_core_run(status="dry_run"))

    assert plan["status"] == "blocked"
    assert "promotion_run_not_applied" in plan["issues"]


@pytest.mark.parametrize("value", ["", "not-a-uuid", "123", None])
def test_run_id_must_be_a_uuid(value) -> None:
    with pytest.raises(ValueError):
        _parse_run_id(value)


def test_apply_revert_calls_the_rpc_with_run_and_actor(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    class _Rpc:
        def execute(self):
            return SimpleNamespace(data={"status": "reverted", "revert_kind": "core"})

    class _Supabase:
        def rpc(self, function_name: str, params: dict):
            calls.append((function_name, params))
            return _Rpc()

    monkeypatch.setattr(revert_mf_promotion, "supabase", _Supabase())

    result = apply_revert(RUN_ID, requested_by="operator")

    assert calls == [
        ("revert_mf_promotion_run", {"p_run_id": RUN_ID, "p_requested_by": "operator"})
    ]
    assert result["status"] == "reverted"


def test_apply_revert_unwraps_single_row_rpc_responses(monkeypatch) -> None:
    class _Rpc:
        def execute(self):
            return SimpleNamespace(data=[{"status": "reverted"}])

    class _Supabase:
        def rpc(self, _function_name: str, _params: dict):
            return _Rpc()

    monkeypatch.setattr(revert_mf_promotion, "supabase", _Supabase())

    assert apply_revert(RUN_ID, requested_by="operator")["status"] == "reverted"


def test_portfolio_promotion_captures_runtime_rows_before_every_destructive_delete() -> None:
    """The regression this migration exists to prevent.

    Every delete against a runtime portfolio table must be preceded by a snapshot of
    the rows it destroys, otherwise a bad promotion is unrecoverable.
    """
    sql = MIGRATION.read_text(encoding="utf-8")
    # Scope to the promotion function -- the revert function also deletes runtime
    # rows, but it does so to replace them with the captured originals.
    promotion = sql.split("create or replace function public.promote_mf_holdings_document_v2", 1)[1]
    promotion = promotion.split("create or replace function public.revert_mf_promotion_run", 1)[0]

    chunks = promotion.split("delete from public.mutual_fund_")
    assert len(chunks) == 4, "expected exactly the three portfolio deletes"
    for preceding in chunks[:-1]:
        assert "into holdings_before" in preceding or "into sectors_before" in preceding


def test_migration_records_before_snapshot_and_restricts_revert_to_service_role() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "before_snapshot," in sql
    assert "'revertable', true," in sql
    assert "create or replace function public.revert_mf_promotion_run" in sql
    assert (
        "revoke all on function public.revert_mf_promotion_run(uuid, text)\n"
        "  from public, anon, authenticated;" in sql
    )
    assert "grant execute on function public.revert_mf_promotion_run(uuid, text)\n  to service_role;" in sql
    assert "'reverted'" in sql


def test_revert_only_sets_promotion_status_values_the_constraint_allows() -> None:
    """`mf_factsheet_candidates.promotion_status` is check-constrained; releasing a
    reverted candidate must land on an allowed value, not an invented one."""
    staging = (
        MIGRATION.parent / "20260727_add_mf_extraction_staging_and_promotion.sql"
    ).read_text(encoding="utf-8")
    allowed_clause = staging.split("check (promotion_status in (", 1)[1].split("))", 1)[0]
    allowed = {value.strip().strip("'") for value in allowed_clause.split(",")}

    revert = MIGRATION.read_text(encoding="utf-8").split(
        "create or replace function public.revert_mf_promotion_run", 1
    )[1]
    assigned = revert.split("promotion_status = case", 1)[1].split("end,", 1)[0]
    used = {
        segment.split("'", 1)[0]
        for segment in assigned.split("then '")[1:]
    } | {
        segment.split("'", 1)[0]
        for segment in assigned.split("else '")[1:]
    }

    assert used, "expected the revert to set promotion_status"
    assert used <= allowed, f"{used - allowed} not permitted by the check constraint"


def test_migration_does_not_promote_or_revert_on_apply() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "applying this migration does not promote or revert any data" in sql
    # No bare DML outside the function bodies.
    assert "\nupdate public.mutual_fund_core_snapshot\n" not in sql
