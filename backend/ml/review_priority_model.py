from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from app.services.review_priority_service import score_review_item
except ModuleNotFoundError:  # Supports repository-root module execution.
    from backend.app.services.review_priority_service import score_review_item


MODEL_VERSION = "mf_review_logistic_v1"
TARGET_NAME = "requires_reparse"
POSITIVE_STATUS = "reparse_requested"
TERMINAL_STATUSES = {"approved", "skipped"}
ISSUE_MARKERS = (
    "parse_exception",
    "raw_file_missing",
    "raw_file_unavailable",
    "holdings_not_found",
    "percent_aum_out_of_band",
    "factsheet_fields_not_extracted",
    "llm_partial_review_required",
)
NUMERIC_FEATURES = [
    "confidence_score",
    "issue_count",
    "review_age_days",
    "has_report_month",
    *[f"issue_{marker}" for marker in ISSUE_MARKERS],
]
CATEGORICAL_FEATURES = ["amc_code", "parser_version", "source_extension"]


def _timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _source_extension(value: Any) -> str:
    path = PurePosixPath(urlparse(str(value or "")).path)
    suffix = path.suffix.lower().lstrip(".")
    return suffix or "unknown"


def _feature_row(row: dict[str, Any]) -> dict[str, Any]:
    issues = [str(value).strip().lower() for value in row.get("validation_issues") or [] if str(value).strip()]
    created_at = _timestamp(row.get("created_at"))
    observed_at = _timestamp(row.get("reviewed_at")) or _timestamp(row.get("updated_at"))
    age_days = max(0.0, (observed_at - created_at).total_seconds() / 86400.0) if created_at and observed_at else 0.0
    try:
        confidence = float(row.get("confidence_score"))
    except (TypeError, ValueError):
        confidence = np.nan
    features: dict[str, Any] = {
        "confidence_score": confidence,
        "issue_count": float(len(issues)),
        "review_age_days": age_days,
        "has_report_month": float(bool(row.get("report_month"))),
        "amc_code": str(row.get("amc_code") or "unknown").strip().lower(),
        "parser_version": str(row.get("parser_version") or "unknown").strip().lower(),
        "source_extension": _source_extension(row.get("source_url")),
    }
    for marker in ISSUE_MARKERS:
        features[f"issue_{marker}"] = float(any(marker in issue for issue in issues))
    return features


def feature_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([_feature_row(row) for row in rows], columns=[*NUMERIC_FEATURES, *CATEGORICAL_FEATURES])


def _historical_rule_score(row: dict[str, Any], observed_at: datetime) -> float:
    comparable = dict(row)
    created_at = _timestamp(row.get("created_at"))
    if created_at:
        age = max(timedelta(0), observed_at - created_at)
        comparable["created_at"] = (datetime.now(timezone.utc) - age).isoformat()
    return float(score_review_item(comparable)["priority_score"])


def prepare_labelled_rows(rows: list[dict[str, Any]]) -> tuple[pd.DataFrame, np.ndarray, list[datetime], np.ndarray]:
    features: list[dict[str, Any]] = []
    labels: list[int] = []
    timestamps: list[datetime] = []
    rule_scores: list[float] = []
    for row in rows:
        status = str(row.get("status") or "").strip().lower()
        if status != POSITIVE_STATUS and status not in TERMINAL_STATUSES:
            continue
        observed_at = _timestamp(row.get("reviewed_at")) or _timestamp(row.get("updated_at"))
        if observed_at is None:
            continue
        features.append(_feature_row(row))
        labels.append(int(status == POSITIVE_STATUS))
        timestamps.append(observed_at)
        rule_scores.append(_historical_rule_score(row, observed_at))
    return (
        pd.DataFrame(features, columns=[*NUMERIC_FEATURES, *CATEGORICAL_FEATURES]),
        np.asarray(labels, dtype=int),
        timestamps,
        np.asarray(rule_scores, dtype=float),
    )


