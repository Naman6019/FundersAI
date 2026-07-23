from __future__ import annotations

from app.mf_ingestion.agents.history import (
    build_discovery_diff,
    build_source_configuration_candidates,
)


def _document(*, url: str, checksum: str = "abc", readiness: str = "promotable") -> dict:
    return {
        "amc": "HDFC",
        "document_type": "factsheet",
        "report_month": "2026-06-01",
        "source_url": url,
        "content_sha256": checksum,
        "discovery_agent_status": readiness,
        "month_confirmation": "confirmed",
    }


def test_discovery_diff_ignores_unchanged_documents_and_reports_content_changes() -> None:
    unchanged = _document(url="https://files.hdfcfund.com/june.pdf")
    changed = _document(url="https://files.hdfcfund.com/june.pdf", checksum="def")

    diff = build_discovery_diff([unchanged], [changed])

    assert diff["added"] == []
    assert diff["removed"] == []
    assert diff["changed"][0]["changes"]["content_sha256"] == {"before": "abc", "after": "def"}


def test_source_configuration_candidate_requires_three_promotable_observations() -> None:
    document = _document(url="https://files.hdfcfund.com/june.pdf")

    assert build_source_configuration_candidates([document, document]) == []
    staged = build_source_configuration_candidates([document, document, document])

    assert staged[0]["state"] == "staged_for_review"
    assert staged[0]["consecutive_promotable_runs"] == 3
