from __future__ import annotations

import asyncio
import logging
from typing import Any

import numpy as np
import pandas as pd

from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.mf_nav_freshness import assess_nav_freshness
from app.services.asset_resolver import AssetResolution, AssetResolver, HIGH_CONFIDENCE
from app.services.comparison_reasoning import build_mf_why_better
from app.services.mf_holdings_quality import is_holding_summary_or_noise
from app.services.mf_metrics_service import NAV_METRIC_SNAPSHOT_VERSION, compute_nav_metrics
from app.services.mfapi_service import get_nav_cache_summary, get_stored_nav_history

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


def _metric_snapshot_metadata(row: dict[str, Any]) -> dict[str, Any]:
    provider_payload = row.get("provider_payload")
    if not isinstance(provider_payload, dict):
        return {}
    metadata = provider_payload.get("metric_snapshot")
    return metadata if isinstance(metadata, dict) else {}


def _has_precomputed_metric_snapshot(row: dict[str, Any] | None) -> bool:
    if not isinstance(row, dict):
        return False
    metadata = _metric_snapshot_metadata(row)
    return (
        metadata.get("version") == NAV_METRIC_SNAPSHOT_VERSION
        and bool(metadata.get("as_of_date"))
    )


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
        async def _load_core_row(resolution: AssetResolution) -> dict[str, Any] | None:
            if not resolution.is_high_confidence or not resolution.id:
                return None
            return await asyncio.to_thread(self._core_snapshot_row, resolution.id)

        core_rows = await asyncio.gather(*[_load_core_row(resolution) for resolution in resolutions])
        needs_request_metrics = any(
            row and not _has_precomputed_metric_snapshot(row)
            for row in core_rows
        )
        benchmark_task = asyncio.create_task(self._nifty_history_df()) if needs_request_metrics else None

        async def _build_entry(
            entity: str,
            resolution: AssetResolution,
            row: dict[str, Any] | None,
        ) -> tuple[str, dict[str, Any], str]:
            key = resolution.resolved_name or entity
            if not resolution.is_high_confidence or not resolution.id:
                return key, self._unavailable_item(resolution), resolution.coverage_status
            if not row:
                return key, self._unavailable_item(
                    resolution,
                    reason="Resolved fund is missing from local snapshot data.",
                ), "partial"
            item = await self._comparison_item(row, resolution, benchmark_task)
            return key, item, item.get("data_quality", {}).get("coverage_status", "complete")

        entries = await asyncio.gather(*[
            _build_entry(entity, resolution, row)
            for entity, resolution, row in zip(entities, resolutions, core_rows)
        ])
        comparison: dict[str, Any] = {}
        data_status: dict[str, str] = {}
        for key, item, status in entries:
            comparison[key] = item
            data_status[key] = status

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

    async def build_mutual_fund_compare_summary(
        self,
        entities: list[str],
        *,
        downside_focus: bool = False,
        pre_resolutions: list[AssetResolution] | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Build the small comparison payload used before the canvas opens.

        The canvas loads its own NAV history, holdings, and sector detail. Keeping
        those reads out of chat removes duplicate remote reads from the first paint.
        """
        resolutions = pre_resolutions or self.resolver.resolve_many(entities, asset_type="mutual_fund")

        async def _load_core_row(resolution: AssetResolution) -> dict[str, Any] | None:
            if not resolution.is_high_confidence or not resolution.id:
                return None
            return await asyncio.to_thread(self._core_snapshot_row, resolution.id)

        core_rows = await asyncio.gather(*[_load_core_row(resolution) for resolution in resolutions])
        comparison: dict[str, Any] = {}
        data_status: dict[str, str] = {}
        for entity, resolution, row in zip(entities, resolutions, core_rows):
            key = resolution.resolved_name or entity
            if not resolution.is_high_confidence or not resolution.id:
                item = self._unavailable_item(resolution)
                status = resolution.coverage_status
            elif not row:
                item = self._unavailable_item(
                    resolution,
                    reason="Resolved fund is missing from local snapshot data.",
                )
                status = "partial"
            else:
                item = self._summary_item(row, resolution)
                status = item["data_quality"]["coverage_status"]
            comparison[key] = item
            data_status[key] = status

        why_better = build_mf_why_better(comparison, downside_focus=downside_focus)
        why_better["data_limitations"] = [
            limitation
            for limitation in why_better.get("data_limitations", [])
            if "holdings data missing" not in str(limitation).lower()
            and "holdings-based reasoning unavailable" not in str(limitation).lower()
        ]
        why_better["holdings_based_reasoning"] = {
            "status": "deferred_to_canvas",
            "reason": "Holdings and sector detail load in the comparison canvas.",
        }
        risk_analysis = why_better.get("risk_analysis")
        if isinstance(risk_analysis, dict) and isinstance(risk_analysis.get("items"), list):
            risk_analysis["items"] = [
                item
                for item in risk_analysis["items"]
                if not (isinstance(item, dict) and item.get("label") == "Concentration risk")
            ]
        quant_data = {
            "comparison": comparison,
            "why_better": why_better,
            "verdict_context": why_better.get("verdict_context"),
            "source_freshness": why_better.get("source_freshness"),
            "data_quality": {name: (payload.get("data_quality") or {}) for name, payload in comparison.items()},
            "risk_analysis": why_better.get("risk_analysis"),
            "asset_type": "mutual_fund",
            "comparison_data_level": "summary",
            "resolution": [resolution.client_payload() for resolution in resolutions],
        }
        quant_data["comparison_summary"] = _build_comparison_summary(comparison)
        coverage_status = self._aggregate_coverage(data_status)
        logger.info(
            "compare_summary trace_id=%s coverage=%s data_status=%s resolution=%s",
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

    async def _comparison_item(
        self,
        row: dict[str, Any],
        resolution: AssetResolution,
        benchmark_task: asyncio.Task[pd.DataFrame] | None,
    ) -> dict[str, Any]:
        scheme_code = row.get("scheme_code") or resolution.id
        uses_precomputed_metrics = _has_precomputed_metric_snapshot(row)
        if uses_precomputed_metrics:
            holdings_result, history_summary = await asyncio.gather(
                self._load_holdings_and_sectors(scheme_code),
                asyncio.to_thread(self._nav_history_summary, scheme_code),
            )
            hist = pd.DataFrame()
            benchmark_hist = pd.DataFrame()
        else:
            pending = [
                self._load_holdings_and_sectors(scheme_code),
                self._mf_history_df(scheme_code),
                asyncio.to_thread(self._nav_history_summary, scheme_code),
            ]
            if benchmark_task is not None:
                pending.append(asyncio.shield(benchmark_task))
            results = await asyncio.gather(*pending)
            holdings_result = results[0]
            hist = results[1]
            history_summary = results[2]
            benchmark_hist = results[3] if len(results) > 3 else pd.DataFrame()
        holdings_rows, sector_rows, holdings_as_of = holdings_result
        history_rows = [
            {"nav_date": index.strftime("%Y-%m-%d"), "nav": float(value)}
            for index, value in hist["Close"].items()
        ] if not hist.empty else []
        refreshed_metrics = compute_nav_metrics(history_rows, risk_free_rate=0.06) if history_rows else {}
        risk_metrics = _calculate_alpha_beta(hist, benchmark_hist) if not hist.empty and not benchmark_hist.empty else {}
        metric_snapshot = _metric_snapshot_metadata(row)
        benchmark = row.get("benchmark") or "NIFTY"
        benchmark_source = "fund_benchmark" if row.get("benchmark") else "nifty_fallback"
        missing_fields = [
            field
            for field in ("nav", "nav_date", "expense_ratio", "aum")
            if _is_missing(row.get(field))
        ]
        limitations = []
        if benchmark_source == "nifty_fallback":
            limitations.append("Fund benchmark is unavailable; NIFTY is used only as fallback context.")

        provider_payload = row.get("provider_payload") or {}
        qualitative = provider_payload.get("qualitative_insights") or {}
        nav_freshness = assess_nav_freshness(row.get("nav_date") or row.get("last_updated"))

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
            "return_1y": refreshed_metrics.get("return_1y") if refreshed_metrics.get("return_1y") is not None else row.get("return_1y"),
            "return_3y": refreshed_metrics.get("return_3y") if refreshed_metrics.get("return_3y") is not None else row.get("return_3y"),
            "return_5y": refreshed_metrics.get("return_5y") if refreshed_metrics.get("return_5y") is not None else row.get("return_5y"),
            "volatility_1y": refreshed_metrics.get("volatility_1y") if refreshed_metrics.get("volatility_1y") is not None else row.get("volatility_1y"),
            "max_drawdown_1y": refreshed_metrics.get("max_drawdown_1y") if refreshed_metrics.get("max_drawdown_1y") is not None else row.get("max_drawdown_1y"),
            "sharpe_ratio": refreshed_metrics.get("sharpe_ratio") if refreshed_metrics.get("sharpe_ratio") is not None else row.get("sharpe_ratio"),
            "alpha": row.get("alpha"),
            "beta": row.get("beta"),
            "metrics_source": "precomputed_snapshot" if uses_precomputed_metrics else "request_fallback",
            "metrics_as_of_date": metric_snapshot.get("as_of_date") if uses_precomputed_metrics else history_summary.get("last_nav_date"),
            "source": "FundersAI DB",
            "source_summary": {
                "metadata": "FundersAI DB",
                "stale": nav_freshness["status"] == "stale",
                "status": nav_freshness["status"],
                "expected_nav_date": nav_freshness["expected_nav_date"],
                "missed_business_days": nav_freshness["missed_business_days"],
                "nav_date": row.get("nav_date"),
                "holdings_as_of_date": holdings_as_of,
                "benchmark_source": benchmark_source,
                "benchmark_note": "Fund benchmark unavailable; Nifty is used as fallback context." if benchmark_source == "nifty_fallback" else None,
                "nav_history": {
                    "status": history_summary.get("cache_status"),
                    "stale": history_summary.get("stale"),
                    "fetched_at": history_summary.get("fetched_at"),
                },
                "metrics": {
                    "source": "precomputed_snapshot" if uses_precomputed_metrics else "request_fallback",
                    "version": metric_snapshot.get("version") if uses_precomputed_metrics else None,
                    "as_of_date": metric_snapshot.get("as_of_date") if uses_precomputed_metrics else history_summary.get("last_nav_date"),
                    "computed_at": metric_snapshot.get("computed_at") if uses_precomputed_metrics else None,
                },
            },
            "data_quality": {
                "missing_fields": missing_fields,
                "limitations": limitations,
                "message": "Some mutual fund fields are unavailable from local Supabase data." if missing_fields else "Complete for requested fields.",
                "coverage_status": "incomplete" if missing_fields else "complete",
            },
            "history_coverage": history_summary,
            "holdings": holdings_rows,
            "sector_allocation": sector_rows,
        }
        item.update(risk_metrics)
        return item

    def _summary_item(self, row: dict[str, Any], resolution: AssetResolution) -> dict[str, Any]:
        """Return snapshot metrics only; detailed data is loaded by the canvas."""
        scheme_code = row.get("scheme_code") or resolution.id
        missing_fields = [
            field
            for field in (
                "nav",
                "nav_date",
                "return_3y",
                "volatility_1y",
                "max_drawdown_1y",
                "expense_ratio",
                "aum",
            )
            if _is_missing(row.get(field))
        ]
        nav_freshness = assess_nav_freshness(row.get("nav_date") or row.get("last_updated"))
        return {
            "scheme_code": str(scheme_code) if scheme_code is not None else None,
            "name": row.get("scheme_name") or resolution.resolved_name,
            "resolved_scheme_name": row.get("scheme_name") or resolution.resolved_name,
            "nav": row.get("nav"),
            "nav_date": row.get("nav_date"),
            "category": row.get("category"),
            "benchmark": row.get("benchmark"),
            "fund_manager": row.get("fund_manager"),
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
                "stale": nav_freshness["status"] == "stale",
                "status": nav_freshness["status"],
                "expected_nav_date": nav_freshness["expected_nav_date"],
                "missed_business_days": nav_freshness["missed_business_days"],
                "nav_date": row.get("nav_date"),
            },
            "data_quality": {
                "missing_fields": missing_fields,
                "limitations": ["Detailed NAV history, holdings, and sector data load in the comparison canvas."],
                "message": "Some mutual fund snapshot fields are unavailable." if missing_fields else "Snapshot comparison fields are available.",
                "coverage_status": "incomplete" if missing_fields else "complete",
            },
            "holdings": [],
            "sector_allocation": [],
        }

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
        summary = get_nav_cache_summary(str(scheme_code or ""))
        return {
            **summary,
            "supports": self._supports_from_history(summary.get("first_nav_date"), summary.get("last_nav_date")),
        }

    def _supports_from_history(self, first_nav: Any, last_nav: Any) -> dict[str, bool]:
        try:
            first_dt = pd.to_datetime(first_nav)
            last_dt = pd.to_datetime(last_nav)
            span_days = max(int((last_dt - first_dt).days), 0)
            return {"1Y": span_days >= 365, "3Y": span_days >= 365 * 3, "5Y": span_days >= 365 * 5}
        except Exception:
            return {"1Y": False, "3Y": False, "5Y": False}

    async def _mf_history_df(self, scheme_code: Any, days: int = 2200) -> pd.DataFrame:
        if scheme_code in (None, ""):
            return pd.DataFrame()

        def _fetch_rows() -> list[dict[str, Any]]:
            result = get_stored_nav_history(str(scheme_code))
            rows = result.get("data") if result.get("ok") else []
            return rows[-max(int(days), 1):]

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

    async def _load_holdings_and_sectors(
        self,
        scheme_code: Any,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
        if not self.repository or scheme_code in (None, ""):
            return [], [], None
        try:
            family_id = await asyncio.to_thread(self.repository.get_family_id_for_scheme, scheme_code)
        except Exception:
            family_id = None

        async def _holdings() -> list[dict[str, Any]]:
            try:
                return await asyncio.to_thread(
                    self.repository.get_latest_holdings_for_resolved_family,
                    scheme_code,
                    family_id,
                )
            except Exception:
                return []

        async def _sectors() -> list[dict[str, Any]]:
            try:
                return await asyncio.to_thread(
                    self.repository.get_sector_rows_for_resolved_family,
                    scheme_code,
                    family_id,
                )
            except Exception:
                return []

        holding_rows, sectors = await asyncio.gather(_holdings(), _sectors())
        latest_as_of = None
        holdings = []
        for row in holding_rows:
            as_of = row.get("as_of_date")
            if latest_as_of is None:
                latest_as_of = as_of
            if as_of != latest_as_of:
                continue
            if is_holding_summary_or_noise(row.get("security_name")):
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
