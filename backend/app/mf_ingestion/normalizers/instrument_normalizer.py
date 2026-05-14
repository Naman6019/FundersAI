from __future__ import annotations

import re


def normalize_instrument_name(value: object) -> str:
    raw = "" if value is None else str(value)
    cleaned = re.sub(r"\s+", " ", raw).strip()
    return cleaned
