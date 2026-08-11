from __future__ import annotations

from datetime import date

from scripts.review_kotak_pdf_amfi_identities import build_review_rows


def test_kotak_pdf_review_keeps_all_exact_amfi_plan_children() -> None:
    rows = build_review_rows(
        scheme_names=["Kotak Multi Asset Omni FOF", "Kotak Missing Fund"],
        source_url="https://vatseelabs-s3.kotakmf.com/factsheet.pdf",
        report_month=date(2026, 7, 1),
        amfi_payload="""
Kotak Mahindra Mutual Fund
2|INF174K01001||Kotak Multi Asset Omni FOF - Direct Growth|10.0|30-Jun-2026
3|INF174K01002|INF174K01003|Kotak Multi Asset Omni FOF - Regular IDCW|10.0|30-Jun-2026
""",
    )

    assert rows[0]["status"] == "verified"
    assert [child["scheme_code"] for child in rows[0]["amfi_children"]] == ["2", "3"]
    assert rows[1]["status"] == "needs_review"
    assert "kotak_amfi_exact_family_match_missing" in rows[1]["issues"]
