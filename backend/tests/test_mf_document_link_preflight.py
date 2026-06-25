from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path("backend/scripts").resolve()))

import preflight_mf_document_links as preflight


class _FakeSession:
    def __init__(self, response):
        self.response = response

    def get(self, *_args, **_kwargs):
        return self.response


def test_collect_link_candidates_reads_manifest_before_env(tmp_path: Path):
    manifest = tmp_path / "mf_document_sources.json"
    manifest.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "amc": "PPFAS",
                        "document_type": "factsheet",
                        "report_month": "2026-05",
                        "source_url": "https://amc.ppfas.com/docs/factsheet-may-2026.xlsx",
                        "expected_file_type": ".xlsx",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    docs = preflight.collect_link_candidates(
        amcs=["ppfas"],
        manifest_path=str(manifest),
        env={"MF_PPFAS_FACTSHEET_DOCUMENT_URLS": "https://amc.ppfas.com/docs/factsheet-apr-2026.xlsx"},
    )

    assert [doc.source for doc in docs] == ["manifest", "env"]
    assert docs[0].source_url.endswith("factsheet-may-2026.xlsx")


def test_validate_link_rejects_html_response_for_pdf():
    response = SimpleNamespace(status_code=200, content=b"<html>blocked</html>", headers={"Content-Type": "text/html"})
    candidate = preflight.LinkCandidate(
        amc="AXIS",
        document_type="factsheet",
        source_url="https://www.axismf.com/factsheet.pdf",
        expected_file_type=".pdf",
        report_month=None,
        source="manifest",
    )

    result = preflight.validate_link(
        candidate,
        session=_FakeSession(response),
        timeout_seconds=1,
        max_stale_months=2,
    )

    assert result["status"] == "error"
    assert result["reason"] == "html_response"


def test_validate_link_warns_on_stale_report_month():
    response = SimpleNamespace(status_code=200, content=b"%PDF-1.4", headers={"Content-Type": "application/pdf"})
    candidate = preflight.LinkCandidate(
        amc="AXIS",
        document_type="factsheet",
        source_url="https://www.axismf.com/factsheet.pdf",
        expected_file_type=".pdf",
        report_month=date(2026, 1, 1),
        source="manifest",
    )

    result = preflight.validate_link(
        candidate,
        session=_FakeSession(response),
        timeout_seconds=1,
        max_stale_months=2,
        today=date(2026, 6, 24),
    )

    assert result["status"] == "ok"
    assert result["warnings"] == ["stale_report_month:2026-01-01"]
