from datetime import date

import pytest

from app.mf_ingestion.services.kotak_html_identity import (
    AMFISchemeIdentity,
    KotakFactsheetPage,
    discover_kotak_factsheet_pages,
    inspect_kotak_factsheet_page,
    parse_amfi_navall_kotak_identities,
    resolve_kotak_page_identity,
)


ARCHIVE_URL = "https://www.kotakmf.com/factsheet/June_2026/"


def test_discovery_accepts_only_kotak_scheme_pages_under_selected_month() -> None:
    pages = discover_kotak_factsheet_pages(
        """
        <a href="kotak/MULTI-ASSET.html">Kotak Multi Asset Omni FOF</a>
        <a href="how-to-read.html">How to read</a>
        <a href="kotak/ABOUTOUR.html">About Our Fund Managers - Regular Plan</a>
        <a href="https://example.com/factsheet/June_2026/kotak/OTHER.html">Other</a>
        <a href="kotak/MULTI-ASSET.pdf">PDF</a>
        """,
        ARCHIVE_URL,
    )

    assert [page.url for page in pages] == [
        "https://www.kotakmf.com/factsheet/June_2026/kotak/MULTI-ASSET.html"
    ]
    assert pages[0].report_month == date(2026, 6, 1)


def test_inspection_requires_scheme_month_and_portfolio_table() -> None:
    page = KotakFactsheetPage(
        url="https://www.kotakmf.com/factsheet/June_2026/kotak/MULTI-ASSET.html",
        title="Multi Asset",
        report_month=date(2026, 6, 1),
    )
    inspection = inspect_kotak_factsheet_page(
        page,
        """
        <h1>KOTAK MULTI ASSET OMNI FOF</h1>
        <h2>Portfolio</h2><table><tr><th>Issuer/Instrument</th><th>% to Net Assets</th></tr></table>
        <p>Data as on 30th June, 2026 unless otherwise specified.</p>
        """,
        expected_month=date(2026, 6, 1),
    )

    assert inspection.scheme_name == "KOTAK MULTI ASSET OMNI FOF"
    assert inspection.content_month == date(2026, 6, 1)
    assert inspection.has_portfolio is True
    assert inspection.issues == ()


def test_inspection_rejects_content_month_mismatch() -> None:
    page = KotakFactsheetPage("https://www.kotakmf.com/factsheet/June_2026/kotak/A.html", "A", date(2026, 6, 1))
    inspection = inspect_kotak_factsheet_page(
        page,
        "KOTAK ABC FUND Portfolio Issuer/Instrument % to Net Assets Data as on 31st May, 2026",
        expected_month=date(2026, 6, 1),
    )

    assert "kotak_html_content_month_mismatch:2026-05-01!=2026-06-01" in inspection.issues


def test_amfi_navall_parser_keeps_only_kotak_rows_and_isins() -> None:
    rows = parse_amfi_navall_kotak_identities(
        """
        Other Mutual Fund
        1|INF000A00001||Other Fund - Direct Growth|10.0|30-Jun-2026
        Kotak Mahindra Mutual Fund
        2|INF174K01001||Kotak Multi Asset Omni FOF - Direct Growth|10.0|30-Jun-2026
        3|INF174K01002|INF174K01003|Kotak Multi Asset Omni FOF - Regular IDCW|10.0|30-Jun-2026
        """
    )

    assert [row.scheme_code for row in rows] == ["2", "3"]
    assert rows[1].isins == ("INF174K01002", "INF174K01003")


def test_exact_family_match_returns_all_plan_children_without_fuzzy_fallback() -> None:
    page = KotakFactsheetPage("https://www.kotakmf.com/factsheet/June_2026/kotak/A.html", "A", date(2026, 6, 1))
    inspection = inspect_kotak_factsheet_page(
        page,
        "KOTAK MULTI ASSET OMNI FOF Portfolio Issuer/Instrument % to Net Assets Data as on 30th June, 2026",
        expected_month=date(2026, 6, 1),
    )
    resolution = resolve_kotak_page_identity(
        inspection,
        [
            AMFISchemeIdentity("2", "Kotak Multi Asset Omni FOF - Direct Growth", "INF174K01001", None, date(2026, 6, 30)),
            AMFISchemeIdentity("3", "Kotak Multi Asset Omni FOF - Regular IDCW", "INF174K01002", None, date(2026, 6, 30)),
            AMFISchemeIdentity("4", "Kotak Multi Asset Allocation Fund - Direct Growth", "INF174K01004", None, date(2026, 6, 30)),
        ],
    )

    assert resolution.status == "verified"
    assert [child.scheme_code for child in resolution.amfi_children] == ["2", "3"]


def test_missing_amfi_isin_or_exact_family_match_stays_in_review() -> None:
    page = KotakFactsheetPage("https://www.kotakmf.com/factsheet/June_2026/kotak/A.html", "A", date(2026, 6, 1))
    inspection = inspect_kotak_factsheet_page(
        page,
        "KOTAK MULTI ASSET OMNI FOF Portfolio Issuer/Instrument % to Net Assets Data as on 30th June, 2026",
        expected_month=date(2026, 6, 1),
    )
    missing = resolve_kotak_page_identity(inspection, [])
    no_isin = resolve_kotak_page_identity(
        inspection,
        [AMFISchemeIdentity("2", "Kotak Multi Asset Omni FOF - Direct Growth", None, None, date(2026, 6, 30))],
    )

    assert missing.status == "needs_review"
    assert "kotak_amfi_exact_family_match_missing" in missing.issues
    assert no_isin.status == "needs_review"
    assert "kotak_amfi_child_isin_missing" in no_isin.issues


def test_review_cli_rejects_kotak_edge_redirects() -> None:
    from scripts.review_kotak_html_factsheet_identities import _require_kotak_host

    _require_kotak_host("https://www.kotakmf.com/factsheet/June_2026/")
    with pytest.raises(RuntimeError, match="non_official_host:validate.perfdrive.com"):
        _require_kotak_host("https://validate.perfdrive.com/challenge")