def dataset_version(rows: list[dict[str, Any]]) -> str:
    stable = [
        {
            "source_document_id": row.get("source_document_id"),
            "status": row.get("status"),
            "validation_issues": sorted(str(value) for value in row.get("validation_issues") or []),
            "confidence_score": row.get("confidence_score"),
            "parser_version": row.get("parser_version"),
            "updated_at": row.get("updated_at"),
        }
        for row in rows
    ]
    stable.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("source_document_id") or "")))
    rendered = json.dumps(stable, sort_keys=True, separators=(",", ":"), default=str)
    return f"mf_review_labels_{hashlib.sha256(rendered.encode('utf-8')).hexdigest()[:12]}"


def _build_pipeline() -> Pipeline:
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = Pipeline(
        [("imputer", SimpleImputer(strategy="most_frequent")), ("one_hot", OneHotEncoder(handle_unknown="ignore"))]
    )
    features = ColumnTransformer([("numeric", numeric, NUMERIC_FEATURES), ("categorical", categorical, CATEGORICAL_FEATURES)])
    return Pipeline(
        [
            ("features", features),
            ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)),
        ]
    )


def _ranking_metrics(labels: np.ndarray, scores: np.ndarray, capacity: int) -> dict[str, float]:
    cutoff = min(max(1, capacity), len(labels))
    selected = np.argsort(-scores)[:cutoff]
    positives = max(1, int(labels.sum()))
    true_positives = int(labels[selected].sum())
    return {
        "precision_at_capacity": round(true_positives / cutoff, 4),
        "recall_at_capacity": round(true_positives / positives, 4),
    }


def train_review_priority_model(
    rows: list[dict[str, Any]],
    *,
    minimum_samples: int = 50,
    minimum_class_samples: int = 10,
    review_capacity: int = 20,
) -> dict[str, Any]:
    version = dataset_version(rows)
    frame, labels, timestamps, rule_scores = prepare_labelled_rows(rows)
    counts = {"requires_reparse": int(labels.sum()), "terminal_decision": int((labels == 0).sum())}
    if len(labels) < minimum_samples:
        return {"status": "insufficient_labels", "reason": "minimum_samples", "dataset_version": version, "samples": len(labels), "class_counts": counts}
    if min(counts.values(), default=0) < minimum_class_samples:
        return {"status": "insufficient_labels", "reason": "minimum_class_samples", "dataset_version": version, "samples": len(labels), "class_counts": counts}

    order = np.argsort(np.asarray([value.timestamp() for value in timestamps]))
    split = max(1, min(len(order) - 1, int(len(order) * 0.8)))
    train_indexes, test_indexes = order[:split], order[split:]
    if len(set(labels[train_indexes])) < 2 or len(set(labels[test_indexes])) < 2:
        return {"status": "insufficient_labels", "reason": "time_split_class_coverage", "dataset_version": version, "samples": len(labels), "class_counts": counts}

    model = _build_pipeline()
    model.fit(frame.iloc[train_indexes], labels[train_indexes])
    probabilities = model.predict_proba(frame.iloc[test_indexes])[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    test_labels = labels[test_indexes]
    model_metrics = {
        "precision": round(precision_score(test_labels, predictions, zero_division=0), 4),
        "recall": round(recall_score(test_labels, predictions, zero_division=0), 4),
        "f1": round(f1_score(test_labels, predictions, zero_division=0), 4),
        "average_precision": round(average_precision_score(test_labels, probabilities), 4),
        "roc_auc": round(roc_auc_score(test_labels, probabilities), 4),
        **_ranking_metrics(test_labels, probabilities, review_capacity),
    }
    test_rule_scores = rule_scores[test_indexes]
    baseline_metrics = {
        "average_precision": round(average_precision_score(test_labels, test_rule_scores), 4),
        "roc_auc": round(roc_auc_score(test_labels, test_rule_scores), 4),
        **_ranking_metrics(test_labels, test_rule_scores, review_capacity),
    }
    return {
        "status": "trained",
        "model_version": MODEL_VERSION,
        "target": TARGET_NAME,
        "dataset_version": version,
        "samples": len(labels),
        "class_counts": counts,
        "train_samples": len(train_indexes),
        "test_samples": len(test_indexes),
        "split": "chronological_80_20",
        "features": [*NUMERIC_FEATURES, *CATEGORICAL_FEATURES],
        "metrics": model_metrics,
        "rule_baseline_metrics": baseline_metrics,
        "model": model,
        "test_frame": frame.iloc[test_indexes],
        "test_labels": test_labels,
        "test_probabilities": probabilities,
    }
