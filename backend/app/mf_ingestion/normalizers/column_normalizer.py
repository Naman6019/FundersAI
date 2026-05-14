from __future__ import annotations

import re


COLUMN_ALIASES = {
    "instrument_name": {
        "name of the instrument",
        "instrument",
        "security",
        "security name",
        "company name",
        "name",
    },
    "isin": {
        "isin",
        "isin code",
    },
    "sector": {
        "industry",
        "sector",
        "industry / rating",
        "rating",
    },
    "percent_aum": {
        "% to nav",
        "% to aum",
        "percentage to aum",
        "market value % to aum",
        "% to net assets",
        "% to net asset",
        "weight",
        "weightage",
        "%",
    },
    "market_value": {
        "market value",
        "market value (rs. in lakhs)",
        "market value rs in lakhs",
        "market/fair value (rs. in lakhs)",
        "market/fair value rs in lakhs",
    },
}


def normalize_column_name(column_name: object) -> str:
    raw = "" if column_name is None else str(column_name)
    normalized = re.sub(r"\s+", " ", raw).strip().lower()
    normalized = normalized.replace("\n", " ").replace("_", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()

    for canonical, aliases in COLUMN_ALIASES.items():
        if normalized == canonical:
            return canonical
        if normalized in aliases:
            return canonical
    return normalized


def normalize_columns(columns: list[object]) -> list[str]:
    return [normalize_column_name(col) for col in columns]
