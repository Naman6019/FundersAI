import pytest

from backend.scripts.list_actionable_mf_parser_amcs import actionable_matrix


def test_actionable_matrix_defaults_to_green_amcs_with_documents() -> None:
    rows = [{"amc_code": "PPFAS"}, {"amc_code": "HDFC"}, {"amc_code": "unknown"}]

    matrix = actionable_matrix(rows)

    assert set(matrix) == {"ppfas", "hdfc"}
    assert "unknown" not in matrix


def test_actionable_matrix_honors_requested_amcs_and_returns_sentinel() -> None:
    assert actionable_matrix([{"id": "doc-hdfc", "amc_code": "HDFC"}], "uti", lane="approved_restricted", source_document_ids="doc-uti") == ["__none__"]


def test_actionable_matrix_requires_exact_ids_for_restricted_lane() -> None:
    rows = [
        {"id": "approved", "amc_code": "UTI"},
        {"id": "unapproved", "amc_code": "UTI"},
    ]
    assert actionable_matrix(
        rows,
        "uti",
        lane="approved_restricted",
        source_document_ids="approved",
    ) == ["uti"]


@pytest.mark.parametrize("amc", ["icici", "kotak"])
def test_formerly_frozen_amcs_are_actionable_in_green_lane(amc) -> None:
    """icici and kotak graduated to GREEN_AMCS once their family-merge bug (GitHub
    issue #2) was fixed; their remaining residual scope exclusions (icici: risk,
    kotak: holdings/sectors) are enforced by the promotion job, not parser retries."""
    rows = [{"id": "doc-1", "amc_code": amc.upper()}]
    assert actionable_matrix(rows, amc, lane="green") == [amc]
