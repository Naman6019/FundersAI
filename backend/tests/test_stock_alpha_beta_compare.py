import pytest
from datetime import datetime, timedelta, timezone
from app.services import quant_service


def test_calculate_stock_alpha_beta(monkeypatch):
    # Create mock price history of 100 days
    base_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    
    # Stock prices increasing by ~1% each day
    mock_stock_prices = []
    current_stock = 100.0
    # NIFTY prices increasing by ~0.5% each day
    mock_nifty_prices = []
    current_nifty = 10000.0
    
    for i in range(100):
        date_str = (base_date + timedelta(days=i)).isoformat()
        
        # Stock: daily growth of 1%
        mock_stock_prices.append({
            "date": date_str,
            "close": current_stock,
            "source": "mock"
        })
        current_stock *= 1.01
        
        # NIFTY: daily growth of 0.5%
        mock_nifty_prices.append({
            "date": date_str,
            "close": current_nifty,
            "source": "mock"
        })
        current_nifty *= 1.005

    # Mock get_stock_price_history in quant_service
    def mock_get_price_history(symbol, days=1100):
        if symbol == "TCS":
            return mock_stock_prices
        elif symbol == "NIFTY":
            return mock_nifty_prices
        return []

    monkeypatch.setattr(quant_service, "get_stock_price_history", mock_get_price_history)

    # Run the helper function
    beta, alpha_vs_nifty = quant_service._calculate_stock_alpha_beta("TCS")

    # Assert that results are not None and are calculated correctly
    assert beta is not None
    assert alpha_vs_nifty is not None
    
    # Beta should be positive since they are positively correlated
    assert beta > 0
    # Alpha should be positive because stock growth (1% daily) exceeds nifty growth (0.5% daily)
    assert alpha_vs_nifty > 0


def test_comparison_item_includes_alpha_beta(monkeypatch):
    # Mock stock snapshot, metadata, price history, financials, ratios, and shareholding
    monkeypatch.setattr(quant_service, "normalize_symbol", lambda symbol: symbol.upper())
    monkeypatch.setattr(quant_service, "get_stock_snapshot_with_freshness", lambda symbol: {
        "row": {
            "symbol": symbol,
            "close_price": 200.0,
            "previous_close": 198.0,
            "market_cap": 50000,
            "pe_ratio": 15.0,
            "industry": "IT"
        },
        "stale": False,
        "warning": None
    })
    monkeypatch.setattr(quant_service, "get_stock_metadata", lambda symbol: {"symbol": symbol, "company_name": symbol})
    monkeypatch.setattr(quant_service, "get_stock_financials", lambda symbol: {"quarterly": [], "annual": []})
    monkeypatch.setattr(quant_service, "_latest_ratios", lambda symbol: {"market_cap": 50000, "pe": 15.0})
    monkeypatch.setattr(quant_service, "_latest_shareholding", lambda symbol: {})
    
    # Mock stock price history return for both 365 (1y history) and 1100 days (helper function)
    base_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    mock_prices = [{"date": (base_date + timedelta(days=i)).isoformat(), "close": 100.0 + i} for i in range(100)]
    mock_nifty = [{"date": (base_date + timedelta(days=i)).isoformat(), "close": 10000.0 + (i * 10)} for i in range(100)]
    
    def mock_get_price_history(symbol, days=365):
        if symbol == "TCS":
            return mock_prices
        if symbol == "NIFTY":
            return mock_nifty
        return []
        
    monkeypatch.setattr(quant_service, "get_stock_price_history", mock_get_price_history)

    # Call _comparison_item
    item = quant_service._comparison_item("TCS")

    # Assert beta and alpha_vs_nifty are present and correctly retrieved
    assert "beta" in item
    assert "alpha_vs_nifty" in item
    assert item["beta"] is not None
    assert item["alpha_vs_nifty"] is not None
