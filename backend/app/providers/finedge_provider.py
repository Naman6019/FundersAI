from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime
from typing import Any

import httpx

from app.models.stock_models import StockProfile
from app.providers.base import FundamentalsProvider, normalize_symbol
from app.services.provider_usage import log_provider_usage

logger = logging.getLogger(__name__)


class FinEdgeProvider(FundamentalsProvider):
    name = "finedge"

    def __init__(self) -> None:
        self.api_key = os.environ.get("FINEDGE_API_KEY")
        self.base_url = os.environ.get("FINEDGE_BASE_URL", "https://data.finedgeapi.com").rstrip("/")
        self.timeout_seconds = float(os.environ.get("FINEDGE_TIMEOUT_SECONDS", "20"))

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        query = dict(params or {})
        query["token"] = self.api_key
        response = httpx.get(f"{self.base_url}{path}", params=query, timeout=self.timeout_seconds)
        log_provider_usage(
            provider=self.name,
            endpoint=path.strip("/"),
            symbol=str(query.get("symbol") or "").upper() or None,
            cache_hit=False,
            status_code=response.status_code,
            success=response.status_code < 400,
            error_message=None if response.status_code < 400 else f"http_{response.status_code}",
            request_cost=1,
        )
        return response

    def get_stock_universe(self) -> list[StockProfile]:
        try:
            res = self._get("/api/v1/stock-symbols")
            if res.status_code != 200:
                logger.warning("FinEdge get_stock_universe failed with %s", res.status_code)
                return []

            profiles = []
            for item in _as_list(res.json()):
                symbol = item.get("nse_code") or item.get("symbol") or item.get("bse_code")
                if not symbol:
                    continue
                profiles.append(
                    StockProfile(
                        symbol=str(symbol).upper(),
                        exchange="NSE" if item.get("nse_code") else "BSE",
                        company_name=_pick(item, "name", "company_name", "companyName"),
                        isin=_pick(item, "isin", "ISIN"),
                        sector=_pick(item, "sector", "macro_sector"),
                        industry=_pick(item, "industry", "sub_industry"),
                        listing_status="Active",
                        is_active=True,
                        source=self.name,
                    )
                )
            return profiles
        except Exception as exc:
            logger.error("FinEdge get_stock_universe error: %s", exc)
            return []

    def get_company_profile(self, symbol: str) -> dict[str, Any] | None:
        clean = normalize_symbol(symbol)
        try:
            res = self._get(f"/api/v1/company-profile/{clean}", {"symbol": clean})
            if res.status_code != 200:
                logger.warning("FinEdge get_company_profile failed for %s with %s", clean, res.status_code)
                return None
            data = res.json()
            if not isinstance(data, dict):
                return None
            return {
                "symbol": normalize_symbol(_pick(data, "nse_code", "symbol", "bse_code") or clean),
                "exchange": "NSE" if _pick(data, "nse_code") else "BSE",
                "company_name": _pick(data, "name", "company_name"),
                "isin": _pick(data, "isin", "ISIN"),
                "sector": _pick(data, "sector", "macro_sector"),
                "industry": _pick(data, "industry", "sub_industry"),
                "is_active": True,
                "source": self.name,
            }
        except Exception as exc:
            logger.error("FinEdge get_company_profile error for %s: %s", clean, exc)
            return None

    def get_eod_prices(self, symbol: str) -> list[dict]:
        clean = normalize_symbol(symbol)
        try:
            current_year = datetime.now().year
            res = self._get(
                f"/api/v1/daily-quotes/{clean}",
                params={"from": current_year - 1, "to": current_year, "symbol": clean},
            )
            if res.status_code != 200:
                logger.warning("FinEdge get_eod_prices failed for %s with %s", clean, res.status_code)
                return []

            data = res.json()
            rows = data.get("price", []) if isinstance(data, dict) else []
            prices = []
            for row in rows:
                quote_date = row.get("quote_date")
                if not quote_date:
                    continue
                try:
                    parsed_date = datetime.fromisoformat(str(quote_date)[:10]).date()
                except ValueError:
                    continue

                close = _safe_float(row.get("close_price"))
                prices.append({
                    "symbol": clean,
                    "date": parsed_date,
                    "open": _safe_float(row.get("open_price")),
                    "high": _safe_float(row.get("high_price")),
                    "low": _safe_float(row.get("low_price")),
                    "close": close,
                    "adj_close": close,
                    "volume": _safe_int(row.get("volume")),
                    "value_traded": None,
                    "delivery_qty": None,
                    "delivery_percent": None,
                    "source": self.name,
                })
            return sorted(prices, key=lambda item: item["date"])
        except Exception as exc:
            logger.error("FinEdge get_eod_prices error for %s: %s", clean, exc)
            return []

    def get_corporate_actions(self, symbol: str) -> list[dict]:
        clean = normalize_symbol(symbol)
        events: list[dict[str, Any]] = []
        try:
            res = self._get("/api/v1/corporate-actions/all", params={"symbol": clean})
            if res.status_code == 200:
                for item in _as_list(res.json()):
                    event_date = _parse_finedge_date(item.get("ex_date") or item.get("date"))
                    if not event_date:
                        continue
                    event_type = str(item.get("action") or item.get("corp_action") or "corporate_action").lower()
                    events.append({
                        "symbol": clean,
                        "event_date": event_date,
                        "event_type": event_type,
                        "title": item.get("subject") or item.get("category") or event_type.title(),
                        "description": item.get("description") or item.get("sub_category") or item.get("subject"),
                        "source_url": item.get("pdf_file_link"),
                        "source": self.name,
                    })
            else:
                logger.warning("FinEdge get_corporate_actions failed for %s with %s", clean, res.status_code)
            events.extend(self._get_dividends(clean))
            return events
        except Exception as exc:
            logger.error("FinEdge get_corporate_actions error for %s: %s", clean, exc)
            return events

    def _get_dividends(self, symbol: str) -> list[dict[str, Any]]:
        try:
            res = self._get(f"/api/v1/dividend/{symbol}", {"symbol": symbol})
            if res.status_code != 200:
                return []
            data = res.json()
            rows = data.get("dividend", []) if isinstance(data, dict) else []
            events = []
            for item in rows:
                event_date = _parse_finedge_date(item.get("date"))
                if not event_date:
                    continue
                events.append({
                    "symbol": symbol,
                    "event_date": event_date,
                    "event_type": "dividend",
                    "title": item.get("subject") or item.get("dividend_type") or "Dividend",
                    "description": item.get("dividend_type") or item.get("subject"),
                    "source_url": None,
                    "source": self.name,
                })
            return events
        except Exception as exc:
            logger.warning("FinEdge dividend sync failed for %s: %s", symbol, exc)
            return []

    def get_quarterly_results(self, symbol: str) -> list[dict]:
        return self._get_financial_statement(symbol, statement_code="pl", period="quarterly")

    def get_annual_results(self, symbol: str) -> list[dict]:
        rows = self._get_financial_statement(symbol, statement_code="pl", period="annual")
        if rows:
            return rows
        return self._get_basic_financials(symbol)

    def get_balance_sheet(self, symbol: str) -> list[dict]:
        return self._get_financial_statement(symbol, statement_code="bs", period="annual")

    def get_cash_flow(self, symbol: str) -> list[dict]:
        return self._get_financial_statement(symbol, statement_code="cf", period="annual")

    def _get_financial_statement(self, symbol: str, statement_code: str, period: str) -> list[dict]:
        clean = normalize_symbol(symbol)
        try:
            res = self._get(
                f"/api/v1/financials/{clean}",
                params={
                    "symbol": clean,
                    "statement_type": os.environ.get("FINEDGE_STATEMENT_TYPE", "s"),
                    "statement_code": statement_code,
                    "period": period,
                },
            )
            if res.status_code != 200:
                logger.warning("FinEdge financials failed for %s/%s/%s with %s", clean, statement_code, period, res.status_code)
                return []
            data = res.json()
            rows = data.get("financials", []) if isinstance(data, dict) else []
            mapped = [_statement_row(clean, item, period, self.name) for item in rows]
            return [row for row in mapped if row]
        except Exception as exc:
            logger.error("FinEdge financials error for %s/%s/%s: %s", clean, statement_code, period, exc)
            return []

    def _get_basic_financials(self, symbol: str) -> list[dict]:
        clean = normalize_symbol(symbol)
        try:
            res = self._get(
                f"/api/v1/basic-financials/{clean}",
                params={"symbol": clean, "statement_type": os.environ.get("FINEDGE_STATEMENT_TYPE", "s"), "statement_code": "pl"},
            )
            if res.status_code != 200:
                logger.warning("FinEdge get_annual_results failed for %s with %s", clean, res.status_code)
                return []

            data = res.json()
            rows = data.get("basic_financials", []) if isinstance(data, dict) else []
            mapped = [_statement_row(clean, item, "annual", self.name) for item in rows]
            return [row for row in mapped if row]
        except Exception as exc:
            logger.error("FinEdge get_annual_results error for %s: %s", clean, exc)
            return []

    def get_shareholding(self, symbol: str) -> list[dict]:
        if os.environ.get("ENABLE_SHAREHOLDING_SYNC", "0").strip().lower() not in {"1", "true", "yes", "on"}:
            return []
        clean = normalize_symbol(symbol)
        try:
            res = self._get(f"/api/v1/shareholdings/pattern/{clean}", {"symbol": clean, "period": "quarterly"})
            if res.status_code != 200:
                logger.warning("FinEdge get_shareholding failed for %s with %s", clean, res.status_code)
                return []
            return _shareholding_rows(clean, res.json(), self.name)[:4]
        except Exception as exc:
            logger.error("FinEdge get_shareholding error for %s: %s", clean, exc)
            return []

    def get_ratios_snapshot(self, symbol: str) -> dict[str, Any] | None:
        clean = normalize_symbol(symbol)
        sections: list[Any] = []
        for ratio_type in _env_list("FINEDGE_RATIO_TYPES", "pr,le,li"):
            try:
                res = self._get(
                    f"/api/v1/ratios/{clean}",
                    {"symbol": clean, "statement_type": os.environ.get("FINEDGE_STATEMENT_TYPE", "s"), "ratio_type": ratio_type},
                )
                if res.status_code == 200:
                    sections.extend(_as_list(res.json().get("ratios", [])))
            except Exception as exc:
                logger.warning("FinEdge ratios failed for %s/%s: %s", clean, ratio_type, exc)

        price_ratios = self._latest_price_ratios(clean)
        ratios = {
            "symbol": clean,
            "snapshot_date": date.today(),
            "market_cap": None,
            "enterprise_value": None,
            "pe": _pick_number(price_ratios, "pe", "p/e") or _latest_from_sections(sections, "pe", "p/e", "price to earnings"),
            "pb": _pick_number(price_ratios, "pb", "ptb", "p/b") or _latest_from_sections(sections, "pb", "p/b", "price to book"),
            "ps": _pick_number(price_ratios, "ps", "p/s") or _latest_from_sections(sections, "ps", "p/s", "price to sales"),
            "ev_ebitda": _latest_from_sections(sections, "ev ebitda", "ev/ebitda"),
            "roe": _latest_from_sections(sections, "returnOnEquity", "return on equity", "roe"),
            "roce": _latest_from_sections(sections, "returnOnCapital", "return on capital", "roce"),
            "roa": _latest_from_sections(sections, "returnOnAsset", "return on asset", "roa"),
            "debt_to_equity": _latest_from_sections(sections, "debtToEquity", "debt to equity"),
            "current_ratio": _latest_from_sections(sections, "currentRatio", "current ratio"),
            "interest_coverage": _latest_from_sections(sections, "interestCoverage", "interest coverage"),
            "dividend_yield": _latest_from_sections(sections, "dividendYield", "dividend yield"),
            "sales_growth_1y": None,
            "sales_growth_3y": None,
            "profit_growth_1y": None,
            "profit_growth_3y": None,
            "eps_growth_1y": None,
            "eps_growth_3y": None,
            "source": self.name,
        }
        return ratios if any(value is not None for key, value in ratios.items() if key not in {"symbol", "snapshot_date", "source"}) else None

    def _latest_price_ratios(self, symbol: str) -> dict[str, Any]:
        try:
            res = self._get(
                f"/api/v1/annual-price-ratios/{symbol}",
                {"symbol": symbol, "statement_type": os.environ.get("FINEDGE_STATEMENT_TYPE", "s")},
            )
            if res.status_code != 200:
                return {}
            rows = res.json().get("price_ratios", [])
            return _latest_row_by_period(_as_list(rows))
        except Exception as exc:
            logger.warning("FinEdge price ratios failed for %s: %s", symbol, exc)
            return {}


