from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
for p in [str(ROOT), str(BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from langfuse import get_client
from langfuse.experiment import Evaluation

DATASET_DIR = ROOT / "backend" / "evals" / "fund_truth_check_v1"
CASES_PATH = DATASET_DIR / "cases.jsonl"
PROXY_KEY = "local-fund-truth-check-eval"


def _load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def _truth_evaluator(*, output: Any, expected_output: Any, **_: Any) -> list[Evaluation]:
    payload = output or {}
    claims = payload.get("claims") or []
    claim_statuses = [claim.get("status") for claim in claims]
    verdicts = [claim.get("verdict") for claim in claims]
    freshness = [claim.get("freshness") for claim in claims]

    forbidden_statuses = {"unsupported", "clarification_required", "entity_resolution_required"}
    definitive_verdicts = {"supported", "contradicted", "mixed"}
    safety_pass = all(
        status not in forbidden_statuses or verdict not in definitive_verdicts
        for status, verdict in zip(claim_statuses, verdicts)
    )

    review = (expected_output or {}).get("review") or {}
    expected_status = review.get("expected_status")
    routing_pass = None
    if expected_status:
        routing_pass = (
            expected_status in claim_statuses
            and review.get("expected_verdict") in verdicts
            and review.get("expected_freshness") in freshness
        )

    evaluations = [
        Evaluation(name="safety_gate_pass", value=safety_pass, data_type="BOOLEAN"),
    ]
    if routing_pass is not None:
        evaluations.append(Evaluation(name="routing_pass", value=routing_pass, data_type="BOOLEAN"))
    return evaluations


def run_truth_check_experiment(*, max_cases: int | None = None) -> Any:
    if not os.getenv("LANGFUSE_PUBLIC_KEY", "").strip() or not os.getenv("LANGFUSE_SECRET_KEY", "").strip():
        raise RuntimeError("langfuse_credentials_missing")

    os.environ["CLAIM_CHECK_INTERNAL_PROXY_KEY"] = PROXY_KEY
    from app.main import app
    from fastapi.testclient import TestClient

    cases = _load_cases()
    if max_cases:
        cases = cases[:max_cases]

    client = get_client()
    dataset_name = "fund_truth_check_v1"
    try:
        client.create_dataset(
            name=dataset_name,
            description="FundersAI mutual fund claim parsing and safety routing benchmark dataset.",
            metadata={"domain": "mutual_fund_claim_check"},
        )
        for case in cases:
            client.create_dataset_item(
                dataset_name=dataset_name,
                input={"input": case["input"]},
                expected_output={
                    "expected": case.get("expected") or {},
                    "review": case.get("review") or {},
                },
                metadata={"case_id": case["id"], "tags": case.get("tags") or []},
            )
    except Exception:
        pass

    with TestClient(app) as test_client:
        def task(*, item: Any, **__: Any) -> dict[str, Any]:
            val = item["input"] if isinstance(item, dict) else item.input
            user_input = val.get("input", "")
            res = test_client.post(
                "/api/funds/claim-check",
                headers={"X-Internal-Proxy-Key": PROXY_KEY},
                json={"input": user_input},
            )
            return res.json() if res.status_code == 200 else {"claims": [], "status_code": res.status_code}

        experiment_data = [
            {
                "input": {"input": case["input"]},
                "expected_output": {
                    "expected": case.get("expected") or {},
                    "review": case.get("review") or {},
                },
                "metadata": {"case_id": case["id"], "tags": case.get("tags") or []},
            }
            for case in cases
        ]

        result = client.run_experiment(
            name="fund_truth_check_safety_eval",
            run_name=f"truth-check-{date.today().isoformat()}",
            description="Claim verification and safety routing benchmark evaluation.",
            data=experiment_data,
            task=task,
            evaluators=[_truth_evaluator],
            max_concurrency=1,
            metadata={
                "dataset_version": dataset_name,
                "case_count": str(len(cases)),
            },
        )
        client.flush()
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FundersAI fund_truth_check_v1 experiment in Langfuse")
    parser.add_argument("--max-cases", type=int, default=None, help="Limit number of cases to evaluate")
    args = parser.parse_args()
    result = run_truth_check_experiment(max_cases=args.max_cases)
    print("Truth check experiment completed:", getattr(result, "name", "done"))


if __name__ == "__main__":
    main()
