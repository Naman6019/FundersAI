import sys
import os
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.main import _deterministic_compare_intent

def test_deterministic_compare_intent_accepts_fund_names():
    result = _deterministic_compare_intent("Compare Parag Parikh Flexi Cap and HDFC Flexi Cap")
    assert result is not None
    assert result.get("asset_type") == "mutual_fund"
    assert result.get("compare_entities") == ["Parag Parikh Flexi Cap", "HDFC Flexi Cap"]
