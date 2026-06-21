from __future__ import annotations

import asyncio
import logging
from typing import Any

import numpy as np
import pandas as pd

from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services import cache_policy
from app.services.asset_resolver import AssetResolution, AssetResolver, HIGH_CONFIDENCE
from app.services.comparison_reasoning import build_mf_why_better

logger = logging.getLogger(__name__)

MF_COMPARE_MIN_NAV_POINTS = 252


def _coerce_scheme_code_filter(value: Any) -> Any:
    text = str(value or "").strip()
    return int(text) if text.isdigit() else text


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.strip().upper() in {"N/A", "NA", "NONE", "NULL"}
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _to_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_price_df_index(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df = df.copy()
        df.index = df.index.tz_convert(None)
    return df


def _calculate_alpha_beta(local_hist: pd.DataFrame, benchmark_hist: pd.DataFrame) -> dict[str, Any]:
    if local_hist.empty or benchmark_hist.empty or len(local_hist) < 20 or len(benchmark_hist) < 20:
        return {}
    try:
        fund_close = _normalize_price_df_index(local_hist)["Close"].astype(float).ffill().dropna()
        bench_close = _normalize_price_df_index(benchmark_hist)["Close"].astype(float).ffill().dropna()
        fund_returns = fund_close.pct_change().dropna()
        bench_returns = bench_close.pct_change().dropna()
        aligned = pd.concat([fund_returns, bench_returns], axis=1, join="inner").dropna()
        if aligned.empty or len(aligned) < 20:
            return {}
        aligned.columns = ["fund", "benchmark"]
        benchmark_var = float(np.var(aligned["benchmark"]))
        if benchmark_var <= 1e-12:
            return {}
        beta = float(np.cov(aligned["fund"], aligned["benchmark"])[0][1] / benchmark_var)
        alpha = float((aligned["fund"].mean() - beta * aligned["benchmark"].mean()) * 252 * 100)
        span_days = max(int((aligned.index[-1] - aligned.index[0]).days), 1)
        return {
            "beta": round(beta, 2),
            "alpha_vs_nifty": round(alpha, 2),
            "risk_period": f"{max(round(span_days / 365, 1), 0.1)}Y",
        }
    except Exception as exc:
        logger.debug("Risk metric calculation failed: %s", exc)
        return {}


def _holding_key(row: dict[str, Any]) -> str | None:
    isin = str(row.get("isin") or "").strip().upper()
    if isin and isin not in {"N/A", "NA", "NONE", "NULL"}:
        return f"isin:{isin}"
    name = " ".join(str(row.get("security_name") or "").lower().split())
    return f"name:{name}" if name else None


def _holding_weight(row: dict[str, Any]) -> float:
    return _to_float(row.get("weight_pct")) or 0.0


def _build_holdings_overlap(comparison: dict[str, Any]) -> dict[str, Any]:
    valid = [(name, data) for name, data in comparison.items() if isinstance(data, dict) and not data.get("error")]
    if len(valid) < 2:
        return {"coverage_status": "unavailable", "reason": "Need two matched funds for holdings overlap."}
    (name_a, data_a), (name_b, data_b) = valid[:2]
    holdings_a = data_a.get("holdings") if isinstance(data_a.get("holdings"), list) else []
    holdings_b = data_b.get("holdings") if isinstance(data_b.get("holdings"), list) else []
    if not holdings_a or not holdings_b:
        return {
            "coverage_status": "unavailable",
            "reason": "Holdings data is unavailable for one or both funds.",
            "entities": [name_a, name_b],
            "top_common_holdings": [],
            "total_overlap_weight": 0,
        }
    map_a = {_holding_key(row): row for row in holdings_a if isinstance(row, dict) and _holding_key(row)}
    map_b = {_holding_key(row): row for row in holdings_b if isinstance(row, dict) and _holding_key(row)}
    common = []
    for key in sorted(set(map_a).intersection(map_b)):
        row_a = map_a[key]
        row_b = map_b[key]
        common.append({
            "name": row_a.get("security_name") or row_b.get("security_name") or "N/A",
            "isin": row_a.get("isin") or row_b.get("isin"),
            "sector": row_a.get("sector") or row_b.get("sector"),
            "weight_a": round(_holding_weight(row_a), 4),
            "weight_b": round(_holding_weight(row_b), 4),
            "overlap_weight": round(min(_holding_weight(row_a), _holding_weight(row_b)), 4),
        })
    common.sort(key=lambda row: row["overlap_weight"], reverse=True)
    return {
        "coverage_status": "available",
        "entities": [name_a, name_b],
        "common_holding_count": len(common),
        "top_common_holdings": common[:10],
        "total_overlap_weight": round(sum(row["overlap_weight"] for row in common), 4),
    }


def _build_comparison_summary(comparison: dict[str, Any]) -> dict[str, Any]:
    valid = [(name, data) for name, data in comparison.items() if isinstance(data, dict) and not data.get("error")]
    if len(valid) < 2:
        return {
            "headline": "Structured comparison is limited because one or more funds could not be matched.",
            "verdict_cards": [],
            "key_differences": ["Data coverage is insufficient for a decisive research snapshot."],
            "missing_data": [],
        }
    missing_data = []
    for name, data in valid[:2]:
        missing = [
            label
            for label, key in (
                ("1Y return", "return_1y"),
                ("3Y return", "return_3y"),
                ("5Y return", "return_5y"),
                ("expense ratio", "expense_ratio"),
                ("AUM", "aum"),
                ("volatility", "volatility_1y"),
                ("drawdown", "max_drawdown_1y"),
                ("Sharpe", "sharpe_ratio"),
            )
            if _is_missing(data.get(key))
        ]
        if missing:
            missing_data.append({"entity": name, "fields": missing})
    return {
        "headline": "Structured comparison is available; read the data notes before interpreting any edge.",
        "verdict_cards": [
            {
                "label": "Data quality",
                "value": "Complete" if not missing_data else "Partial",
                "note": "Core comparison fields are available." if not missing_data else "Some fields are missing; use the data notes before reading the verdict.",
            }
        ],
        "key_differences": ["Compare return, risk, cost, and holdings together rather than using a single metric."],
        "missing_data": missing_data,
    }


class CompareDataService:
    def __init__(self, repository: Any = None, resolver: AssetResolver | None = None):
        self.repository = repository if isinstance(repository, MutualFundRepository) else MutualFundRepository(repository)
        self.resolver = resolver if resolver is not None else AssetResolver(self.repository)

    async def build_mutual_fund_compare(
        self,
        entities: list[str],
        *,
        downside_focus: bool = False,
        pre_resolutions: list[AssetResolution] | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        resolutions = pre_resolutions or self.resolver.resolve_many(entities, asset_type="mutual_fund")
        benchmark_hist = await self._nifty_history_df()
        comparison: dict[str, Any] = {}
        data_status: dict[str, str] = {}

        for entity, resolution in zip(entities, resolutions):
            key = resolution.resolved_name or entity
            if not resolution.is_high_confidence or not resolution.id:
                comparison[key] = self._unavailable_item(resolution)
                data_status[key] = resolution.coverage_status
                continue

            row = self._core_snapshot_row(resolution.id)
            if not row:
                comparison[key] = self._unavailable_item(resolution, reason="Resolved fund is missing from local snapshot data.")
                data_status[key] = "partial"
                continue

            item = await self._comparison_item(row, resolution, benchmark_hist)
            comparison[key] = item
            data_status[key] = item.get("data_quality", {}).get("coverage_status", "complete")

        why_better = build_mf_why_better(comparison, downside_focus=downside_focus)
        quant_data = {
            "comparison": comparison,
            "why_better": why_better,
            "verdict_context": why_better.get("verdict_context"),
            "source_freshness": why_better.get("source_freshness"),
            "data_quality": {name: (payload.get("data_quality") or {}) for name, payload in comparison.items()},
            "risk_analysis": why_better.get("risk_analysis"),
            "asset_type": "mutual_fund",
            "resolution": [resolution.client_payload() for resolution in resolutions],
        }
        quant_data["holdings_overlap"] = _build_holdings_overlap(comparison)
        quant_data["comparison_summary"] = _build_comparison_summary(comparison)

        coverage_status = self._aggregate_coverage(data_status)
        logger.info(
            "compare_data trace_id=%s coverage=%s data_status=%s resolution=%s",
            trace_id,
            coverage_status,
            data_status,
            [resolution.client_payload() for resolution in resolutions],
        )
        return {
            "quant_data": quant_data,
            "entities": list(comparison.keys()),
            "resolution": [resolution.client_payload() for resolution in resolutions],
            "coverage_status": coverage_status,
            "data_status": data_status,
        }

    def _core_snapshot_row(self, scheme_code: Any) -> dict[str, Any] | None:
        if not self.repository:
            return None
        try:
            return self.repository.get_fund_by_scheme_code(scheme_code)
        except Exception as exc:
            logger.warning("MF core snapshot lookup failed for %s: %s", scheme_code, exc)
            return None

    async def _comparison_item(self, row: dict[str, Any], resolution: AssetResolution, benchmark_hist: pd.DataFrame) -> dict[str, Any]:
        scheme_code = row.get("scheme_code") or resolution.id
        history_summary = self._nav_history_summary(scheme_code)
        holdings_rows, sector_rows, holdings_as_of = await asyncio.to_thread(self._load_holdings_and_sectors, scheme_code)
        hist = await self._mf_history_df(scheme_code)
        risk_metrics = _calculate_alpha_beta(hist, benchmark_hist) if not hist.empty and not benchmark_hist.empty else {}
        benchmark = row.get("benchmark") or "NIFTY"
        benchmark_source = "fund_benchmark" if row.get("benchmark") else "nifty_fallback"
        missing_fields = [
            field
            for field in ("nav", "nav_date", "expense_ratio", "aum")
            if _is_missing(row.get(field))
        ]
        if benchmark_source == "nifty_fallback":
            missing_fields.append("fund_benchmark")

        provider_payload = row.get("provider_payload") or {}
        qualitative = provider_payload.get("qualitative_insights") or {}

        item = {
            "scheme_code": str(scheme_code) if scheme_code is not None else None,
            "name": row.get("scheme_name") or resolution.resolved_name,
            "resolved_scheme_name": row.get("scheme_name") or resolution.resolved_name,
            "history_points": history_summary.get("count"),
            "first_nav_date": history_summary.get("first_nav_date"),
            "last_nav_date": history_summary.get("last_nav_date"),
            "nav": row.get("nav"),
            "nav_date": row.get("nav_date"),
            "category": row.get("category"),
            "benchmark": benchmark,
            "benchmark_source": benchmark_source,
            "fund_manager": row.get("fund_manager"),
            "main_style": qualitative.get("main_style"),
            "minimum_sip": qualitative.get("minimum_sip"),
            "mandate": qualitative.get("mandate"),
            "best_for": qualitative.get("best_for"),
            "main_risk": qualitative.get("main_risk"),
            "risk_level": row.get("risk_level"),
            "fund_house": row.get("amc_name") or row.get("fund_house"),
            "expense_ratio": row.get("expense_ratio"),
            "aum": row.get("aum"),
            "return_1y": row.get("return_1y"),
            "return_3y": row.get("return_3y"),
            "return_5y": row.get("return_5y"),
            "volatility_1y": row.get("volatility_1y"),
            "max_drawdown_1y": row.get("max_drawdown_1y"),
            "sharpe_ratio": row.get("sharpe_ratio"),
            "alpha": row.get("alpha"),
            "beta": row.get("beta"),
            "source": "FundersAI DB",
            "source_summary": {
                "metadata": "FundersAI DB",
                "stale": not cache_policy.is_fresh(row.get("nav_date") or row.get("last_updated"), "mutual_fund_nav"),
                "nav_date": row.get("nav_date"),
                "holdings_as_of_date": holdings_as_of,
                "benchmark_source": benchmark_source,
                "benchmark_note": "Fund benchmark unavailable; Nifty is used as fallback context." if benchmark_source == "nifty_fallback" else None,
            },
            "data_quality": {
                "missing_fields": missing_fields,
                "message": "Some mutual fund fields are unavailable from local Supabase data." if missing_fields else "Complete for requested fields.",
                "coverage_status": "incomplete" if missing_fields else "complete",
            },
            "history_coverage": history_summary,
            "holdings": holdings_rows,
            "sector_allocation": sector_rows,
        }
        item.update(risk_metrics)
        return item

    def _unavailable_item(self, resolution: AssetResolution, reason: str | None = None) -> dict[str, Any]:
        message = reason or "Mutual fund could not be matched with high confidence in local Supabase data."
        return {
            "error": message,
            "data_quality": {
                "missing_fields": ["scheme_code"],
                "message": message,
                "coverage_status": "incomplete",
            },
            "source_summary": {"metadata": None, "stale": True, "nav_date": None},
            "holdings": [],
            "resolution": resolution.client_payload(),
        }

    def _nav_history_summary(self, scheme_code: Any) -> dict[str, Any]:
        default = {"count": 0, "first_nav_date": None, "last_nav_date": None, "supports": {"1Y": False, "3Y": False, "5Y": False}}
        if not self.repository or scheme_code in (None, ""):
            return default
        try:
            rows = self.repository.get_nav_history_rows(scheme_code, fields="nav_date", limit=5000, desc=False)
            if not rows:
                return default
            return {
                "count": len(rows),
                "first_nav_date": rows[0].get("nav_date"),
                "last_nav_date": rows[-1].get("nav_date"),
                "supports": self._supports_from_history(rows[0].get("nav_date"), rows[-1].get("nav_date")),
            }
        except Exception:
            return default

    def _supports_from_history(self, first_nav: Any, last_nav: Any) -> dict[str, bool]:
        try:
            first_dt = pd.to_datetime(first_nav)
            last_dt = pd.to_datetime(last_nav)
            span_days = max(int((last_dt - first_dt).days), 0)
            return {"1Y": span_days >= 365, "3Y": span_days >= 365 * 3, "5Y": span_days >= 365 * 5}
        except Exception:
            return {"1Y": False, "3Y": False, "5Y": False}

    async def _mf_history_df(self, scheme_code: Any, days: int = 1100) -> pd.DataFrame:
        if not self.repository or scheme_code in (None, ""):
            return pd.DataFrame()

        def _fetch_rows() -> list[dict[str, Any]]:
            return self.repository.get_nav_history_rows(scheme_code, fields="nav,nav_date", limit=days, desc=True)

        try:
            rows = await asyncio.to_thread(_fetch_rows)
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["nav_date"])
            df = df.sort_values("date")
            df.rename(columns={"nav": "Close"}, inplace=True)
            df.set_index("date", inplace=True)
            return _normalize_price_df_index(df)
        except Exception:
            return pd.DataFrame()

    async def _nifty_history_df(self, days: int = 1100) -> pd.DataFrame:
        if not self.repository:
            return pd.DataFrame()

        def _fetch_rows() -> list[dict[str, Any]]:
            return self.repository.get_nifty_price_rows(limit=days)

        try:
            rows = await asyncio.to_thread(_fetch_rows)
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            df.rename(columns={"close": "Close"}, inplace=True)
            df.set_index("date", inplace=True)
            return _normalize_price_df_index(df)
        except Exception:
            return pd.DataFrame()

    def _load_holdings_and_sectors(self, scheme_code: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
        if not self.repository or scheme_code in (None, ""):
            return [], [], None
        try:
            holding_rows = self.repository.get_latest_holdings(scheme_code)
        except Exception:
            holding_rows = []
        latest_as_of = None
        holdings = []
        for row in holding_rows:
            as_of = row.get("as_of_date")
            if latest_as_of is None:
                latest_as_of = as_of
            if as_of != latest_as_of:
                continue
            holdings.append({
                "security_name": row.get("security_name"),
                "isin": row.get("isin"),
                "sector": row.get("sector"),
                "weight_pct": row.get("weight_pct"),
                "as_of_date": as_of,
                "source": row.get("source"),
                "provider_payload": row.get("provider_payload"),
            })
        try:
            sectors = self.repository.get_sector_rows(scheme_code)
        except Exception:
            sectors = []
        return holdings, sectors, latest_as_of

    def _aggregate_coverage(self, data_status: dict[str, str]) -> str:
        if not data_status:
            return "unavailable"
        values = set(data_status.values())
        if values == {"complete"}:
            return "complete"
        if values.intersection({"complete", "incomplete", "partial"}):
            return "partial"
        return "unavailable"
