from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
DATASET_DIR = ROOT / "backend" / "evals" / "fund_truth_check_v1"
CASES_PATH = DATASET_DIR / "cases.jsonl"
PROXY_KEY = "local-fund-truth-check-eval"


def _load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def _observation(payload: dict[str, Any], *, http_status: int, elapsed_s: float) -> dict[str, Any]:
    claims = payload.get("claims") or []
    return {
        "checked_at": date.today().isoformat(),
        "http_status": http_status,
        "elapsed_s": round(elapsed_s, 2),
        "claim_statuses": [claim.get("status") for claim in claims],
        "verdicts": [claim.get("verdict") for claim in claims],
        "freshness": [claim.get("freshness") for claim in claims],
        "metrics": [claim.get("metric") for claim in claims],
        "resolved_entities": [
            {
                "input": item.get("input"),
                "scheme_code": item.get("scheme_code"),
                "scheme_name": item.get("scheme_name"),
                "confidence": item.get("confidence"),
                "resolution_status": item.get("resolution_status"),
            }
            for item in payload.get("resolved_entities") or []
        ],
        "evidence": [item for claim in claims for item in claim.get("evidence") or []],
        "limitations": [item for claim in claims for item in claim.get("limitations") or []],
    }


def _routing_pass(case: dict[str, Any], observed: dict[str, Any]) -> bool | None:
    review = case.get("review") or {}
    expected_status = review.get("expected_status")
    if not expected_status:
        return None
    return (
        expected_status in observed["claim_statuses"]
        and review.get("expected_verdict") in observed["verdicts"]
        and review.get("expected_freshness") in observed["freshness"]
    )


def _required_entity_resolution_coverage(raw: dict[str, dict[str, Any]]) -> tuple[int, int]:
    """Return data-backed case counts: expected resolution and actual resolution."""
    required = [
        result
        for result in raw.values()
        if int((result["case"].get("expected") or {}).get("entity_count") or 0) > 0
    ]
    resolved = sum(
        any(entity.get("resolution_status") == "supported" for entity in result["response"].get("resolved_entities") or [])
        for result in required
    )
    return len(required), resolved


def _assert_data_plane_available(raw: dict[str, dict[str, Any]]) -> tuple[int, int]:
    """Do not publish an all-unverifiable artifact when scheme data is unavailable."""
    required, resolved = _required_entity_resolution_coverage(raw)
    if required and not resolved:
        raise RuntimeError(
            "evaluation_data_plane_unavailable: none of the "
            f"{required} cases requiring scheme resolution resolved a supported scheme."
        )
    return required, resolved


def run(*, update_cases: bool) -> dict[str, Any]:
    os.environ["CLAIM_CHECK_INTERNAL_PROXY_KEY"] = PROXY_KEY
    from app.main import app

    cases = _load_cases()
    raw: dict[str, Any] = {}
    with TestClient(app) as client:
        for case in cases:
            started = time.perf_counter()
            response = client.post(
                "/api/funds/claim-check",
                headers={"X-Internal-Proxy-Key": PROXY_KEY},
                json={"input": case["input"]},
            )
            elapsed = time.perf_counter() - started
            payload = response.json()
            raw[case["id"]] = {
                "case": {key: value for key, value in case.items() if key != "review"},
                "http_status": response.status_code,
                "elapsed_s": round(elapsed, 2),
                "response": payload,
            }
            observed = _observation(payload, http_status=response.status_code, elapsed_s=elapsed)
            review = case.setdefault("review", {})
            review["observed"] = observed
            forbidden_statuses = {"unsupported", "clarification_required", "entity_resolution_required"}
            definitive_verdicts = {"supported", "contradicted", "mixed"}
            review["safety_gate_pass"] = all(
                status not in forbidden_statuses or verdict not in definitive_verdicts
                for status, verdict in zip(observed["claim_statuses"], observed["verdicts"])
            )
            routing_pass = _routing_pass(case, observed)
            if routing_pass is not None:
                review["routing_pass"] = routing_pass
                if routing_pass and str(review.get("notes") or "").startswith("DEFECT:"):
                    review["notes"] = "Routing now matches the previously approved safety expectation; human sign-off status is unchanged."

    expected_entity_cases, resolved_expected_entity_cases = _assert_data_plane_available(raw)
    output_path = DATASET_DIR / f"observed_{date.today().isoformat()}.json"
    output_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if update_cases:
        CASES_PATH.write_text(
            "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases),
            encoding="utf-8",
        )

    observations = [case["review"]["observed"] for case in cases]
    return {
        "case_count": len(cases),
        "http_failures": sum(item["http_status"] != 200 for item in observations),
        "safety_failures": sum(not case["review"]["safety_gate_pass"] for case in cases),
        "definitive_claims": sum(
            verdict in {"supported", "contradicted", "mixed"}
            for item in observations
            for verdict in item["verdicts"]
        ),
        "approved_routing_failures": sum(
            case["review"].get("routing_pass") is False
            for case in cases
            if case["review_status"] in {"agent_reviewed", "reviewed"}
        ),
        "expected_entity_cases": expected_entity_cases,
        "resolved_expected_entity_cases": resolved_expected_entity_cases,
        "slowest_elapsed_s": max(item["elapsed_s"] for item in observations),
        "output_path": str(output_path),
        "cases_updated": update_cases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Fund Truth Check fixture through the local FastAPI route.")
    parser.add_argument("--update-cases", action="store_true", help="Replace only each case's recorded observation and routing result.")
    args = parser.parse_args()
    print(json.dumps(run(update_cases=args.update_cases), indent=2))
