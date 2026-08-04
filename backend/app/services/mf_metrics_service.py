from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import sqrt
from typing import Any


NAV_METRIC_SNAPSHOT_VERSION = "mf_nav_metrics_v3"


@dataclass
class NavPoint:
    nav_date: date
    nav: float


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(raw[:11], fmt).date()
        except ValueError:
            continue
    return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def normalize_nav_history(rows: list[dict[str, Any]]) -> list[NavPoint]:
    points: list[NavPoint] = []
    for row in rows:
        nav_date = _parse_date(row.get("nav_date") or row.get("date"))
        nav = _parse_float(
            row.get("nav")
            if row.get("nav") is not None
            else row.get("close")
            if row.get("close") is not None
            else row.get("value")
        )
        if nav_date and nav is not None and nav > 0:
            points.append(NavPoint(nav_date=nav_date, nav=nav))
    points.sort(key=lambda item: item.nav_date)
    return points


def _find_nav_on_or_before(points: list[NavPoint], target: date) -> float | None:
    eligible = [item.nav for item in points if item.nav_date <= target]
    return eligible[-1] if eligible else None


def _pct_return(points: list[NavPoint], period_days: int) -> float | None:
    if not points:
        return None
    latest = points[-1]
    past = _find_nav_on_or_before(points, latest.nav_date - timedelta(days=period_days))
    if past is None or past == 0:
        return None
    return ((latest.nav - past) / past) * 100


def _cagr(points: list[NavPoint], years: int) -> float | None:
    if not points:
        return None
    latest = points[-1]
    past_target = latest.nav_date - timedelta(days=365 * years)
    past = _find_nav_on_or_before(points, past_target)
    if past is None or past <= 0:
        return None
    return (((latest.nav / past) ** (1 / years)) - 1) * 100


def _daily_returns(points: list[NavPoint], lookback_days: int) -> list[float]:
    if len(points) < 2:
        return []
    cutoff = points[-1].nav_date - timedelta(days=lookback_days)
    filtered = [item for item in points if item.nav_date >= cutoff]
    returns: list[float] = []
    for prev, curr in zip(filtered[:-1], filtered[1:]):
        if prev.nav <= 0:
            continue
        returns.append((curr.nav / prev.nav) - 1)
    return returns


def _daily_returns_by_date(points: list[NavPoint], lookback_days: int) -> dict[date, float]:
    if len(points) < 2:
        return {}
    cutoff = points[-1].nav_date - timedelta(days=lookback_days)
    returns: dict[date, float] = {}
    for prev, curr in zip(points[:-1], points[1:]):
        if curr.nav_date < cutoff or prev.nav <= 0:
            continue
        returns[curr.nav_date] = (curr.nav / prev.nav) - 1
    return returns


def _volatility_1y(points: list[NavPoint]) -> float | None:
    rets = _daily_returns(points, 365)
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    variance = sum((r - mean) ** 2 for r in rets) / len(rets)
    return sqrt(variance) * sqrt(252) * 100


def _max_drawdown_1y(points: list[NavPoint]) -> float | None:
    if not points:
        return None
    cutoff = points[-1].nav_date - timedelta(days=365)
    filtered = [item for item in points if item.nav_date >= cutoff]
    if not filtered:
        return None
    peak = filtered[0].nav
    max_drawdown = 0.0
    for item in filtered:
        peak = max(peak, item.nav)
        if peak <= 0:
            continue
        drawdown = (peak - item.nav) / peak
        max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown * 100


def compute_nav_metrics(
    rows: list[dict[str, Any]],
    benchmark_daily_returns: list[float] | None = None,
    risk_free_rate: float | None = None,
    *,
    benchmark_rows: list[dict[str, Any]] | None = None,
) -> dict[str, float | None]:
    metrics, _ = compute_nav_metrics_with_diagnostics(
        rows,
        benchmark_daily_returns=benchmark_daily_returns,
        risk_free_rate=risk_free_rate,
        benchmark_rows=benchmark_rows,
    )
    return metrics