def _statement_row(symbol: str, row: dict[str, Any], period: str, source: str) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    period_end = _period_end(row, period)
    if not period_end:
        return None
    return {
        "symbol": symbol,
        "period_type": "quarterly" if period == "quarterly" else "annual",
        "period_end_date": period_end,
        "fiscal_year": _safe_int(row.get("year")) or period_end.year,
        "fiscal_quarter": {6: 1, 9: 2, 12: 3, 3: 4}.get(period_end.month) if period == "quarterly" else None,
        "revenue": _pick_number(row, "revenueFromOperations", "operatingRevenue", "grossIncome", "income", "revenue"),
        "operating_profit": _pick_number(row, "operatingProfit"),
        "ebitda": _pick_number(row, "ebitda"),
        "ebit": _pick_number(row, "ebit"),
        "profit_before_tax": _pick_number(row, "profitBeforeTax", "pbt"),
        "net_profit": _pick_number(row, "profitLossForPeriod", "profitLossForEPS", "netProfit", "pat"),
        "eps": _pick_number(row, "EPS", "eps"),
        "total_assets": _pick_number(row, "totalAssets", "assets"),
        "total_liabilities": _pick_number(row, "totalLiabilities", "liabilities"),
        "total_equity": _pick_number(row, "totalEquity", "netWorth", "shareholdersFunds"),
        "total_debt": _pick_number(row, "borrowings", "totalDebt", "debt"),
        "cash_and_equivalents": _pick_number(row, "cashAndCashEquivalents", "cashAndBank", "cash"),
        "cash_from_operations": _pick_number(row, "cashFromOperatingActivity", "operatingCashFlow"),
        "cash_from_investing": _pick_number(row, "cashFromInvestingActivity", "investingCashFlow"),
        "cash_from_financing": _pick_number(row, "cashFromFinancingActivity", "financingCashFlow"),
        "source": source,
    }


