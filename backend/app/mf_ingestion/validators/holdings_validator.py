from __future__ import annotations

from dataclasses import dataclass

from app.mf_ingestion.constants import (
    DEFAULT_SCHEME_MATCH_THRESHOLD,
    VALIDATION_STATUS_INVALID,
    VALIDATION_STATUS_REVIEW,
    VALIDATION_STATUS_VALID,
)
from app.mf_ingestion.validators.metrics_validator import validate_percent_aum_total


@dataclass(frozen=True)
class HoldingValidationResult:
    validation_status: str
    issues: list[str]



def validate_holdings(
    rows: list[dict],
    scheme_match_confidence: float,
    report_month_present: bool,
) -> HoldingValidationResult:
    issues: list[str] = []

    if not report_month_present:
        issues.append("report_month_missing")

    if scheme_match_confidence < DEFAULT_SCHEME_MATCH_THRESHOLD:
        issues.append("scheme_match_low_confidence")

    total_percent = 0.0
    for row in rows:
        name = str(row.get("instrument_name") or "").strip()
        if not name:
            issues.append("instrument_name_missing")

        isin = str(row.get("isin") or "").strip()
        if isin and len(isin) != 12:
            issues.append("isin_length_invalid")

        percent = row.get("percent_aum")
        if percent is not None:
            try:
                total_percent += float(percent)
            except (TypeError, ValueError):
                issues.append("percent_aum_invalid")

    metric_result = validate_percent_aum_total(total_percent)
    if not metric_result.is_within_expected_band:
        issues.append("percent_aum_out_of_band")

    if not rows:
        issues.append("holdings_empty")

    unique_issues = sorted(set(issues))
    if not unique_issues:
        status = VALIDATION_STATUS_VALID
    elif "report_month_missing" in unique_issues or "holdings_empty" in unique_issues:
        status = VALIDATION_STATUS_INVALID
    else:
        status = VALIDATION_STATUS_REVIEW

    return HoldingValidationResult(validation_status=status, issues=unique_issues)
