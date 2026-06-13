import re
_deterministic_compare_intent = re.compile(r"^(compare)\s+(?:code\s+)?(\w+)\s+(?:and|with|to)\s+(?:code\s+)?(\w+)$", re.IGNORECASE)

m = _deterministic_compare_intent.match("Compare 122639 with 100033")
if m:
    print("Match!")
    print(m.groups())
else:
    print("No match")
