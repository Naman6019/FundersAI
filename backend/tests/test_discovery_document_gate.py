from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.mf_ingestion.jobs import run_discovery_agents


def _agent(amc: str, document_count: int, status: str = "completed"):
    return SimpleNamespace(
        amc=amc, status=status, documents=[object()] * document_count
    )


@pytest.fixture
def run_job(monkeypatch, tmp_path):
    """Drive main() with a stubbed supervisor so the gate is exercised on its own."""

    def _run(agents, argv_extra):
        result = SimpleNamespace(
            status="completed",
            agents=agents,
            to_dict=lambda: {
                "status": "completed",
                "agents": [],
                "manifest": {"documents": []},
            },
        )
        monkeypatch.setattr(
            run_discovery_agents.AMCDiscoverySupervisor,
            "build",
            classmethod(lambda _cls, *_a, **_k: SimpleNamespace(run=lambda **_kw: result)),
        )
        monkeypatch.setattr(run_discovery_agents, "build_discovery_diff", lambda *_a, **_k: {})
        monkeypatch.setattr(
            run_discovery_agents, "build_source_configuration_candidates", lambda *_a, **_k: []
        )
        monkeypatch.setattr(
            "sys.argv",
            ["run_discovery_agents", "--amcs", "hdfc,sbi", "--all-document-types", *argv_extra],
        )
        return run_discovery_agents.main()

    return _run


def test_an_amc_that_discovers_nothing_fails_the_run(run_job, caplog):
    """The cheapest reliable signal that a listing page changed shape. Across a full
    42-AMC run this separated the 9 structurally broken AMCs from the 33 healthy ones
    with no overlap -- every healthy AMC returned at least one document."""
    exit_code = run_job(
        [_agent("HDFC", 6), _agent("SBI", 0)], ["--minimum-documents-per-amc", "1"]
    )

    assert exit_code == 1


def test_the_failure_names_the_starved_amc(run_job, caplog):
    with caplog.at_level("ERROR"):
        run_job([_agent("HDFC", 6), _agent("SBI", 0)], ["--minimum-documents-per-amc", "1"])

    assert "SBI=0" in caplog.text
    assert "HDFC" not in caplog.text


def test_a_run_where_every_amc_found_something_passes(run_job):
    exit_code = run_job(
        [_agent("HDFC", 6), _agent("SBI", 1)], ["--minimum-documents-per-amc", "1"]
    )

    assert exit_code == 0


def test_the_gate_is_off_by_default(run_job):
    """A manual dispatch is often deliberately narrow, so the gate must be opt-in."""
    assert run_job([_agent("HDFC", 0), _agent("SBI", 0)], []) == 0


def test_a_threshold_above_one_is_honoured(run_job):
    exit_code = run_job(
        [_agent("HDFC", 3), _agent("SBI", 2)], ["--minimum-documents-per-amc", "3"]
    )

    assert exit_code == 1