def _shareholding_rows(symbol: str, data: Any, source: str) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    rows = _as_list(data.get("rows", []))
    labels = [str(label) for label in data.get("columns", []) if _parse_period_label(label)]
    if not labels:
        labels = sorted({label for row in rows for label in (row.get("data") or {}).keys() if _parse_period_label(label)})

    output = []
    for label in labels:
        period_end = _parse_period_label(label)
        if not period_end:
            continue
        bucket = {
            "symbol": symbol,
            "period_end_date": period_end,
            "promoter_holding": None,
            "promoter_pledge": None,
            "fii_holding": None,
            "dii_holding": None,
            "public_holding": None,
            "government_holding": None,
            "source": source,
        }
        for row in rows:
            raw = _safe_float((row.get("data") or {}).get(label))
            if raw is None:
                continue
            name = _norm_key(f"{row.get('catagory', '')} {row.get('name', '')}")
            field = _shareholding_field(name)
            if field:
                bucket[field] = (bucket[field] or 0) + raw
        output.append(bucket)
    return sorted(output, key=lambda item: item["period_end_date"], reverse=True)


def _shareholding_field(name: str) -> str | None:
    if "pledge" in name:
        return "promoter_pledge"
    if "promoter" in name:
        return "promoter_holding"
    if "foreigninstitution" in name or "foreignportfolio" in name or "fii" in name:
        return "fii_holding"
    if "domesticinstitution" in name or "mutualfund" in name or "insurance" in name or "dii" in name:
        return "dii_holding"
    if "government" in name:
        return "government_holding"
    if "public" in name or "noninstitution" in name or "individual" in name:
        return "public_holding"
    return None


