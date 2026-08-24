from pathlib import Path


def test_edelweiss_snapshot_match_migration_extends_existing_guard_without_data_writes():
    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "20260824_add_edelweiss_amc_snapshot_match.sql"
    ).read_text(encoding="utf-8").lower()

    assert "when 'edelweiss' then lower(coalesce(p_amc_name, '')) like '%edelweiss%'" in sql
    assert "create or replace function public.mf_snapshot_matches_amc" in sql
    assert "insert into" not in sql
    assert "delete from" not in sql
