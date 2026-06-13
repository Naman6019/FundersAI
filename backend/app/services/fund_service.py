import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional, Tuple

from app.database import supabase
from app.models.fund_models import (
    FundDetails, FundReturns, RiskMetrics, NavHistoryPoint,
    FundDataQuality, FundProfileResponse, FundHolding, SectorAllocation
)

logger = logging.getLogger(__name__)

DEBUG_MF_RESOLUTION = True
MF_COMPARE_MIN_NAV_POINTS = 10

def _to_utc_datetime(date_val: Any) -> datetime | None:
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val.astimezone(timezone.utc)
    try:
        dt = pd.to_datetime(date_val)
        if dt.tzinfo is None:
            dt = dt.tz_localize("UTC")
        return dt.to_pydatetime()
    except Exception:
        return None

def _normalize_fund_text(text: str) -> str:
    return " ".join(
        text.lower()
        .replace("smallcap", "small cap")
        .replace("midcap", "mid cap")
        .replace("largecap", "large cap")
        .replace("bluechip", "blue chip")
        .replace("-", " ")
        .split()
    )

def _coerce_scheme_code_filter(scheme_code_value: Any):
    if scheme_code_value in (None, ""):
        return None
    scheme_code_str = str(scheme_code_value).strip()
    if not scheme_code_str:
        return None
    return int(scheme_code_str) if scheme_code_str.isdigit() else scheme_code_str

