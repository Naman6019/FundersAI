from datetime import datetime, timezone

from app.services.mf_nav_freshness import assess_nav_freshness


def test_friday_nav_is_fresh_on_monday_before_new_nav_is_expected():
    result = assess_nav_freshness("2026-07-24", now=datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc))

    assert result == {
        "status": "fresh",
        "nav_date": "2026-07-24",
        "expected_nav_date": "2026-07-24",
        "missed_business_days": 0,
    }


def test_one_missed_business_day_is_lagging():
    result = assess_nav_freshness("2026-07-24", now=datetime(2026, 7, 28, 9, 0, tzinfo=timezone.utc))

    assert result["status"] == "lagging"
    assert result["expected_nav_date"] == "2026-07-27"
    assert result["missed_business_days"] == 1


def test_two_missed_business_days_are_stale():
    result = assess_nav_freshness("2026-07-24", now=datetime(2026, 7, 29, 9, 0, tzinfo=timezone.utc))

    assert result["status"] == "stale"
    assert result["expected_nav_date"] == "2026-07-28"
    assert result["missed_business_days"] == 2


def test_configured_market_holiday_extends_last_expected_nav_date(monkeypatch):
    monkeypatch.setenv("MF_NAV_MARKET_HOLIDAYS", "2026-07-27")

    result = assess_nav_freshness("2026-07-24", now=datetime(2026, 7, 28, 9, 0, tzinfo=timezone.utc))

    assert result["status"] == "fresh"
    assert result["expected_nav_date"] == "2026-07-24"
