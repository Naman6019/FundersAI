from datetime import date, timedelta
import json
from pathlib import Path

import pytest
from app.services.mf_catalog_service import assess_history, catalog_row, identity_reasons
from app.jobs.backfill_catalog_nav_history import run_batch

TODAY = date(2026, 9, 5)


def history(days=400):
    return [{"nav_date": (TODAY - timedelta(days=i)).isoformat(), "nav": 100 * 1.1 ** (-i / 365)}
            for i in range(days + 1) if (TODAY - timedelta(days=i)).weekday() < 5]


def snapshot():
    return dict(scheme_code="120503", scheme_name="HDFC Flexi Cap Fund Direct Growth",
                amc_name="HDFC Mutual Fund", category="Equity Scheme - Flexi Cap Fund")


def test_full_window_golden_and_missing_longer_windows():
    result = assess_history(history(), today=TODAY)
    assert result["gate_reasons"] == []
    assert result["cagr_1y"] == pytest.approx(10)
    assert result["cagr_3y"] is None
    assert result["cagr_5y"] is None


@pytest.mark.parametrize("days,ready3,ready5", [(900, False, False), (1200, True, False), (1900, True, True)])
def test_long_windows(days, ready3, ready5):
    result = assess_history(history(days), today=TODAY)
    assert (result["cagr_3y"] is not None) == ready3
    assert (result["cagr_5y"] is not None) == ready5


def test_fresh_fetch_cannot_rescue_old_nav():
    rows = history()[20:]
    assert "nav_stale" in assess_history(rows, today=TODAY)["gate_reasons"]


def test_depth_count_and_internal_gaps():
    assert "history_1y_incomplete" in assess_history(history(300), today=TODAY)["gate_reasons"]
    rows = history()
    assert "history_1y_incomplete" in assess_history(rows[::2], today=TODAY)["gate_reasons"]
    del rows[60:75]
    assert "history_1y_incomplete" in assess_history(rows, today=TODAY)["gate_reasons"]


@pytest.mark.parametrize("nav", [float('nan'), float('inf'), 0, -1, 'garbage'])
def test_invalid_nav_fails_closed(nav):
    rows = history() + [{"nav_date": "2026-09-04", "nav": nav}]
    result = assess_history(rows, today=TODAY)
    assert "invalid_nav" in result["gate_reasons"]
    assert result["cagr_1y"] is None


def test_duplicates_and_future_rows():
    rows = history()
    assert assess_history(rows + rows, today=TODAY) == assess_history(rows, today=TODAY)
    assert "conflicting_nav" in assess_history(rows + [{**rows[0], "nav": 7}], today=TODAY)["gate_reasons"]
    assert "future_nav" in assess_history(rows + [{"nav_date": "2027-01-01", "nav": 10}], today=TODAY)["gate_reasons"]


@pytest.mark.parametrize("extra", [{"plan_type": "Regular"}, {"option_type": "IDCW"},
                                   {"scheme_name": "Direct Segregated Growth"}, {"amc_name": "Unknown"}])
def test_conflicting_share_classes_rejected(extra):
    assert identity_reasons({**snapshot(), **extra})


def test_frozen_legacy_url_does_not_override_gate():
    legacy = {"amc_slug": "hdfc", "fund_slug": "hdfc-flexi-cap-fund"}
    row = catalog_row(snapshot(), [], reservation=legacy, today=TODAY)
    assert not row["is_published"]
    assert row["fund_slug"] == legacy["fund_slug"]
    renamed = {**snapshot(), "scheme_name": "Renamed Direct Growth"}
    new = catalog_row(renamed, history(), existing=row, today=TODAY)
    assert new["is_published"]
    assert new["fund_slug"] == row["fund_slug"]


def test_unknown_category_is_auditable():
    row = catalog_row({**snapshot(), "category": "Other"}, history(), today=TODAY)
    assert row["gate_reasons"] == ["category_unresolved"]


def test_readiness_is_read_only_and_refresh_is_re_read(monkeypatch):
    import app.jobs.backfill_catalog_nav_history as job
    reads = []
    monkeypatch.setattr(job, 'stored_history', lambda client, code: reads.append(code) or [])
    refreshed = []
    def refresh(*args, **kwargs):
        refreshed.append(args)
        return {"cache_status": "refreshed", "data": history()}
    report = run_batch(None, [snapshot()], refresh=refresh, today=TODAY)
    assert not refreshed and report["ready"] == 0
    report = run_batch(None, [snapshot()], apply=True, refresh=refresh, delay=0, today=TODAY)
    assert len(refreshed) == 1 and len(reads) == 3
    assert report["ready"] == 0  # Provider data never substitutes for persisted data.


def test_database_error_is_not_absence(monkeypatch):
    import app.jobs.backfill_catalog_nav_history as job
    def fail(*args):
        raise RuntimeError('offline')
    monkeypatch.setattr(job, 'stored_history', fail)
    report = run_batch(None, [snapshot()], today=TODAY)
    assert report['rows'][0]['error'] == 'RuntimeError'
    assert report['ready'] == 0


def test_refresh_ready_history_is_not_fetched_again(monkeypatch):
    import app.jobs.backfill_catalog_nav_history as job
    monkeypatch.setattr(job, 'stored_history', lambda *args: history())
    def refresh(*args, **kwargs):
        pytest.fail('Already-ready history must not consume provider requests')
    result = run_batch(None, [snapshot()], apply=True, refresh=refresh, today=TODAY)
    assert result['ready'] == 1 and result['complete']


def test_deadline_stops_before_next_scheme(monkeypatch):
    import app.jobs.backfill_catalog_nav_history as job
    ticks = iter([0, 0, 2, 2])
    monkeypatch.setattr(job.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(job, 'stored_history', lambda *args: history())
    result = run_batch(None, [snapshot(), {**snapshot(), 'scheme_code': '120504'}], max_seconds=1, today=TODAY)
    assert result['scanned'] == 1 and not result['complete']
    assert result['next_after'] == '120503'


def test_legacy_reservations_match_current_registry():
    import re
    root = Path(__file__).resolve().parents[2]
    reservations = json.loads((root / 'backend/config/mf_catalog_legacy_urls.json').read_text())
    source = (root / 'frontend/lib/fund-registry.ts').read_text(encoding='utf-8')
    blocks = re.findall(r'\{\s*schemeCode: \d+[^}]*\}', source)
    assert len(reservations) == len(blocks)
    for row, block in zip(reservations, blocks):
        assert f"schemeCode: {row['scheme_code']}" in block
        assert f"amcSlug: '{row['amc_slug']}'" in block
        assert f"fundSlug: '{row['fund_slug']}'" in block


def test_migration_reserves_urls_and_enforces_server_only_access():
    root = Path(__file__).resolve().parents[2]
    sql = (root / 'backend/migrations/20260905_add_mf_page_catalog.sql').read_text()
    reservations = json.loads((root / 'backend/config/mf_catalog_legacy_urls.json').read_text())
    for row in reservations:
        assert f"('{row['scheme_code']}', '{row['amc_slug']}', '{row['fund_slug']}'" in sql
    assert 'ENABLE ROW LEVEL SECURITY' in sql
    assert 'FROM PUBLIC, anon, authenticated' in sql
    assert 'TO service_role' in sql
    assert 'IS TRUE)' in sql  # SQL NULL must not bypass the publication CHECK.
    assert 'OLD.amc_slug IS DISTINCT FROM NEW.amc_slug' in sql
    assert 'OLD.fund_slug IS DISTINCT FROM NEW.fund_slug' in sql