class FundService:
    @staticmethod
    def get_nav_history_summary(scheme_code_value: Any, cache: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        key = str(scheme_code_value or "").strip()
        default_summary = {"count": 0, "first_nav_date": None, "last_nav_date": None}
        
        if not key:
            return default_summary
        if cache is not None and key in cache:
            return cache[key]

        code_filter = _coerce_scheme_code_filter(scheme_code_value)
        if code_filter is None or not supabase:
            if cache is not None:
                cache[key] = default_summary
            return default_summary

        summary = dict(default_summary)
        try:
            count_res = supabase.table("mutual_fund_nav_history").select("nav_date", count="exact").eq("scheme_code", code_filter).execute()
            summary["count"] = int(count_res.count or 0)

            first_res = supabase.table("mutual_fund_nav_history").select("nav_date").eq("scheme_code", code_filter).order("nav_date", desc=False).limit(1).execute()
            last_res = supabase.table("mutual_fund_nav_history").select("nav_date").eq("scheme_code", code_filter).order("nav_date", desc=True).limit(1).execute()
            
            first_row = (first_res.data or [None])[0]
            last_row = (last_res.data or [None])[0]
            
            summary["first_nav_date"] = first_row.get("nav_date") if isinstance(first_row, dict) else None
            summary["last_nav_date"] = last_row.get("nav_date") if isinstance(last_row, dict) else None
        except Exception as exc:
            if DEBUG_MF_RESOLUTION:
                logger.warning("MF nav history summary lookup failed for %s: %s", key, exc)

        if cache is not None:
            cache[key] = summary
        return summary

    @staticmethod
    def score_fund_candidates(entity: str, rows: List[Dict], nav_history_cache: Optional[Dict[str, Dict[str, Any]]] = None, min_history_points: int = 0) -> List[Dict[str, Any]]:
        if not rows:
            return []

        entity_norm = _normalize_fund_text(entity.replace(" fund", "").replace(" growth", ""))
        entity_words = [w for w in entity_norm.split() if len(w) > 2]
        wants_passive = "passive" in entity_norm
        wants_fof = "fund of funds" in entity_norm or "fof" in entity_norm
        wants_multi_asset = "multi asset" in entity_norm
        wants_direct = "direct" in entity_norm
        wants_regular = "regular" in entity_norm

        scored_rows: List[Dict[str, Any]] = []
        for row in rows:
            notes: List[str] = []
            name_norm = _normalize_fund_text(row.get("scheme_name", ""))
            value = 0
            if entity_norm and entity_norm in name_norm:
                value += 100
                notes.append("name_contains_full_query:+100")
            overlap_hits = sum(1 for word in entity_words if word in name_norm)
            if overlap_hits:
                value += overlap_hits * 100
                notes.append(f"token_overlap:+{overlap_hits * 100}")
            
            # Always prefer Direct Growth siblings for AMC-derived fields.
            if "direct" in name_norm:
                value += 30
                notes.append("direct_bonus:+30")
            else:
                value -= 20
                notes.append("direct_missing_penalty:-20")
            if "growth" in name_norm:
                value += 20
                notes.append("growth_bonus:+20")
            if "regular" in name_norm:
                value -= 35
                notes.append("regular_penalty:-35")
            if "idcw" in name_norm or "dividend" in name_norm:
                value -= 25
                notes.append("idcw_dividend_penalty:-25")
            if "index" in name_norm and "index" not in entity_norm:
                value -= 35
                notes.append("index_mismatch_penalty:-35")
            if "etf" in name_norm and "etf" not in entity_norm:
                value -= 35
                notes.append("etf_mismatch_penalty:-35")
            if "institutional" in name_norm and "institutional" not in entity_norm:
                value -= 20
                notes.append("institutional_penalty:-20")
            if "passive" in name_norm and not wants_passive:
                value -= 80
                notes.append("passive_mismatch_penalty:-80")
            if "fund of funds" in name_norm and not wants_fof:
                value -= 70
                notes.append("fof_mismatch_penalty:-70")
            if "multi asset" in name_norm and not wants_multi_asset:
                value -= 80
                notes.append("multi_asset_mismatch_penalty:-80")
            if wants_direct and "regular" in name_norm:
                value -= 60
                notes.append("direct_requested_regular_penalty:-60")
            if wants_regular and "direct" in name_norm:
                value -= 60
                notes.append("regular_requested_direct_penalty:-60")
            if wants_multi_asset and "multi asset" in name_norm:
                value += 20
                notes.append("multi_asset_match_bonus:+20")
            if wants_multi_asset and "fund of funds" in name_norm and not wants_fof:
                value -= 30
                notes.append("multi_asset_fof_penalty:-30")

            history = FundService.get_nav_history_summary(row.get("scheme_code"), nav_history_cache)
            history_points = int(history.get("count") or 0)
            if history_points == 0:
                value -= 30
                notes.append("no_nav_history_penalty:-30")
            else:
                history_bonus = min(history_points // 200, 30)
                value += history_bonus
                notes.append(f"history_bonus:+{history_bonus}")
            if min_history_points > 0 and history_points < min_history_points:
                value -= 120
                notes.append(f"min_history_penalty:-120(required={min_history_points})")

            scored_rows.append({
                "score": value,
                "history_points": history_points,
                "row": row,
                "notes": notes,
                "history_summary": history,
            })

        scored_rows.sort(key=lambda item: item["score"], reverse=True)
        return scored_rows

    @staticmethod
    def pick_best_fund_match(entity: str, rows: List[Dict], nav_history_cache: Optional[Dict[str, Dict[str, Any]]] = None, min_history_points: int = 0) -> Optional[Dict]:
        scored_rows = FundService.score_fund_candidates(entity, rows, nav_history_cache, min_history_points)
        return scored_rows[0]["row"] if scored_rows else None

    @staticmethod
    def get_mf_history_df(scheme_code: Any, days: int = 1100) -> pd.DataFrame:
        if not supabase:
            return pd.DataFrame()

        def _fetch_rows_for_filter(code_filter: Any, max_rows: int) -> List[Dict[str, Any]]:
            batch_size = 1000
            offset = 0
            collected: List[Dict[str, Any]] = []
            while offset < max_rows:
                chunk = (
                    supabase.table('mutual_fund_nav_history')
                    .select('nav, nav_date')
                    .eq('scheme_code', code_filter)
                    .order('nav_date', desc=True)
                    .range(offset, offset + batch_size - 1)
                    .execute()
                    .data or []
                )
                if not chunk:
                    break
                collected.extend(chunk)
                if len(chunk) < batch_size:
                    break
                offset += batch_size
            return collected[:max_rows]

        try:
            # We only need one query since Supabase casts string to int safely for eq checks
            best_rows = _fetch_rows_for_filter(scheme_code, days)

            # Fallback to MFAPI if database has extremely stale/limited history
            if len(best_rows) < min(days, 50):
                from app.services.mfapi_service import get_nav_history as mfapi_get_nav_history
                mfapi_res = mfapi_get_nav_history(str(scheme_code))
                if mfapi_res.get("ok") and mfapi_res.get("data"):
                    # mfapi returns oldest first typically or newest? We will sort it in DataFrame
                    mfapi_data = mfapi_res["data"]
                    # Limit to requested days
                    best_rows = mfapi_data[:days]

            if best_rows:
                df = pd.DataFrame(best_rows)
                df['date'] = pd.to_datetime(df['nav_date'])
                df = df.sort_values('date')
                df.rename(columns={'nav': 'Close'}, inplace=True)
                df.set_index('date', inplace=True)
                
                # Normalize index
                if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
                    df.index = df.index.tz_convert(None)
                return df
        except Exception as e:
            logger.error(f"Failed to fetch local MF history for {scheme_code}: {e}")
        return pd.DataFrame()

    @staticmethod
    def load_latest_fund_holdings(scheme_code_value: Any) -> Tuple[List[FundHolding], Optional[str]]:
        if not supabase or scheme_code_value in (None, ""):
            return [], None
        scheme_code = str(scheme_code_value)
        try:
            rows = (
                supabase.table("mutual_fund_holdings")
                .select("as_of_date,security_name,isin,sector,weight_pct,source,provider_payload")
                .eq("scheme_code", int(scheme_code) if scheme_code.isdigit() else scheme_code)
                .order("as_of_date", desc=True)
                .order("weight_pct", desc=True)
                .limit(500)
                .execute()
                .data or []
            )
        except Exception:
            return [], None

        latest_as_of = None
        holdings: List[FundHolding] = []
        for row in rows:
            as_of = row.get("as_of_date")
            if latest_as_of is None:
                latest_as_of = as_of
            if as_of != latest_as_of:
                continue
            holdings.append(FundHolding(**row))
        return holdings, latest_as_of

    @staticmethod
    def get_mutual_fund_profile(scheme_code: int) -> Optional[FundProfileResponse]:
        if not supabase:
            return None

        # Fetch snapshot
        fund_res = supabase.table('mutual_fund_core_snapshot').select('*').eq('scheme_code', str(scheme_code)).limit(1).execute()
        if not fund_res.data:
            fund_res = supabase.table('mutual_funds').select('*').eq('scheme_code', scheme_code).limit(1).execute()
        
        if not fund_res.data:
            return None

        raw_details = fund_res.data[0]

        # Fallback to legacy mutual_funds table for missing AUM/Expense Ratio
        if not raw_details.get("aum") or not raw_details.get("expense_ratio"):
            legacy_res = supabase.table("mutual_funds").select("*").eq("scheme_code", scheme_code).limit(1).execute()
            if legacy_res.data:
                legacy_row = legacy_res.data[0]
                if not raw_details.get("aum"):
                    raw_details["aum"] = legacy_row.get("aum")
                if not raw_details.get("expense_ratio"):
                    raw_details["expense_ratio"] = legacy_row.get("expense_ratio")

        # Fetch holdings & calculate sectors
        holdings, _ = FundService.load_latest_fund_holdings(scheme_code)
        sector_map = {}
        for h in holdings:
            sec = h.sector or "Unclassified"
            sector_map[sec] = sector_map.get(sec, 0.0) + float(h.weight_pct or 0.0)
            
        sorted_sectors = [
            SectorAllocation(sector_name=k, weight_pct=round(v, 2)) 
            for k, v in sorted(sector_map.items(), key=lambda item: item[1], reverse=True)
        ]

        # Fetch NAV History
        hist_df = FundService.get_mf_history_df(scheme_code, days=2200)
        close_series = hist_df["Close"] if not hist_df.empty else pd.Series(dtype=float)

        nav_points = []
        chart_df = hist_df.sort_index().tail(250) if not hist_df.empty else pd.DataFrame()
        if not chart_df.empty:
            for idx, val in chart_df["Close"].items():
                nav_points.append(NavHistoryPoint(date=idx.strftime("%d-%m-%Y"), value=round(float(val), 4)))

        # Risk & Returns logic
        def _compute_cagr(series: pd.Series, years: int):
            if series.empty: 
                print(f"_compute_cagr({years}): series empty")
                return None
            current_date = series.index[-1]
            target_date = current_date - pd.DateOffset(years=years)
            historical = series[series.index <= target_date]
            if historical.empty: 
                print(f"_compute_cagr({years}): historical empty (target: {target_date}, min: {series.index[0]})")
                return None
            current_val = float(series.iloc[-1])
            past_val = float(historical.iloc[-1])
            if past_val <= 0: 
                print(f"_compute_cagr({years}): past_val <= 0")
                return None
            cagr = (current_val / past_val) ** (1 / years) - 1
            print(f"_compute_cagr({years}): SUCCESS -> {round(cagr * 100, 2)}")
            return round(cagr * 100, 2)

        def _compute_risk(series: pd.Series, risk_free_rate: float = 0.06):
            series = series.astype(float).dropna()
            if len(series) < 2: return {}
            rets = series.pct_change().dropna()
            if rets.empty: return {}

            mean_daily = float(rets.mean())
            std_daily = float(rets.std(ddof=0))
            ann_std = std_daily * np.sqrt(252)
            ann_return = mean_daily * 252

            sharpe = None if ann_std == 0 else (ann_return - risk_free_rate) / ann_std
            downside = rets[rets < 0]
            downside_std = float(np.sqrt(np.mean(np.square(downside)))) * np.sqrt(252) if len(downside) > 0 else 0.0
            sortino = None if downside_std == 0 else (ann_return - risk_free_rate) / downside_std

            running_max = series.cummax()
            drawdown = (running_max - series) / running_max.replace(0, np.nan)
            max_drawdown = float(drawdown.max()) if not drawdown.empty else 0.0

            return {
                "stdDev": round(ann_std, 4),
                "sharpeRatio": round(sharpe, 2) if sharpe is not None else None,
                "sortinoRatio": round(sortino, 2) if sortino is not None else None,
                "maxDrawdown": round(max_drawdown, 4)
            }

        returns = FundReturns(
            return_1y=raw_details.get("return_1y") if raw_details.get("return_1y") is not None else _compute_cagr(close_series, 1),
            return_3y=raw_details.get("return_3y") if raw_details.get("return_3y") is not None else _compute_cagr(close_series, 3),
            return_5y=raw_details.get("return_5y") if raw_details.get("return_5y") is not None else _compute_cagr(close_series, 5)
        )

        calc_risk = _compute_risk(close_series)
        risk_metrics = RiskMetrics(
            stdDev=raw_details.get("volatility_1y") if raw_details.get("volatility_1y") is not None else calc_risk.get("stdDev"),
            sharpeRatio=raw_details.get("sharpe_ratio") if raw_details.get("sharpe_ratio") is not None else calc_risk.get("sharpeRatio"),
            sortinoRatio=calc_risk.get("sortinoRatio"),
            maxDrawdown=(raw_details.get("max_drawdown_1y") / 100) if raw_details.get("max_drawdown_1y") is not None else calc_risk.get("maxDrawdown"),
            alpha_vs_nifty=raw_details.get("alpha"),
            beta=raw_details.get("beta")
        )

        raw_details["holdings"] = holdings
        raw_details["sector_allocation"] = sorted_sectors

        details = FundDetails(**raw_details)
        
        summary = FundService.get_nav_history_summary(scheme_code)
        nav_points_count = int(summary.get("count") or 0)
        
        data_quality = FundDataQuality(
            nav_points_count=nav_points_count,
            first_nav_date=summary.get("first_nav_date"),
            last_nav_date=summary.get("last_nav_date"),
            is_stale=nav_points_count < 10,
            warning="Insufficient historical data" if nav_points_count < 10 else None
        )

        return FundProfileResponse(
            details=details,
            returns=returns,
            risk_metrics=risk_metrics,
            nav_history=nav_points,
            data_quality=data_quality
        )