def compute_nav_metrics_with_diagnostics(
    rows: list[dict[str, Any]],
    benchmark_daily_returns: list[float] | None = None,
    risk_free_rate: float | None = None,
    *,
    benchmark_rows: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float | None], dict[str, Any]]:
    points = normalize_nav_history(rows)

    metrics: dict[str, float | None] = {
        "return_1m": _pct_return(points, 30),
        "return_3m": _pct_return(points, 90),
        "return_6m": _pct_return(points, 182),
        "return_1y": _cagr(points, 1),
        "return_3y": _cagr(points, 3),
        "return_5y": _cagr(points, 5),
        "volatility_1y": _volatility_1y(points),
        "max_drawdown_1y": _max_drawdown_1y(points),
        "alpha": None,
        "beta": None,
        "sharpe_ratio": None,
    }

    nav_returns = _daily_returns(points, 365)
    if risk_free_rate is not None and len(nav_returns) >= 30:
        nav_mean = sum(nav_returns) / len(nav_returns)
        annualized_std = sqrt(sum((value - nav_mean) ** 2 for value in nav_returns) / len(nav_returns)) * sqrt(252)
        if annualized_std > 0:
            metrics["sharpe_ratio"] = ((nav_mean * 252) - risk_free_rate) / annualized_std

    nav_sample: list[float] = []
    bench_sample: list[float] = []
    benchmark_points: list[NavPoint] = []
    if benchmark_rows:
        benchmark_points = normalize_nav_history(benchmark_rows)
        nav_by_date = _daily_returns_by_date(points, 365)
        benchmark_by_date = _daily_returns_by_date(benchmark_points, 365)
        shared_dates = sorted(set(nav_by_date).intersection(benchmark_by_date))
        nav_sample = [nav_by_date[item] for item in shared_dates]
        bench_sample = [benchmark_by_date[item] for item in shared_dates]
    elif benchmark_daily_returns:
        paired = min(len(nav_returns), len(benchmark_daily_returns))
        nav_sample = nav_returns[-paired:]
        bench_sample = benchmark_daily_returns[-paired:]

    # Alpha and beta require at least 30 aligned daily returns.
    if risk_free_rate is not None and len(nav_sample) >= 30:
        paired = min(len(nav_sample), len(bench_sample))
        if paired >= 30:
            nav_sample = nav_sample[-paired:]
            bench_sample = bench_sample[-paired:]
            bench_mean = sum(bench_sample) / paired
            nav_mean = sum(nav_sample) / paired
            bench_var = sum((r - bench_mean) ** 2 for r in bench_sample) / paired
            if bench_var > 0:
                covariance = sum((a - nav_mean) * (b - bench_mean) for a, b in zip(nav_sample, bench_sample)) / paired
                beta = covariance / bench_var
                ann_nav = nav_mean * 252
                ann_bench = bench_mean * 252
                alpha = ann_nav - (risk_free_rate + beta * (ann_bench - risk_free_rate))
                metrics["beta"] = beta
                metrics["alpha"] = alpha * 100

    if not points:
        calculation_status = "fund_history_unavailable"
    elif len(nav_sample) < 30:
        calculation_status = (
            "benchmark_unavailable"
            if not benchmark_points and not benchmark_daily_returns
            else "insufficient_overlap"
        )
    elif metrics["alpha"] is None or metrics["beta"] is None:
        calculation_status = "benchmark_zero_variance"
    else:
        calculation_status = "computed"

    diagnostics = {
        "calculation_status": calculation_status,
        "fund_start_date": points[0].nav_date.isoformat() if points else None,
        "fund_end_date": points[-1].nav_date.isoformat() if points else None,
        "benchmark_start_date": benchmark_points[0].nav_date.isoformat() if benchmark_points else None,
        "benchmark_end_date": benchmark_points[-1].nav_date.isoformat() if benchmark_points else None,
        "overlap_points": min(len(nav_sample), len(bench_sample)),
        "minimum_overlap_points": 30,
    }
    return metrics, diagnostics
