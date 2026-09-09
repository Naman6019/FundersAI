from __future__ import annotations

from app.mf_ingestion.downloaders.amc_downloader import _resolve_listing_file_ext


def test_viewer_script_url_resolves_to_the_real_document_extension():
    """NJ serves every current document through a viewer script with the real file
    name in the query string. Taking the path suffix resolved these to ".php", which
    is not an allowed extension, so all 58 matching factsheet links on the listing
    page were dropped and the AMC discovered nothing."""
    url = "https://downloads.njmutualfund.com/viewfile.php?file=NJ-MF-Factsheet-July-2026-20260806102447.pdf"

    assert _resolve_listing_file_ext(url, f"nj mutual fund factsheet - july 2026 {url}") == ".pdf"


def test_direct_document_url_still_uses_its_own_path_suffix():
    url = "https://downloads.njmutualfund.com/pdf/NJ-BAF-factsheet-October-2021.pdf"

    assert _resolve_listing_file_ext(url, f"nj balanced advantage fund {url}") == ".pdf"


def test_path_suffix_wins_over_an_unrelated_extension_mentioned_in_the_title():
    """A workbook whose surrounding listing text happens to mention a PDF must not
    be misread as a PDF: a real, supported path suffix is authoritative."""
    url = "https://example.com/downloads/monthly-portfolio-july-2026.xlsx"
    combined = f"monthly portfolio july 2026 (see also the factsheet .pdf) {url}"

    assert _resolve_listing_file_ext(url, combined) == ".xlsx"


def test_extensionless_url_still_falls_back_to_text_inference():
    url = "https://example.com/downloads/12345"

    assert _resolve_listing_file_ext(url, "monthly portfolio .xlsx download") == ".xlsx"


def test_unresolvable_link_keeps_its_path_suffix_so_it_is_filtered_out():
    """An unrecognised suffix with nothing inferable must stay unrecognised rather
    than becoming empty, so the allowed-extension check still rejects it."""
    url = "https://example.com/investor/login.aspx"

    assert _resolve_listing_file_ext(url, f"investor login {url}") == ".aspx"
