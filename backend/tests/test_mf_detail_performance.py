from __future__ import annotations

import asyncio
from threading import Event
from types import SimpleNamespace

from fastapi import BackgroundTasks


class _Dumpable(SimpleNamespace):
    def model_dump(self, **_kwargs):
        return dict(self.__dict__)


def test_mf_detail_parallelizes_profile_and_freshness_and_skips_benchmark(monkeypatch):
    from app.services import chat_service as main

    profile_started = Event()
    freshness_started = Event()
    profile = SimpleNamespace(
        details=_Dumpable(aum=1000, scheme_code="101", scheme_name="Fund A"),
        returns=_Dumpable(return_1y=10.0, return_3y=12.0, return_5y=11.0),
        risk_metrics=_Dumpable(
            std_dev=0.1,
            sharpe_ratio=1.1,
            sortino_ratio=1.2,
            max_drawdown=0.08,
            alpha_vs_nifty=2.0,
            beta=0.9,
        ),
        nav_history=[],
        full_nav_history=[],
        data_quality=_Dumpable(
            nav_points_count=2200,
            first_nav_date="2020-01-01",
            last_nav_date="2026-07-24",
            is_stale=False,
            warning=None,
        ),
    )

    def fake_profile(_scheme_code):
        profile_started.set()
        assert freshness_started.wait(1)
        return profile

    def fake_freshness(_scheme_code):
        freshness_started.set()
        assert profile_started.wait(1)
        return {
            "cache_status": "hit",
            "stale": False,
            "fetched_at": "2026-07-25T00:00:00+00:00",
            "expires_at": "2026-07-26T00:00:00+00:00",
            "source": "mfapi",
        }

    async def benchmark_should_not_load(*_args, **_kwargs):
        raise AssertionError("benchmark loaded despite precomputed alpha and beta")

    monkeypatch.setattr(main, "get_mf_repository", lambda: object())
    monkeypatch.setattr(main.FundService, "get_mutual_fund_profile", fake_profile)
    monkeypatch.setattr(main, "get_nav_cache_summary", fake_freshness)
    monkeypatch.setattr(main, "get_nifty_history_df", benchmark_should_not_load)

    result = asyncio.run(main.get_mutual_fund_details(101, BackgroundTasks()))

    assert result["riskMetrics"]["alpha_vs_nifty"] == 2.0
    assert result["riskMetrics"]["beta"] == 0.9
    assert result["historyCoverage"]["supports"] == {"1Y": True, "3Y": True, "5Y": True}
