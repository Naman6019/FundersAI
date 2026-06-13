import sys
import os
import json
import logging
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.main import _deterministic_compare_intent

print(_deterministic_compare_intent("Compare 120596 with 130498"))
