from __future__ import annotations

from types import SimpleNamespace

from backend.scripts.report_mf_metric_coverage_remediation import (
    build_metric_coverage_remediation,
)


def _source(_amc_code: str):
    return SimpleNamespace(promotion_enabled=True)


def _candidate(
    *,
    candidate_id: str,
    scheme_code: str,
    source_document_id: str,
    benchmark: str | None = "NIFTY 500 TRI",
    risk_level: str | None = "Very High",
    promotion_status: str = "staged",
    promoted_scopes: list[str] | None = None,
) -> dict:
    return {
        "id": candidate_id,
        "source_document_id": source_document_id,
        "amc_code": "HDFC",
        "report_month": "2026-08-01",
        "mapped_scheme_code": scheme_code,
        "mapped_family_id": f"family-{scheme_code}",
        "mapping_status": "mapped",
        "mapping_confidence": 99,
        "promotion_status": promotion_status,
        "promoted_scopes": promoted_scopes or [],
        "benchmark": benchmark,
        "risk_level": risk_level,
        "checksum": f"checksum-{source_document_id}",
        "storage_key": f"key-{source_document_id}",
        "updated_at": "2026-08-02T00:00:00+00:00",
    }


def _document(source_document_id: str, *, storage_backend: str = "r2") -> dict:
    return {
        "id": source_document_id,
        "amc_code": "HDFC",
        "report_month": "2026-08-01",
        "parse_status": "parsed",
        "storage_backend": storage_backend,
        "checksum": f"checksum-{source_document_id}",
        "storage_key": f"key-{source_document_id}",
    }


def _report(
    *,
    candidates: list[dict],
    documents: list[dict],
    core_by_code: dict[str, dict] | None = None,
):
    targets = [
        {
            "scheme_code": "101",
            "family_id": "family-101",
            "amc_code": "HDFC",
            "report_month": "2026-08-01",
        }
    ]
    return build_metric_coverage_remediation(
        targets=targets,
        core_by_code=core_by_code or {"101": {"scheme_code": "101"}},
        candidate_rows=candidates,
        mapping_by_code={"101": "family-101"},
        document_by_id={row["id"]: row for row in documents},
        source_lookup=_source,
    )


def test_remediation_manifest_uses_exact_staged_candidates_without_writing() -> None:
    report = _report(
        candidates=[_candidate(candidate_id="candidate-1", scheme_code="101", source_document_id="doc-1")],
        documents=[_document("doc-1")],
    )

    assert report["status"] == "action_required"
    assert report["fields"]["benchmark"]["missing_live_count"] == 1
    assert report["fields"]["risk"]["missing_live_count"] == 1
    assert report["fields"]["benchmark"]["manual_review_candidate_count"] == 1
    assert report["fields"]["risk"]["manual_review_candidate_count"] == 1
    assert report["promotion_review_batches"] == [
        {
            "workflow": "Promote MF Disclosures",
            "source_document_id": "doc-1",
            "amc_code": "HDFC",
            "expected_month": "2026-08",
            "scopes": ["benchmark", "risk"],
            "candidate_ids": ["candidate-1"],
            "affected_scheme_codes": ["101"],
            "apply": False,
            "note": "Run a dry-run first; the existing workflow revalidates every gate before any write.",
        }
    ]
    assert report["safety"] == {
        "writes_runtime_data": False,
        "lowers_coverage_thresholds": False,
        "treats_staged_values_as_live_evidence": False,
        "requires_existing_promotion_dry_run": True,
    }


def test_remediation_manifest_blocks_unreviewable_or_previously_promoted_candidates() -> None:
    report = _report(
        candidates=[
            _candidate(
                candidate_id="candidate-1",
                scheme_code="101",
                source_document_id="doc-1",
                promoted_scopes=["benchmark", "risk"],
            )
        ],
        documents=[_document("doc-1")],
    )

    assert report["promotion_review_batches"] == []
    assert report["fields"]["benchmark"]["blocked_counts"] == {
        "previously_promoted_missing_runtime_field": 1
    }
    assert report["fields"]["risk"]["blocked_counts"] == {
        "previously_promoted_missing_runtime_field": 1
    }
    assert report["coverage_gate_projection"]["all_fields_can_pass_with_current_manifest"] is False


