from ml.monitor_review_drift import build_drift_report


def _row(amc: str, confidence: float) -> dict:
    return {
        "amc_code": amc,
        "confidence_score": confidence,
        "validation_issues": ["holdings_not_found"],
        "parser_version": "v1",
        "source_url": "https://official.example/factsheet.pdf",
        "report_month": "2026-04",
    }


def test_feature_drift_report_is_clear_for_same_distribution() -> None:
    rows = [_row("hdfc", 0.7), _row("axis", 0.8)] * 5
    report = build_drift_report(rows, list(rows))

    assert report["status"] == "ok"
    assert report["drifted_features"] == []


def test_feature_drift_report_flags_large_numeric_and_category_shift() -> None:
    reference = [_row("hdfc", 0.8 + index / 100) for index in range(10)]
    current = [_row("new-amc", 0.1 + index / 100) for index in range(10)]
    report = build_drift_report(reference, current)

    assert report["status"] == "alert"
    assert "confidence_score" in report["drifted_features"]
    assert "amc_code" in report["drifted_features"]
