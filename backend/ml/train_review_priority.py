from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    from app.repositories.admin_ops_repository import AdminOpsRepository
    from ml.review_priority_model import MODEL_VERSION, train_review_priority_model
except ModuleNotFoundError:  # Supports repository-root module execution.
    from backend.app.repositories.admin_ops_repository import AdminOpsRepository
    from backend.ml.review_priority_model import MODEL_VERSION, train_review_priority_model


REGISTERED_MODEL_NAME = "fundersai-review-priority"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_live_rows(limit: int) -> list[dict[str, Any]]:
    repository = AdminOpsRepository()
    if not repository:
        raise RuntimeError("supabase_unavailable")
    return repository.list_reviewed_review_items(limit=limit)


def _log_to_mlflow(result: dict[str, Any], *, register_model: bool) -> dict[str, Any]:
    os.environ.setdefault("MLFLOW_RECORD_ENV_VARS_IN_MODEL_LOGGING", "false")
    import mlflow
    import mlflow.sklearn
    from mlflow.models import infer_signature
    from mlflow.tracking import MlflowClient

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "").strip()
    if not tracking_uri:
        database_path = (Path(__file__).resolve().parents[2] / "logs" / "mlflow" / "tracking.db").resolve()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        tracking_uri = f"sqlite:///{database_path.as_posix()}"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("fundersai-review-priority")
    with mlflow.start_run(run_name=f"{MODEL_VERSION}-{result['dataset_version']}") as run:
        mlflow.log_params(
            {
                "model_version": MODEL_VERSION,
                "dataset_version": result["dataset_version"],
                "split": result["split"],
                "target": result["target"],
                "train_samples": result["train_samples"],
                "test_samples": result["test_samples"],
                "dataset_status": result["dataset_status"],
            }
        )
        mlflow.set_tag("dataset_status", result["dataset_status"])
        mlflow.log_metrics({f"model_{key}": value for key, value in result["metrics"].items()})
        mlflow.log_metrics({f"rule_{key}": value for key, value in result["rule_baseline_metrics"].items()})
        signature = infer_signature(result["test_frame"], result["test_probabilities"])
        mlflow.sklearn.log_model(
            sk_model=result["model"],
            name="model",
            signature=signature,
            input_example=result["test_frame"].head(3),
            registered_model_name=REGISTERED_MODEL_NAME if register_model else None,
            serialization_format="skops",
            skops_trusted_types=["numpy.dtype"],
        )
        run_id = run.info.run_id
    output = {"tracking_uri": tracking_uri, "run_id": run_id, "registered_model": None}
    if register_model:
        versions = MlflowClient().search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
        registered_version = max(versions, key=lambda item: int(item.version)).version
        MlflowClient().set_registered_model_alias(REGISTERED_MODEL_NAME, "candidate", registered_version)
        output.update({"registered_model": REGISTERED_MODEL_NAME, "registered_version": registered_version, "alias": "candidate"})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the internal parser-review priority model when labels are sufficient")
    parser.add_argument("--input", type=Path, help="Optional exported JSONL. Without it, read reviewed rows from Supabase.")
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--minimum-samples", type=int, default=50)
    parser.add_argument("--minimum-class-samples", type=int, default=10)
    parser.add_argument("--review-capacity", type=int, default=20)
    parser.add_argument("--mlflow", action="store_true", help="Log only a successfully trained model and metrics.")
    parser.add_argument("--register-model", action="store_true", help="Register the model as candidate; requires verified reviewer data.")
    parser.add_argument("--verified-reviewer-export", action="store_true", help="Confirm that --input contains reviewer-verified production outcomes.")
    args = parser.parse_args()
    rows = _load_jsonl(args.input) if args.input else _load_live_rows(args.limit)
    result = train_review_priority_model(
        rows,
        minimum_samples=max(10, args.minimum_samples),
        minimum_class_samples=max(2, args.minimum_class_samples),
        review_capacity=max(1, args.review_capacity),
    )
    result["dataset_status"] = "verified_reviewer_outcomes" if (not args.input or args.verified_reviewer_export) else "unverified_export"
    if args.register_model and result["dataset_status"] != "verified_reviewer_outcomes":
        raise SystemExit("model_registration_requires_verified_reviewer_outcomes")
    if result["status"] == "trained" and (args.mlflow or args.register_model):
        result["mlflow"] = _log_to_mlflow(result, register_model=args.register_model)
    printable = {key: value for key, value in result.items() if key not in {"model", "test_frame", "test_labels", "test_probabilities"}}
    print(json.dumps(printable, indent=2, default=str, sort_keys=True))
    if result["status"] != "trained":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