def _latest_from_sections(rows: list[Any], *keys: str) -> float | None:
    return _pick_number(_latest_row_by_period([row for row in rows if isinstance(row, dict)]), *keys)


def _latest_row_by_period(rows: list[dict[str, Any]]) -> dict[str, Any]:
    best: tuple[date, dict[str, Any]] | None = None
    for row in rows:
        period = _period_end(row, "annual")
        if period and (best is None or period > best[0]):
            best = (period, row)
    return best[1] if best else (rows[0] if rows else {})


def _period_end(row: dict[str, Any], period: str) -> date | None:
    parsed = _parse_period_label(_pick(row, "header", "period", "date", "quote_date"))
    if parsed:
        return parsed
    year = _safe_int(row.get("year"))
    if year:
        return date(year, 3, 31) if period != "quarterly" else date(year, 3, 31)
    return None


def _as_list(value: Any) -> list[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        cleaned = re.sub(r"\s+", "", str(value)).replace(",", "").replace("%", "")
        if cleaned in {"", "-", "--", "NA", "N/A", "None"}:
            return None
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _pick(row: dict[str, Any], *keys: str) -> Any:
    normalized = {_norm_key(key): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(_norm_key(key))
        if value not in (None, ""):
            return value
    return None


def _pick_number(row: dict[str, Any], *keys: str) -> float | None:
    return _safe_float(_pick(row, *keys))


def _parse_period_label(label: Any) -> date | None:
    if not label:
        return None
    text = str(label).strip()
    for fmt in ("%b %Y", "%B %Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y"):
        try:
            parsed = datetime.strptime(text[:11], fmt)
            if fmt in ("%b %Y", "%B %Y"):
                month_end = {3: 31, 6: 30, 9: 30, 12: 31}.get(parsed.month, 28)
                return date(parsed.year, parsed.month, month_end)
            return parsed.date()
        except ValueError:
            continue
    return None


def _parse_finedge_date(value: Any):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(text[:11], fmt).date()
        except ValueError:
            continue
    return None


def _env_list(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]
