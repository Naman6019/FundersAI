import re
_deterministic_compare_intent = re.compile(r"^(compare)\s+(?:code\s+)?(\w+)\s+(?:and|with|to)\s+(?:code\s+)?(\w+)$", re.IGNORECASE)

def test_compare_regex_matches_scheme_codes():
    match = _deterministic_compare_intent.match("Compare 122639 with 100033")
    assert match is not None
    assert match.groups() == ("Compare", "122639", "100033")
