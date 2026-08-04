from backend.scripts.list_actionable_mf_parser_amcs import actionable_matrix


def test_actionable_matrix_only_includes_enabled_amcs_with_documents() -> None:
    rows = [{"amc_code": "MOTILAL"}, {"amc_code": "HDFC"}, {"amc_code": "unknown"}]

    matrix = actionable_matrix(rows)

    assert "motilal" in matrix
    assert "hdfc" in matrix
    assert "unknown" not in matrix


def test_actionable_matrix_honors_requested_amcs_and_returns_sentinel() -> None:
    assert actionable_matrix([{"amc_code": "HDFC"}], "motilal") == ["__none__"]
