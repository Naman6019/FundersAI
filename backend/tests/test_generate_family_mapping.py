from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate_family_mapping.py"
    spec = importlib.util.spec_from_file_location("generate_family_mapping", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gfm = _load_module()


def test_regular_savings_fund_keeps_its_own_family():
    """Regression for GitHub issue #2: 'Regular' is plan-qualifier noise in the AMFI
    suffix ('Savings Fund - Growth - Regular Plan') but a genuine brand word in schemes
    like 'Regular Savings Fund'. The old unconditional strip collapsed ABSL's and
    ICICI's 'Regular Savings Fund' into their unrelated 'Savings Fund' family and made
    it inherit the wrong benchmark/risk values."""
    savings_fund_regular_plan = "Aditya Birla Sun Life Savings Fund - Growth - Regular Plan"
    savings_fund_direct_plan = "Aditya Birla Sun Life Savings Fund - Growth - Direct Plan"
    regular_savings_fund_growth = "Aditya Birla Sun Life Regular Savings Fund - Growth / Payment - Regular Plan"
    regular_savings_fund_idcw = "Aditya Birla Sun Life Regular Savings Fund - REGULAR - MONTHLY IDCW"

    # The two real, unrelated schemes must land in different families...
    assert gfm.generate_family_id(gfm.clean_scheme_name(savings_fund_regular_plan)) != gfm.generate_family_id(
        gfm.clean_scheme_name(regular_savings_fund_growth)
    )
    # ...while each scheme's own plan/option variants still share one family.
    assert gfm.generate_family_id(gfm.clean_scheme_name(savings_fund_regular_plan)) == gfm.generate_family_id(
        gfm.clean_scheme_name(savings_fund_direct_plan)
    )
    assert gfm.generate_family_id(gfm.clean_scheme_name(regular_savings_fund_growth)) == gfm.generate_family_id(
        gfm.clean_scheme_name(regular_savings_fund_idcw)
    )


def test_icici_regular_savings_fund_keeps_its_own_family():
    raw = "ICICI Prudential Regular Savings Fund - Direct Plan - Growth"
    wrong_family_member = "ICICI Prudential Savings Fund - Growth"

    assert gfm.clean_scheme_name(raw) != gfm.clean_scheme_name(wrong_family_member)


def test_compound_word_hyphen_is_not_treated_as_a_plan_separator():
    with_suffix = gfm.clean_scheme_name("Aditya Birla Sun Life Multi-Cap Fund - Growth - Direct Plan")
    without_suffix = gfm.clean_scheme_name("Aditya Birla Sun Life Multi-Cap Fund")
    assert with_suffix == without_suffix


def test_plan_qualifier_noise_still_stripped_from_suffix():
    cleaned = gfm.clean_scheme_name("HDFC Flexi Cap Fund - Growth Option - Direct Plan")
    assert "direct" not in cleaned
    assert "growth" not in cleaned
    assert "plan" not in cleaned
    assert "flexi cap fund" in cleaned
