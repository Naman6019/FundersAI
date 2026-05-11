from __future__ import annotations

from typing import Any


def build_stock_price_upsert_payload(symbol: str, row: dict[str, Any]) -> dict[str, Any]:
    clean = (symbol or "").strip().upper()
    close = row.get("close")
    return {
        "symbol": clean,
        "date": row.get("date"),
        "open": row.get("open"),
        "high": row.get("high"),
        "low": row.get("low"),
        "close": close,
        "adj_close": row.get("adj_close", close),
        "volume": row.get("volume"),
        "source": row.get("source") or "nse_bhavcopy",
    }
