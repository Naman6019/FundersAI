import pytest

from backend.scripts.list_actionable_mf_parser_amcs import actionable_matrix


def test_actionable_matrix_defaults_to_green_amcs_with_documents() -> None:
    rows = [{"amc_code": "PPFAS"}, {"amc_code": "HDFC"}, {"amc_code": "unknown"}]

    matrix = actionable_matrix(rows)

    assert matrix == ["ppfas"]
    assert "unknown" not in matrix


def test_actionable_matrix_honors_requested_amcs_and_returns_sentinel() -> None:
    assert actionable_matrix([{"id": "doc-hdfc", "amc_code": "HDFC"}], "motilal", lane="validation_only", source_document_ids="doc-motilal") == ["__none__"]


def test_actionable_matrix_requires_exact_ids_for_restricted_lane() -> None:
    rows = [
        {"id": "approved", "amc_code": "NIPPON"},
        {"id": "unapproved", "amc_code": "NIPPON"},
    ]
    assert actionable_matrix(
        rows,
        "nippon",
        lane="approved_restricted",
        source_document_ids="approved",
    ) == ["nippon"]


@pytest.mark.parametrize("amc", ["icici", "kotak"])
def test_actionable_matrix_rejects_frozen_amcs(amc) -> None:
    with pytest.raises(ValueError, match="github_issue_2"):
        actionable_matrix([], amc)
