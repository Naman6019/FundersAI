from __future__ import annotations

import re
from typing import Any


def is_holding_summary_or_noise(value: Any) -> bool:
    name = " ".join(str(value or "").lower().split())
    if not name:
        return True

    compact = re.sub(r"[^a-z0-9]+", "", name)
    if "subtotal" in compact or "grandtotal" in compact:
        return True
    return name in {
        "total",
        "equity",
        "debt",
        "company",
        "instrument",
        "company/instrument",
        "cash and cash equivalents",
    }
