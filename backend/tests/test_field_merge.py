"""Tests for factsheet field-level merge across PDF and digital sources.

Driven by the real PPFAS case: the PDF supplies `risk_level`, the digital
factsheet supplies `aum`/`benchmark`/`expense_ratio`, and the merged candidate
must carry both.
"""
from __future__ import annotations

from app.mf_ingestion.services.field_merge import (
    DEFAULT_FIELD_PRECEDENCE,
    SOURCE_KIND_DIGITAL,
    SOURCE_KIND_PDF,
    SourceFields,
    merge_scheme_fields,
)


def _pdf(**values):
    return SourceFields(source_kind=SOURCE_KIND_PDF, values=values, source_document_id="pdf-1")


def _digital(**values):
    return SourceFields(source_kind=SOURCE_KIND_DIGITAL, values=values, source_document_id="html-1")


def test_digital_supplies_aum_and_pdf_supplies_risk():
    merged = merge_scheme_fields(
        [
            _pdf(benchmark="NIFTY 500 (TRI)", risk_level="Very High"),
            _digital(aum=147404.51, expense_ratio=0.53, benchmark="NIFTY 500 (TRI)"),
        ]
    )

    assert merged.values["aum"] == 147404.51
    assert merged.values["expense_ratio"] == 0.53
    assert merged.values["risk_level"] == "Very High"
    assert merged.field_sources["aum"] == SOURCE_KIND_DIGITAL
    assert merged.field_sources["risk_level"] == SOURCE_KIND_PDF


def test_digital_benchmark_wins_over_pdf_table_header_noise():
    """The PDF path has produced 'Returns %' as a benchmark value."""
    merged = merge_scheme_fields(
        [
            _pdf(benchmark="Returns %"),
            _digital(benchmark="CRISIL Hybrid 50+50 Moderate Index"),
        ]
    )

    assert merged.values["benchmark"] == "CRISIL Hybrid 50+50 Moderate Index"
    assert merged.field_sources["benchmark"] == SOURCE_KIND_DIGITAL


def test_pdf_fills_field_the_digital_sheet_omits():
    """July's digital sheet has no risk text; the PDF must still supply it."""
    merged = merge_scheme_fields(
        [
            _digital(aum=2731.59, expense_ratio=0.19, benchmark="Nifty 50 Arbitrage (TRI)"),
            _pdf(risk_level="Low"),
        ]
    )

    assert merged.values["risk_level"] == "Low"
    assert merged.values["aum"] == 2731.59


def test_empty_values_do_not_override_available_ones():
    merged = merge_scheme_fields(
        [
            _pdf(risk_level="Very High"),
            _digital(aum=None, expense_ratio="", benchmark="   ", risk_level=None),
        ]
    )

    assert "aum" not in merged.values
    assert "expense_ratio" not in merged.values
    assert "benchmark" not in merged.values
    assert merged.values["risk_level"] == "Very High"


def test_digital_only_still_yields_its_fields():
    merged = merge_scheme_fields([_digital(aum=860.10, benchmark="NIFTY 100 (TRI)")])

    assert merged.values == {"aum": 860.10, "benchmark": "NIFTY 100 (TRI)"}
    assert merged.contributing_source_kinds == (SOURCE_KIND_DIGITAL,)


def test_pdf_only_still_yields_its_fields():
    merged = merge_scheme_fields([_pdf(risk_level="Low to Moderate", fund_manager="Tejas Soman")])

    assert merged.values == {"risk_level": "Low to Moderate", "fund_manager": "Tejas Soman"}
    assert merged.contributing_source_kinds == (SOURCE_KIND_PDF,)


def test_no_sources_yields_empty_merge():
    merged = merge_scheme_fields([])

    assert merged.values == {}
    assert merged.field_sources == {}
    assert merged.contributing_source_kinds == ()


def test_unknown_source_kind_cannot_override():
    merged = merge_scheme_fields(
        [
            SourceFields(source_kind="mystery", values={"aum": 999.0, "risk_level": "Bogus"}),
            _digital(aum=100.0),
            _pdf(risk_level="Low"),
        ]
    )

    assert merged.values["aum"] == 100.0
    assert merged.values["risk_level"] == "Low"


def test_precedence_is_configurable():
    override = dict(DEFAULT_FIELD_PRECEDENCE)
    override["benchmark"] = (SOURCE_KIND_PDF, SOURCE_KIND_DIGITAL)

    merged = merge_scheme_fields(
        [_pdf(benchmark="From PDF"), _digital(benchmark="From Digital")],
        precedence=override,
    )

    assert merged.values["benchmark"] == "From PDF"
    assert merged.field_sources["benchmark"] == SOURCE_KIND_PDF


def test_first_present_source_wins_within_a_kind():
    first = SourceFields(source_kind=SOURCE_KIND_DIGITAL, values={"aum": 1.0})
    second = SourceFields(source_kind=SOURCE_KIND_DIGITAL, values={"aum": 2.0})

    merged = merge_scheme_fields([first, second])

    assert merged.values["aum"] == 1.0


def test_real_ppfas_august_row_shape():
    """Merged values for Parag Parikh Flexi Cap Fund, August 2026."""
    merged = merge_scheme_fields(
        [
            _pdf(benchmark="Nifty 500 TRI", risk_level="Very High"),
            _digital(
                aum=147404.51,
                expense_ratio=0.53,
                benchmark="NIFTY 500 (TRI)",
                fund_manager="Mr. Rajeev Thakkar; Mr. Raunak Onkar",
            ),
        ]
    )

    assert merged.values == {
        "aum": 147404.51,
        "expense_ratio": 0.53,
        "benchmark": "NIFTY 500 (TRI)",
        "fund_manager": "Mr. Rajeev Thakkar; Mr. Raunak Onkar",
        "risk_level": "Very High",
    }


def test_to_dict_reports_provenance():
    merged = merge_scheme_fields([_digital(aum=1.0), _pdf(risk_level="Low")])

    payload = merged.to_dict()

    assert payload["values"]["aum"] == 1.0
    assert payload["field_sources"] == {"aum": "digital", "risk_level": "pdf"}
    assert payload["contributing_source_kinds"] == ["digital", "pdf"]
