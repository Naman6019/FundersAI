from __future__ import annotations

from types import SimpleNamespace

import pytest

from orchestration.job_runner import BACKEND_DIR, module_command, run_module
from orchestration.pipeline_plan import build_evidence_pipeline_plan, normalize_amcs


def test_pipeline_plan_wraps_existing_jobs_in_order() -> None:
    plan = build_evidence_pipeline_plan(
        amcs=["HDFC", "hdfc", "axis"],
        parse_only=False,
        max_documents=2,
        parse_limit=25,
        parse_rounds=2,
        index_limit=8,
        evaluation_limit=5,
    )

    assert [item["stage"] for item in plan] == ["ingest", "parse", "parse", "ingest", "parse", "parse", "index", "evaluate"]
    assert plan[0]["module"] == "app.mf_ingestion.jobs.ingest_latest_amc_docs"
    assert plan[-1] == {"stage": "evaluate", "module": "evals.run_retrieval_evaluation", "arguments": ["--limit", "5"]}


def test_parse_only_plan_and_amc_validation() -> None:
    plan = build_evidence_pipeline_plan(
        amcs=["sbi"],
        parse_only=True,
        max_documents=1,
        parse_limit=10,
        parse_rounds=1,
        index_limit=3,
        evaluation_limit=50,
    )
    assert [item["stage"] for item in plan] == ["parse", "index", "evaluate"]
    assert plan[-1]["arguments"] == ["--limit", "10"]
    with pytest.raises(ValueError, match="unsupported AMC"):
        normalize_amcs(["unsupported"])


def test_job_runner_uses_current_interpreter_backend_directory_and_no_shell() -> None:
    captured = {}

    def fake_runner(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    result = run_module("evals.run_retrieval_evaluation", ["--limit", "5"], timeout_seconds=30, runner=fake_runner)

    assert captured["command"] == module_command("evals.run_retrieval_evaluation", ["--limit", "5"])
    assert captured["cwd"] == BACKEND_DIR
    assert "shell" not in captured
    assert result["returncode"] == 0
