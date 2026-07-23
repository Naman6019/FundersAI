from __future__ import annotations

from pathlib import Path

import pytest

from app.mf_ingestion.agents.persistence import (
    build_discovery_document_observations,
    build_discovery_run_summary,
    persist_discovery_run,
)
from scripts.render_discovery_run_summary import render_summary


class _FakeR2Store:
    enabled = True

    def __init__(self) -> None:
        self.uploads: list[dict] = []

    def upload_bytes(self, key, content, *, bucket=None, content_type=None, metadata=None):
        upload = {
            "key": key.lower(),
            "content": content,
            "bucket": bucket,
            "content_type": content_type,
            "metadata": metadata,
        }
        self.uploads.append(upload)
        return {"bucket": bucket, "key": key.lower()}


class _FailingR2Store(_FakeR2Store):
    def upload_bytes(self, *args, **kwargs):
        raise RuntimeError("r2 unavailable")


class _FakeQuery:
    def __init__(self) -> None:
        self.row = None
        self.on_conflict = None

    def upsert(self, row, *, on_conflict):
        self.row = row
        self.on_conflict = on_conflict
        return self

    def execute(self):
        return {"data": [self.row]}


class _FakeSupabase:
    def __init__(self) -> None:
        self.table_name = None
        self.table_names: list[str] = []
        self.queries: dict[str, _FakeQuery] = {}

    def table(self, name):
        self.table_name = name
        self.table_names.append(name)
        return self.queries.setdefault(name, _FakeQuery())


def _payload():
    return {
        "status": "partial",
        "agents": [
            {"amc": "SBI", "status": "completed", "documents": [{"source_url": "https://www.sbimf.com/a.pdf"}]},
            {"amc": "HDFC", "status": "escalated", "documents": []},
        ],
        "manifest": {"documents": [{"amc": "SBI", "source_url": "https://www.sbimf.com/a.pdf"}]},
        "started_at": "2026-07-21T03:15:00+00:00",
        "completed_at": "2026-07-21T03:16:00+00:00",
    }


def test_build_discovery_run_summary_counts_statuses_and_documents() -> None:
    summary = build_discovery_run_summary(
        _payload(),
        run_id="github-123-1",
        trigger_source="github_actions:schedule",
        expected_month="2026-06-01",
        requested_amcs=["sbi", "hdfc"],
        document_types=("factsheet",),
        report_upload={"bucket": "cold", "key": "report.json"},
        manifest_upload={"bucket": "cold", "key": "manifest.json"},
    )

    assert summary["completed_agent_count"] == 1
    assert summary["agent_status_counts"] == {"completed": 1, "escalated": 1}
    assert summary["document_count"] == 1
    assert summary["requested_amcs"] == ["sbi", "hdfc"]


def test_persist_discovery_run_uploads_r2_evidence_and_upserts_summary() -> None:
    r2_store = _FakeR2Store()
    supabase = _FakeSupabase()

    summary = persist_discovery_run(
        _payload(),
        run_id="github-123-1",
        trigger_source="github_actions:schedule",
        expected_month="2026-06-01",
        requested_amcs=["sbi", "hdfc"],
        document_types=("factsheet",),
        r2_store=r2_store,
        r2_bucket="cold",
        supabase_client=supabase,
    )

    assert len(r2_store.uploads) == 2
    assert "/report-" in r2_store.uploads[0]["key"]
    assert "/manifest-" in r2_store.uploads[1]["key"]
    assert supabase.table_names.count("mf_discovery_runs") == 4
    assert supabase.table_names.count("mf_discovery_documents") == 1
    assert supabase.queries["mf_discovery_runs"].on_conflict == "run_id"
    assert supabase.queries["mf_discovery_runs"].row == summary
    assert supabase.queries["mf_discovery_documents"].on_conflict == "run_id,source_url"


def test_render_summary_is_github_readable() -> None:
    rendered = render_summary(_payload())

    assert "Completed agents: **1/2**" in rendered
    assert "| SBI | completed | 1 |" in rendered
    assert "| HDFC | escalated | 0 |" in rendered


def test_discovery_workflow_is_persistence_only_and_keeps_the_top_ten_gate() -> None:
    workflow = Path(".github/workflows/discover-mf-documents.yml").read_text(encoding="utf-8")

    assert "sbi,mirae,ppfas,icici,hdfc,nippon,kotak,aditya_birla,uti,dsp" in workflow
    assert "--persist-run" in workflow
    assert "--minimum-completed" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "ingest_latest_amc_docs" not in workflow


def test_discovery_run_migration_is_service_role_only() -> None:
    migration = Path("backend/migrations/20260723_add_discovery_v2_history.sql").read_text(encoding="utf-8")

    assert "alter table public.mf_discovery_documents enable row level security" in migration
    assert "revoke all on table public.mf_discovery_documents from anon" in migration
    assert "revoke all on table public.mf_discovery_documents from authenticated" in migration
    assert "grant select, insert, update, delete on table public.mf_discovery_documents to service_role" in migration


def test_document_observations_keep_readiness_and_checksum() -> None:
    payload = _payload()
    payload["manifest"]["documents"][0].update(
        {
            "document_type": "factsheet",
            "report_month": "2026-06-01",
            "discovery_agent_status": "promotable",
            "content_sha256": "abc123",
            "month_confirmation": "confirmed",
        }
    )

    observations = build_discovery_document_observations(payload, run_id="github-123-1")

    assert observations[0]["readiness"] == "promotable"
    assert observations[0]["content_sha256"] == "abc123"


def test_persistence_records_a_failed_stage_for_reconciliation() -> None:
    supabase = _FakeSupabase()

    with pytest.raises(RuntimeError, match="r2 unavailable"):
        persist_discovery_run(
            _payload(),
            run_id="github-123-1",
            trigger_source="github_actions:schedule",
            expected_month="2026-06-01",
            requested_amcs=["sbi", "hdfc"],
            document_types=("factsheet",),
            r2_store=_FailingR2Store(),
            r2_bucket="cold",
            supabase_client=supabase,
        )

    assert supabase.queries["mf_discovery_runs"].row["persistence_state"] == "failed"
    assert supabase.queries["mf_discovery_runs"].row["persistence_retry_count"] == 1