def test_remediation_manifest_projects_the_95_percent_gate_without_promoting() -> None:
    targets = [
        {
            "scheme_code": str(code),
            "family_id": f"family-{code}",
            "amc_code": "HDFC",
            "report_month": "2026-08-01",
        }
        for code in range(101, 121)
    ]
    report = build_metric_coverage_remediation(
        targets=targets,
        core_by_code={
            str(code): {
                "scheme_code": str(code),
                "benchmark": "NIFTY 500 TRI",
                "risk_level": "Very High",
            }
            for code in range(103, 121)
        },
        candidate_rows=[
            _candidate(candidate_id="candidate-101", scheme_code="101", source_document_id="doc-1")
        ],
        mapping_by_code={str(code): f"family-{code}" for code in range(101, 121)},
        document_by_id={"doc-1": _document("doc-1")},
        source_lookup=_source,
    )

    projection = report["coverage_gate_projection"]
    assert projection["minimum_coverage"] == 0.95
    assert projection["required_count"] == 19
    assert projection["all_fields_can_pass_with_current_manifest"] is True
    assert projection["fields"]["benchmark"] == {
        "current_count": 18,
        "current_coverage": 0.9,
        "required_additional_count": 1,
        "conditional_manual_promotion_count": 1,
        "conditional_projected_count": 19,
        "conditional_projected_coverage": 0.95,
        "conditional_projected_gate_passes": True,
    }
    assert projection["fields"]["risk"] == projection["fields"]["benchmark"]


def test_remediation_manifest_rejects_conflicting_or_non_r2_candidates() -> None:
    conflicting = _report(
        candidates=[
            _candidate(candidate_id="candidate-1", scheme_code="101", source_document_id="doc-1"),
            _candidate(
                candidate_id="candidate-2",
                scheme_code="101",
                source_document_id="doc-1",
                benchmark="NIFTY 50 TRI",
                risk_level="Moderate",
            ),
        ],
        documents=[_document("doc-1")],
    )
    assert conflicting["promotion_review_batches"] == []
    assert conflicting["fields"]["benchmark"]["blocked_counts"] == {
        "conflicting_current_candidate_values": 1
    }
    assert conflicting["fields"]["risk"]["blocked_counts"] == {
        "conflicting_current_candidate_values": 1
    }

    non_r2 = _report(
        candidates=[_candidate(candidate_id="candidate-3", scheme_code="101", source_document_id="doc-2")],
        documents=[_document("doc-2", storage_backend="supabase")],
    )
    assert non_r2["promotion_review_batches"] == []
    assert non_r2["fields"]["benchmark"]["blocked_counts"] == {"source_not_r2_backed": 1}
    assert non_r2["fields"]["risk"]["blocked_counts"] == {"source_not_r2_backed": 1}


def test_remediation_manifest_uses_the_exact_candidate_selected_for_metric_coverage() -> None:
    report = build_metric_coverage_remediation(
        targets=[
            {
                "scheme_code": "101",
                "family_id": "family-101",
                "amc_code": "HDFC",
                "report_month": "2026-08-01",
                "candidate_id": "candidate-1",
                "source_document_id": "doc-1",
            }
        ],
        core_by_code={"101": {"scheme_code": "101"}},
        candidate_rows=[
            _candidate(candidate_id="candidate-1", scheme_code="101", source_document_id="doc-1"),
            _candidate(
                candidate_id="candidate-2",
                scheme_code="101",
                source_document_id="doc-2",
                benchmark="NIFTY 50 TRI",
                risk_level="Moderate",
            ),
        ],
        mapping_by_code={"101": "family-101"},
        document_by_id={"doc-1": _document("doc-1"), "doc-2": _document("doc-2")},
        source_lookup=_source,
    )

    assert report["promotion_review_batches"][0]["candidate_ids"] == ["candidate-1"]
    assert report["promotion_review_batches"][0]["scopes"] == ["benchmark", "risk"]


def test_remediation_manifest_rejects_an_empty_supported_target_set() -> None:
    report = build_metric_coverage_remediation(
        targets=[],
        core_by_code={},
        candidate_rows=[],
        mapping_by_code={},
        document_by_id={},
        source_lookup=_source,
    )

    assert report["status"] == "error"
    assert report["issues"] == ["no_supported_mapped_schemes"]
