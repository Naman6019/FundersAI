"""Tests for layout-drift detection.

The behaviour these tests lock in is driven by a real event: the PPFAS
2026-08 digital factsheet exposes a Risk-o-Meter table, while the 2026-07 one
does not, so `risk_level` yield collapses from 6/7 to 0/7 without any error.
"""
from __future__ import annotations

from app.mf_ingestion.agents.layout_drift import (
    DRIFT_REASON_FIELD_LOST,
    DRIFT_REASON_RECORD_COUNT_DROP,
    build_layout_fingerprint,
    detect_layout_drift,
)


class _Record:
    """Minimal stand-in for FactsheetRecord (attribute access path)."""

    def __init__(self, **fields):
        self.aum = fields.get("aum")
        self.expense_ratio = fields.get("expense_ratio")
        self.benchmark = fields.get("benchmark")
        self.fund_manager = fields.get("fund_manager")
        self.risk_level = fields.get("risk_level")


def _records(count, **present):
    """Build `count` records, setting only the fields named in `present`."""
    return [_Record(**present) for _ in range(count)]


def test_first_observation_never_reports_drift():
    current = build_layout_fingerprint(_records(7, aum=100.0), document_kind="html")

    report = detect_layout_drift(current, None)

    assert report.drifted is False
    assert report.reasons == ()
    assert report.lost_fields == ()
    assert report.baseline is None


def test_field_present_in_baseline_but_lost_reports_drift():
    baseline = build_layout_fingerprint(
        _records(7, aum=1.0, benchmark="NIFTY", risk_level="Very High"),
        document_kind="html",
    )
    current = build_layout_fingerprint(
        _records(6, aum=1.0, benchmark="NIFTY"),  # risk_level gone
        document_kind="html",
    )

    report = detect_layout_drift(current, baseline)

    assert report.drifted is True
    assert DRIFT_REASON_FIELD_LOST in report.reasons
    assert report.lost_fields == ("risk_level",)


def test_pre_existing_gap_is_not_drift():
    """AUM is absent in the PDF path; it must not alert on every run."""
    baseline = build_layout_fingerprint(
        _records(7, benchmark="NIFTY", risk_level="Very High"),  # no aum
        document_kind="pdf",
    )
    current = build_layout_fingerprint(
        _records(7, benchmark="NIFTY", risk_level="Very High"),  # still no aum
        document_kind="pdf",
    )

    report = detect_layout_drift(current, baseline)

    assert report.drifted is False
    assert "aum" not in report.lost_fields


def test_partial_field_loss_below_threshold_is_not_drift():
    """One scheme missing a field is normal; only a collapse counts."""
    baseline = build_layout_fingerprint(_records(7, risk_level="Very High"), document_kind="pdf")
    current = build_layout_fingerprint(_records(6, risk_level="Very High") + _records(1), document_kind="pdf")

    report = detect_layout_drift(current, baseline)

    assert report.drifted is False
    assert report.lost_fields == ()


def test_record_count_drop_alone_is_reported():
    baseline = build_layout_fingerprint(_records(7, aum=1.0, benchmark="X"), document_kind="html")
    current = build_layout_fingerprint(_records(4, aum=1.0, benchmark="X"), document_kind="html")

    report = detect_layout_drift(current, baseline)

    assert report.drifted is True
    assert DRIFT_REASON_RECORD_COUNT_DROP in report.reasons
    assert report.lost_fields == ()


def test_tiny_documents_are_ignored_to_avoid_noise():
    baseline = build_layout_fingerprint(_records(5, risk_level="Very High"), document_kind="pdf")
    current = build_layout_fingerprint(_records(1), document_kind="pdf")

    report = detect_layout_drift(current, baseline)

    assert report.drifted is False


def test_mapping_records_are_supported_as_well_as_objects():
    rows = [
        {"aum": 1.0, "expense_ratio": 0.5, "benchmark": "X", "fund_manager": "A", "risk_level": "Low"},
        {"aum": None, "expense_ratio": "", "benchmark": "X", "fund_manager": "A", "risk_level": "Low"},
    ]

    fingerprint = build_layout_fingerprint(rows, document_kind="HTML")

    assert fingerprint.document_kind == "html"
    assert fingerprint.record_count == 2
    assert fingerprint.field_counts["aum"] == 1
    assert fingerprint.field_counts["expense_ratio"] == 1
    assert fingerprint.field_counts["risk_level"] == 2


def test_empty_and_whitespace_values_count_as_absent():
    rows = [{"aum": "", "benchmark": "   ", "fund_manager": None, "risk_level": "Low"}]

    fingerprint = build_layout_fingerprint(rows, document_kind="html")

    assert fingerprint.field_counts["aum"] == 0
    assert fingerprint.field_counts["benchmark"] == 0
    assert fingerprint.field_counts["fund_manager"] == 0
    assert fingerprint.field_counts["risk_level"] == 1


def test_evidence_payload_shape_is_stable():
    baseline = build_layout_fingerprint(_records(7, aum=1.0, risk_level="Very High"), document_kind="html")
    current = build_layout_fingerprint(_records(7, aum=1.0), document_kind="html")

    report = detect_layout_drift(current, baseline)

    evidence = report.evidence()
    assert set(evidence) == {
        "drifted",
        "reasons",
        "lost_fields",
        "current_field_ratios",
        "baseline_field_ratios",
    }
    assert evidence["drifted"] is True
    assert evidence["lost_fields"] == ["risk_level"]


def test_different_document_kinds_are_never_compared():
    """HTML and PDF legitimately differ; comparing them must not report drift.

    The digital HTML factsheet carries AUM but renders Risk-o-Meter as an image
    (no risk_level). The PDF carries risk_level but no AUM. Cross-kind
    comparison would alert on every run.
    """
    pdf_baseline = build_layout_fingerprint(
        _records(7, benchmark="X", risk_level="Very High", fund_manager="M"),
        document_kind="pdf",
    )
    html_current = build_layout_fingerprint(
        _records(7, aum=1.0, benchmark="X", expense_ratio=0.5, fund_manager="M"),
        document_kind="html",
    )

    report = detect_layout_drift(html_current, pdf_baseline)

    assert report.drifted is False
    assert report.lost_fields == ()


def test_same_kind_drift_is_still_detected():
    """The kind guard must not mask real within-kind drift."""
    html_baseline = build_layout_fingerprint(
        _records(7, aum=1.0, benchmark="X", risk_level="Very High"),
        document_kind="html",
    )
    html_current = build_layout_fingerprint(
        _records(7, aum=1.0, benchmark="X"),
        document_kind="html",
    )

    report = detect_layout_drift(html_current, html_baseline)

    assert report.drifted is True
    assert report.lost_fields == ("risk_level",)


def test_real_ppfas_august_vs_july_shape():
    """August carried risk for 6/7; July carried none for 7/7."""
    august = build_layout_fingerprint(
        _records(6, aum=1.0, expense_ratio=0.5, benchmark="X", fund_manager="M", risk_level="Very High")
        + _records(1, aum=1.0, expense_ratio=0.5, benchmark="X", fund_manager="M"),
        document_kind="html",
    )
    july = build_layout_fingerprint(
        _records(7, aum=1.0, expense_ratio=0.5, benchmark="X", fund_manager="M"),
        document_kind="html",
    )

    report = detect_layout_drift(july, august)

    assert report.drifted is True
    assert report.lost_fields == ("risk_level",)
