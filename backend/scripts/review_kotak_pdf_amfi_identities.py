"""Create a review-only exact Kotak factsheet-to-AMFI identity report.

Kotak's combined PDF identifies fund families but does not expose all plan/option
unit ISINs.  This command downloads one official Kotak PDF, fetches AMFI's
official NAVAll scheme master once, and emits every exact AMFI child.  It never
stages, promotes, or writes runtime mutual-fund data.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mf_ingestion.agents.validation import inspect_parser_smoke, validate_download
from app.mf_ingestion.downloaders.amc_downloader import AMCDownloader
from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.factsheet_parser import FactsheetParser
from app.mf_ingestion.services.kotak_html_identity import (
    KotakFactsheetPage,
    KotakPageInspection,
    parse_amfi_navall_kotak_identities,
    resolve_kotak_page_identity,
)
from app.mf_ingestion.sources.registry import get_source

AMFI_NAVALL_URL = "https://www.amfiindia.com/spages/NAVAll.txt"


def build_review_rows(
    *,
    scheme_names: list[str],
    source_url: str,
    report_month: date,
    amfi_payload: str,
) -> list[dict]:
    """Return all exact AMFI plan/option children for each Kotak PDF family."""
    identities = parse_amfi_navall_kotak_identities(amfi_payload)
    rows: list[dict] = []
    for scheme_name in scheme_names:
        page = KotakFactsheetPage(
            url=source_url,
            title=scheme_name,
            report_month=report_month,
        )
        resolution = resolve_kotak_page_identity(
            KotakPageInspection(
                page=page,
                scheme_name=scheme_name,
                content_month=report_month,
                has_portfolio=False,
                issues=(),
            ),
            identities,
        )
        rows.append(
            {
                "source_scheme_name": scheme_name,
                "normalized_family_name": resolution.normalized_family_name,
                "status": resolution.status,
                "issues": list(resolution.issues),
                "amfi_children": [asdict(child) for child in resolution.amfi_children],
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review one official Kotak factsheet against AMFI NAVAll without database writes."
    )
    parser.add_argument("--factsheet-url", required=True)
    parser.add_argument("--report-month", required=True, help="Selected Kotak month: YYYY-MM")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report_month = date.fromisoformat(f"{args.report_month}-01")
    source = get_source("kotak")
    discovered = DiscoveredDocument(
        amc_name=source.amc_name,
        amc_code=source.amc_code,
        document_type="factsheet",
        title=f"Kotak MF Factsheet {report_month:%B %Y}",
        url=args.factsheet_url,
        discovery_page_url=source.factsheet_page_url,
        file_ext=".pdf",
        report_month=report_month,
        priority_score=0,
    )
    downloader = AMCDownloader(source, timeout_seconds=60, user_agent="FundersAI official-source review")
    downloaded = downloader.download(discovered)
    download_errors = validate_download(source, downloaded)
    smoke_errors, content_month = inspect_parser_smoke(
        downloaded,
        expected_report_month=report_month,
    )
    if download_errors or smoke_errors:
        raise RuntimeError(
            "kotak_factsheet_rejected:" + ",".join([*download_errors, *smoke_errors])
        )

    file_descriptor, temporary_path = tempfile.mkstemp(suffix=".pdf")
    os.close(file_descriptor)
    try:
        Path(temporary_path).write_bytes(downloaded.file_bytes)
        records = FactsheetParser().parse(
            temporary_path,
            ParseContext(
                source_document_id="review-only",
                source_url=downloaded.source_url,
                report_month=report_month,
            ),
        )
    finally:
        Path(temporary_path).unlink(missing_ok=True)

    response = requests.get(
        AMFI_NAVALL_URL,
        timeout=60,
        headers={"User-Agent": "FundersAI official-source review", "Accept": "text/plain,*/*"},
    )
    response.raise_for_status()
    rows = build_review_rows(
        scheme_names=[record.scheme_name for record in records],
        source_url=downloaded.source_url,
        report_month=report_month,
        amfi_payload=response.text,
    )
    payload = {
        "mode": "review_only",
        "source_url": downloaded.source_url,
        "report_month": report_month.isoformat(),
        "content_month": content_month.isoformat() if content_month else None,
        "amfi_navall_url": AMFI_NAVALL_URL,
        "factsheet_record_count": len(records),
        "exact_family_match_count": sum(bool(row["amfi_children"]) for row in rows),
        "needs_review_count": sum(row["status"] != "verified" for row in rows),
        "records": rows,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
