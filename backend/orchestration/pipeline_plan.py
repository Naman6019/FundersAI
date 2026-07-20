from __future__ import annotations

from typing import Any, Iterable


SUPPORTED_AMCS = ("axis", "hdfc", "sbi", "icici", "ppfas", "nippon")


def normalize_amcs(values: Iterable[str]) -> list[str]:
    normalized = []
    for value in values:
        amc = str(value or "").strip().lower()
        if not amc or amc in normalized:
            continue
        if amc not in SUPPORTED_AMCS:
            raise ValueError(f"unsupported AMC: {amc}")
        normalized.append(amc)
    if not normalized:
        raise ValueError("at least one supported AMC is required")
    return normalized


def build_evidence_pipeline_plan(
    *,
    amcs: Iterable[str],
    parse_only: bool,
    max_documents: int,
    parse_limit: int,
    parse_rounds: int,
    index_limit: int,
    evaluation_limit: int,
) -> list[dict[str, Any]]:
    normalized_amcs = normalize_amcs(amcs)
    plan: list[dict[str, Any]] = []
    for amc in normalized_amcs:
        if not parse_only:
            plan.append(
                {
                    "stage": "ingest",
                    "amc": amc,
                    "module": "app.mf_ingestion.jobs.ingest_latest_amc_docs",
                    "arguments": ["--amc", amc, "--all-document-types", "--max-documents", str(max(1, max_documents)), "--strict"],
                }
            )
        for round_number in range(1, max(1, parse_rounds) + 1):
            plan.append(
                {
                    "stage": "parse",
                    "amc": amc,
                    "round": round_number,
                    "module": "app.mf_ingestion.jobs.parse_pending_documents",
                    "arguments": ["--amc", amc, "--limit", str(max(1, parse_limit)), "--strict"],
                }
            )
    plan.extend(
        [
            {
                "stage": "index",
                "module": "app.mf_ingestion.jobs.index_parsed_documents",
                "arguments": ["--limit", str(max(1, index_limit))],
            },
            {
                "stage": "evaluate",
                "module": "evals.run_retrieval_evaluation",
                "arguments": ["--limit", str(max(1, min(evaluation_limit, 10)))],
            },
        ]
    )
    return plan
