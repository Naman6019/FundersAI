from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ml.review_priority_model import train_review_priority_model


def _rows(count: int) -> list[dict]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        requires_reparse = index % 2 == 0
        created = start + timedelta(days=index)
        rows.append(
            {
                "source_document_id": f"doc-{index}",
                "amc_code": ("hdfc", "axis", "sbi", "icici")[index % 4],
                "report_month": "2026-01-01",
                "validation_issues": ["parse_exception"] if requires_reparse else ["factsheet_fields_not_extracted"],
                "confidence_score": 35 if requires_reparse else 92,
                "parser_version": "fixture-v1",
                "status": "reparse_requested" if requires_reparse else ("approved" if index % 3 else "skipped"),
                "source_url": f"https://example.invalid/document-{index}.pdf",
                "created_at": created.isoformat(),
                "updated_at": (created + timedelta(days=2)).isoformat(),
            }
        )
    return rows


def test_training_refuses_insufficient_labels() -> None:
    result = train_review_priority_model(_rows(20), minimum_samples=50, minimum_class_samples=10)
    assert result["status"] == "insufficient_labels"
    assert result["reason"] == "minimum_samples"
    assert result["samples"] == 20


def test_training_uses_chronological_split_and_compares_rule_baseline() -> None:
    result = train_review_priority_model(_rows(80), minimum_samples=50, minimum_class_samples=10, review_capacity=5)
    assert result["status"] == "trained"
    assert result["split"] == "chronological_80_20"
    assert result["train_samples"] == 64
    assert result["test_samples"] == 16
    assert result["metrics"]["average_precision"] == 1.0
    assert "precision_at_capacity" in result["rule_baseline_metrics"]
