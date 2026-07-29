from __future__ import annotations

import math
from numbers import Real
import re


def normalize_instrument_name(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Real) and not math.isfinite(float(value)):
        return ""
    raw = str(value)
    cleaned = re.sub(r"\s+", " ", raw).strip()
    if cleaned.lower() in {"nan", "none", "null", "<na>", "nat"}:
        return ""
    return cleaned
