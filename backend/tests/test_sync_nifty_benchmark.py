from datetime import date

from app.jobs.sync_nifty_benchmark import _business_day_lag, _to_price


def test_business_day_lag_ignores_weekend():
    assert _business_day_lag(date(2026, 7, 31), date(2026, 8, 3)) == 1


def test_nifty_row_conversion_rejects_invalid_close():
    assert _to_price({"date": "2026-08-03", "close": None}) is None
    price = _to_price({"date": "2026-08-03", "close": 25000, "source": "yfinance"})
    assert price is not None
    assert price.symbol == "NIFTY"
    assert price.close is not None
