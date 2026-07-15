from __future__ import annotations

from app.services.review_priority_service import PRIORITY_VERSION, ReviewPriorityService, score_review_item


class _Repository:
    def __init__(self, rows):
        self.rows = rows

    def list_pending_review_items(self, *, limit: int):
        return self.rows[:limit]


def test_review_priority_ranks_exception_and_low_confidence_first():
    result = ReviewPriorityService(
        _Repository(
            [
                {
                    "source_document_id": "low",
                    "validation_issues": ["percent_aum_out_of_band"],
                    "confidence_score": 92,
                    "created_at": "2026-07-10T00:00:00+00:00",
                },
                {
                    "source_document_id": "high",
                    "validation_issues": ["parse_exception:RuntimeError", "holdings_not_found_in_document"],
                    "confidence_score": 20,
                    "created_at": "2026-06-01T00:00:00+00:00",
                },
            ]
        )
    ).list_prioritized()

    assert result["priority_version"] == PRIORITY_VERSION
    assert result["items"][0]["source_document_id"] == "high"
    assert result["items"][0]["priority"] == "high"
    assert "Parser exception requires investigation" in result["items"][0]["priority_reasons"]
    assert result["summary"]["high"] == 1


def test_review_priority_is_a_non_mutating_triage_signal():
    item = {"source_document_id": "doc-1", "validation_issues": [], "confidence_score": 99}
    scored = score_review_item(item)

    assert scored["priority_version"] == PRIORITY_VERSION
    assert scored["priority_reasons"] == ["Pending manual review"]
    assert scored["source_document_id"] == "doc-1"


def test_admin_service_exposes_priorities_only_with_the_admin_key(monkeypatch):
    from app.services.admin_service import AdminService

    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "test-admin-key")
    service = AdminService(
        _Repository(
            [{"source_document_id": "doc-1", "validation_issues": ["holdings_not_found"], "confidence_score": 50}]
        )
    )

    result = service.review_priorities(10, "test-admin-key")

    assert result["items"][0]["source_document_id"] == "doc-1"
