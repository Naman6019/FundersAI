from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

try:
    from app.repositories.admin_ops_repository import AdminOpsRepository
    from ml.review_priority_model import CATEGORICAL_FEATURES, NUMERIC_FEATURES, feature_frame
except ModuleNotFoundError:
    from backend.app.repositories.admin_ops_repository import AdminOpsRepository
    from backend.ml.review_priority_model import CATEGORICAL_FEATURES, NUMERIC_FEATURES, feature_frame

logger = logging.getLogger(__name__)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _numeric_shift(reference, current) -> float:
    ref = reference.dropna().astype(float)
    cur = current.dropna().astype(float)
    if ref.empty or cur.empty:
        return 0.0
    scale = float(ref.std(ddof=0))
    if scale < 1e-9:
        return 0.0 if abs(float(cur.mean()) - float(ref.mean())) < 1e-9 else 1.0
    return abs(float(cur.mean()) - float(ref.mean())) / scale


def _categorical_shift(reference, current) -> float:
    ref = reference.fillna("unknown").astype(str).value_counts(normalize=True)
    cur = current.fillna("unknown").astype(str).value_counts(normalize=True)
    categories = set(ref.index) | set(cur.index)
    return 0.5 * sum(abs(float(ref.get(value, 0.0)) - float(cur.get(value, 0.0))) for value in categories)


def build_drift_report(
    reference_rows: list[dict[str, Any]],
    current_rows: list[dict[str, Any]],
    *,
    numeric_threshold: float = 1.0,
    categorical_threshold: float = 0.25,
) -> dict[str, Any]:
    reference = feature_frame(reference_rows)
    current = feature_frame(current_rows)
    if reference.empty or current.empty:
        return {"status": "insufficient_data", "reference_rows": len(reference), "current_rows": len(current), "features": {}}
    metrics: dict[str, dict[str, Any]] = {}
    for name in NUMERIC_FEATURES:
        score = round(_numeric_shift(reference[name], current[name]), 4)
        metrics[name] = {"kind": "standardized_mean_shift", "score": score, "threshold": numeric_threshold, "drifted": score > numeric_threshold}
    for name in CATEGORICAL_FEATURES:
        score = round(_categorical_shift(reference[name], current[name]), 4)
        metrics[name] = {"kind": "total_variation_distance", "score": score, "threshold": categorical_threshold, "drifted": score > categorical_threshold}
    drifted = sorted(name for name, value in metrics.items() if value["drifted"])
    return {
        "status": "alert" if drifted else "ok",
        "reference_rows": len(reference),
        "current_rows": len(current),
        "drifted_features": drifted,
        "features": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare current review features with a fixed reviewer-export reference")
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--current", type=Path, help="Optional current JSONL. Without it, read review outcomes from Supabase.")
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reference_rows = _load_jsonl(args.reference)
    if args.current:
        current_rows = _load_jsonl(args.current)
    else:
        repository = AdminOpsRepository()
        if not repository:
            raise SystemExit("supabase_unavailable")
        current_rows = repository.list_reviewed_review_items(limit=max(1, args.limit))
    report = build_drift_report(reference_rows, current_rows)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    logger.warning("event=review_feature_drift status=%s drifted_features=%s", report["status"], len(report.get("drifted_features") or []))
    print(rendered)
    if report["status"] == "alert":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
