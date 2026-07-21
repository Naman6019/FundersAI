from __future__ import annotations

from pathlib import Path

from app.mf_ingestion.agents.persistence import build_discovery_run_summary, persist_discovery_run
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
        self.query = _FakeQuery()

    def table(self, name):
        self.table_name = name
        return self.query


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
    assert r2_store.uploads[0]["key"].endswith("/report.json")
    assert r2_store.uploads[1]["key"].endswith("/manifest.json")
    assert supabase.table_name == "mf_discovery_runs"
    assert supabase.query.on_conflict == "run_id"
    assert supabase.query.row == summary


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
    migration = Path("backend/migrations/20260721_add_mf_discovery_runs.sql").read_text(encoding="utf-8")

    assert "alter table public.mf_discovery_runs enable row level security" in migration
    assert "revoke all on table public.mf_discovery_runs from anon" in migration
    assert "revoke all on table public.mf_discovery_runs from authenticated" in migration
    assert "grant select, insert, update, delete on table public.mf_discovery_runs to service_role" in migration
