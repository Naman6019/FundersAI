from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("PREFECT_HOME", str(Path(__file__).resolve().parents[2] / "logs" / "prefect"))

from prefect import flow, task

try:
    from evals.run_retrieval_evaluation import run_evaluation
    from orchestration.job_runner import run_module
    from orchestration.pipeline_plan import SUPPORTED_AMCS, build_evidence_pipeline_plan, normalize_amcs
except ModuleNotFoundError:  # Supports `python -m backend.orchestration...` from the repository root.
    from backend.evals.run_retrieval_evaluation import run_evaluation
    from backend.orchestration.job_runner import run_module
    from backend.orchestration.pipeline_plan import SUPPORTED_AMCS, build_evidence_pipeline_plan, normalize_amcs


FLOW_VERSION = "fund_research_evidence_v1"
logger = logging.getLogger(__name__)


@task(name="ingest-official-amc-documents", retries=1, retry_delay_seconds=60)
def ingest_documents(amc: str, max_documents: int) -> dict[str, Any]:
    return run_module(
        "app.mf_ingestion.jobs.ingest_latest_amc_docs",
        ["--amc", amc, "--all-document-types", "--max-documents", str(max_documents), "--strict"],
        timeout_seconds=2_400,
    )


@task(name="parse-pending-amc-documents", retries=1, retry_delay_seconds=60)
def parse_documents(amc: str, limit: int, round_number: int) -> dict[str, Any]:
    result = run_module(
        "app.mf_ingestion.jobs.parse_pending_documents",
        ["--amc", amc, "--limit", str(limit), "--strict"],
        timeout_seconds=5_100,
    )
    return {**result, "round": round_number, "amc": amc}


@task(name="index-parsed-official-documents", retries=1, retry_delay_seconds=60)
def index_documents(limit: int) -> dict[str, Any]:
    return run_module(
        "app.mf_ingestion.jobs.index_parsed_documents",
        ["--limit", str(limit)],
        timeout_seconds=2_400,
    )


@task(name="evaluate-official-document-retrieval")
def evaluate_seed_dataset(limit: int) -> dict[str, Any]:
    return run_evaluation(limit=limit)


@flow(name="fund-research-evidence-pipeline", version=FLOW_VERSION, log_prints=True)
def fund_research_evidence_flow(
    amcs: list[str] | None = None,
    *,
    parse_only: bool = False,
    max_documents: int = 1,
    parse_limit: int = 100,
    parse_rounds: int = 1,
    index_limit: int = 10,
    evaluation_limit: int = 5,
    dry_run: bool = True,
) -> dict[str, Any]:
    selected_amcs = normalize_amcs(amcs or list(SUPPORTED_AMCS))
    plan = build_evidence_pipeline_plan(
        amcs=selected_amcs,
        parse_only=parse_only,
        max_documents=max_documents,
        parse_limit=parse_limit,
        parse_rounds=parse_rounds,
        index_limit=index_limit,
        evaluation_limit=evaluation_limit,
    )
    if dry_run:
        return {"status": "dry_run", "flow_version": FLOW_VERSION, "plan": plan}

    stages: list[dict[str, Any]] = []
    for amc in selected_amcs:
        if not parse_only:
            stages.append({"stage": "ingest", "amc": amc, "result": ingest_documents(amc, max(1, max_documents))})
        for round_number in range(1, max(1, parse_rounds) + 1):
            stages.append(
                {
                    "stage": "parse",
                    "amc": amc,
                    "round": round_number,
                    "result": parse_documents(amc, max(1, parse_limit), round_number),
                }
            )
    stages.append({"stage": "index", "result": index_documents(max(1, index_limit))})
    evaluation = evaluate_seed_dataset(max(1, min(evaluation_limit, 10)))
    stages.append({"stage": "evaluate", "result": evaluation})
    return {"status": "completed", "flow_version": FLOW_VERSION, "stages": stages, "evaluation": evaluation}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or preview the Fund Research Evidence Prefect flow")
    parser.add_argument("--amcs", default=",".join(SUPPORTED_AMCS))
    parser.add_argument("--parse-only", action="store_true")
    parser.add_argument("--max-documents", type=int, default=1)
    parser.add_argument("--parse-limit", type=int, default=100)
    parser.add_argument("--parse-rounds", type=int, default=1)
    parser.add_argument("--index-limit", type=int, default=10)
    parser.add_argument("--evaluation-limit", type=int, default=5)
    parser.add_argument("--execute", action="store_true", help="Run live jobs. Without this flag the flow returns a dry-run plan.")
    args = parser.parse_args()
    selected_amcs = [value for value in args.amcs.split(",") if value.strip()]
    if not args.execute:
        plan = build_evidence_pipeline_plan(
            amcs=selected_amcs,
            parse_only=args.parse_only,
            max_documents=args.max_documents,
            parse_limit=args.parse_limit,
            parse_rounds=args.parse_rounds,
            index_limit=args.index_limit,
            evaluation_limit=args.evaluation_limit,
        )
        print(json.dumps({"status": "dry_run", "flow_version": FLOW_VERSION, "plan": plan}, indent=2))
        return
    try:
        result = fund_research_evidence_flow(
            selected_amcs,
            parse_only=args.parse_only,
            max_documents=args.max_documents,
            parse_limit=args.parse_limit,
            parse_rounds=args.parse_rounds,
            index_limit=args.index_limit,
            evaluation_limit=args.evaluation_limit,
            dry_run=False,
        )
    except Exception:
        logger.exception("event=fund_research_pipeline_failed flow_version=%s", FLOW_VERSION)
        raise
    logger.info("event=fund_research_pipeline_completed flow_version=%s", FLOW_VERSION)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
