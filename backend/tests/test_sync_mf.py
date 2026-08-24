from __future__ import annotations

from backend.scripts.sync_mf import (
    _build_missing_etf_family_mappings,
    parse_amfi_nav_payload,
)


def test_parse_amfi_nav_payload_keeps_direct_growth_and_eight_column_etf_rows():
    payload = "\n".join(
        [
            "1|INF000A00001|-|Example Fund - Direct Growth|10.0|21-Aug-2026",
            "154535;INF754K01XI7;-;Edelweiss BSE LargeMid (60:40) Stable dividend 50 ETF;;;36.835;21-Aug-2026",
            "2|INF000A00002|-|Example Fund - Regular Growth|11.0|21-Aug-2026",
        ]
    )

    rows = parse_amfi_nav_payload(payload)

    assert [row["scheme_code"] for row in rows] == [1, 154535]
    assert rows[1]["isin"] == "INF754K01XI7"
    assert rows[1]["nav"] == 36.835
    assert rows[1]["nav_date"] == "2026-08-21"


def test_missing_etf_family_mapping_does_not_overwrite_existing_mapping():
    rows = [
        {"scheme_code": 154535, "scheme_name": "Edelweiss BSE LargeMid (60:40) Stable dividend 50 ETF"},
        {"scheme_code": 154347, "scheme_name": "Edelweiss Nifty Next 50 ETF"},
    ]

    mappings = _build_missing_etf_family_mappings(rows, {"154347": {"family_id": "existing"}})

    assert mappings == [
        {
            "scheme_code": "154535",
            "family_id": "edelweiss-bse-largemid-60-40-stable-dividend-50-etf",
            "confidence": 0.9,
            "source": "amfi-navall-etf-v1",
        }
    ]
