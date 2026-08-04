from backend.scripts.verify_mf_metric_coverage import coverage_failures


def test_metric_coverage_gate_rejects_stale_or_insufficient_output() -> None:
    coverage = {
        "supported_mapped_total": 100,
        "history_ready_count": 89,
        "supported_alpha_beta_coverage": 0.89,
        "supported_benchmark_coverage": 0.94,
        "supported_risk_coverage": 0.95,
        "benchmark_freshness": {"fresh": False},
    }

    failures = coverage_failures(
        coverage,
        history_minimum=0.90,
        alpha_beta_minimum=0.90,
        benchmark_risk_minimum=0.95,
    )

    assert failures == [
        "history_coverage_below_threshold",
        "alpha_beta_coverage_below_threshold",
        "benchmark_coverage_below_threshold",
        "benchmark_stale",
    ]
