from __future__ import annotations

from dataclasses import dataclass

from app.mf_ingestion.constants import ReportMonthWindow


@dataclass(frozen=True)
class MetricsValidationResult:
    total_percent_aum: float
    is_within_expected_band: bool


def validate_percent_aum_total(total_percent_aum: float, window: ReportMonthWindow | None = None) -> MetricsValidationResult:
    rule_window = window or ReportMonthWindow()
    return MetricsValidationResult(
        total_percent_aum=total_percent_aum,
        is_within_expected_band=rule_window.lower_bound_pct <= total_percent_aum <= rule_window.upper_bound_pct,
    )
