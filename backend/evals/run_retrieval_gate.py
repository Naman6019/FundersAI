"""Close the evaluation loop: compare a fresh retrieval run against a committed baseline.

This is the gate, not another experiment. The evaluation runner records what a variant
scores; this module decides whether that score is allowed to ship by comparing it to a
baseline a human explicitly promoted with ``--update-baseline``.

Loop:
  run variant -> compare to baseline -> fail on regression -> human promotes a new baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
for _path in (str(REPO_ROOT), str(BACKEND_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from evals.run_retrieval_evaluation import DEFAULT_DATASET_DIR, run_evaluation

DEFAULT_BASELINE = BACKEND_DIR / "evals" / "gates" / "retrieval_baseline.json"
DEFAULT_VARIANT = "lexical_rerank_v2"
DEFAULT_LIMIT = 5

# Metrics that may never fall below the promoted baseline.
REGRESSION_METRICS = (
    "recall_at_k",
    "hit_rate_at_k",
    "all_relevant_rate_at_k",
    "mean_reciprocal_rank",
    "abstention_accuracy",
    "grounded_answer_rate",
    "passed_cases",
)


def load_baseline(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"missing baseline at {path}; create it with --update-baseline after a verified run"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _compare_metric(metric: str, baseline: dict[str, Any], current: dict[str, Any], tolerance: float) -> dict[str, Any]:
    base = baseline.get(metric)
    now = current.get(metric)
    if base is None and now is None:
        return {"metric": metric, "baseline": base, "current": now, "status": "absent"}
    if base is None:
        return {"metric": metric, "baseline": base, "current": now, "status": "new"}
    if now is None:
        return {"metric": metric, "baseline": base, "current": now, "status": "regressed", "delta": None}
    delta = round(float(now) - float(base), 4)
    status = "ok" if delta >= -abs(tolerance) else "regressed"
    return {"metric": metric, "baseline": base, "current": now, "delta": delta, "status": status}


def compare_reports(
    current: dict[str, Any],
    baseline: dict[str, Any],
    *,
    tolerance: float,
    allow_dataset_change: bool,
) -> dict[str, Any]:
    findings = [_compare_metric(metric, baseline, current, tolerance) for metric in REGRESSION_METRICS]

    dataset_changed = str(current.get("dataset_version")) != str(baseline.get("dataset_version"))
    configuration_changed = current.get("configuration") != baseline.get("configuration")

    regressions = [item for item in findings if item["status"] == "regressed"]
    failed = bool(regressions) or (dataset_changed and not allow_dataset_change)

    return {
        "gate": "fund_research_retrieval",
        "passed": not failed,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "variant": (current.get("configuration") or {}).get("variant"),
        "dataset_version": current.get("dataset_version"),
        "baseline_dataset_version": baseline.get("dataset_version"),
        "dataset_changed": dataset_changed,
        "configuration_changed": configuration_changed,
        "tolerance": tolerance,
        "metrics": findings,
        "regressions": regressions,
        "current": {
            key: current.get(key)
            for key in ("recall_at_k", "hit_rate_at_k", "all_relevant_rate_at_k", "mean_reciprocal_rank",
                        "abstention_accuracy", "grounded_answer_rate", "passed_cases", "cases")
        },
        "baseline": {
            key: baseline.get(key)
            for key in ("recall_at_k", "hit_rate_at_k", "all_relevant_rate_at_k", "mean_reciprocal_rank",
                        "abstention_accuracy", "grounded_answer_rate", "passed_cases", "cases")
        },
    }


def run_gate(
    *,
    baseline_path: Path = DEFAULT_BASELINE,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    variant: str = DEFAULT_VARIANT,
    limit: int = DEFAULT_LIMIT,
    tolerance: float = 0.0,
    allow_dataset_change: bool = False,
) -> dict[str, Any]:
    current = run_evaluation(dataset_dir=dataset_dir, limit=limit, variant=variant)
    baseline = load_baseline(baseline_path)
    return compare_reports(
        current,
        baseline,
        tolerance=tolerance,
        allow_dataset_change=allow_dataset_change,
    )


def write_baseline(
    *,
    baseline_path: Path = DEFAULT_BASELINE,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    variant: str = DEFAULT_VARIANT,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    current = run_evaluation(dataset_dir=dataset_dir, limit=limit, variant=variant)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return current


def _render(report: dict[str, Any]) -> str:
    lines = [
        f"gate={report['gate']} variant={report['variant']} passed={report['passed']}",
        f"dataset current={report['dataset_version']} baseline={report['baseline_dataset_version']}",
    ]
    for item in report["metrics"]:
        marker = {"ok": "PASS", "new": "NEW ", "absent": "----", "regressed": "FAIL"}[item["status"]]
        lines.append(
            f"  [{marker}] {item['metric']}: baseline={item['baseline']} current={item['current']} "
            f"delta={item.get('delta')}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail when retrieval quality drops below the promoted baseline")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--variant", default=DEFAULT_VARIANT)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--tolerance", type=float, default=0.0, help="Allowed per-metric drop before failing")
    parser.add_argument("--allow-dataset-change", action="store_true", help="Do not fail solely on a dataset version change")
    parser.add_argument("--update-baseline", action="store_true", help="Promote the current run as the new baseline")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    limit = max(1, min(args.limit, 10))

    if args.update_baseline:
        current = write_baseline(
            baseline_path=args.baseline,
            dataset_dir=args.dataset_dir,
            variant=args.variant,
            limit=limit,
        )
        print(f"promoted baseline {args.baseline} ({args.variant}, {current.get('passed_cases')}/{current.get('cases')})")
        return

    report = run_gate(
        baseline_path=args.baseline,
        dataset_dir=args.dataset_dir,
        variant=args.variant,
        limit=limit,
        tolerance=args.tolerance,
        allow_dataset_change=args.allow_dataset_change,
    )
    rendered = _render(report)
    print(rendered)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
