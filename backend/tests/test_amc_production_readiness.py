from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from app.mf_ingestion.agents.discovery_agent import PRODUCTION_TARGET_AMC_AGENT_KEYS
from app.mf_ingestion.downloaders import amc_downloader
from app.mf_ingestion.downloaders.amc_downloader import AMCDownloader
from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument, DownloadedDocument
from app.mf_ingestion.parsers.adapters.aditya_birla_adapter import AdityaBirlaAdapter
from app.mf_ingestion.parsers.adapters.dsp_adapter import DSPAdapter
from app.mf_ingestion.parsers.adapters.kotak_adapter import KotakAdapter
from app.mf_ingestion.parsers.adapters.mirae_adapter import MiraeAdapter
from app.mf_ingestion.parsers.adapters.uti_adapter import UTIAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.services.ingestion_service import (
    IngestionService,
    _canonicalize_document_url,
    _filter_expected_month_documents,
    _rank_discovered_documents,
)
from app.mf_ingestion.jobs.promote_mf_disclosures import (
    _available_core_scopes,
    _fetch_all_rows,
    _parse_report_month,
    _validate_candidate,
    _validate_holding,
    _validate_source_document,
)
from app.mf_ingestion.sources.registry import SOURCES, get_source
from scripts.smoke_parse_mf_raw_documents import _aggregate_results


EXPECTED_AMCS = {
    "hdfc",
    "sbi",
    "icici",
    "axis",
    "ppfas",
    "nippon",
    "motilal",
    "mirae",
    "uti",
    "dsp",
    "kotak",
    "aditya_birla",
}


def _document(url: str, report_month: date | None, priority: int) -> DiscoveredDocument:
    return DiscoveredDocument(
        amc_name="Nippon India Mutual Fund",
        amc_code="NIPPON",
        document_type="factsheet",
        title=url,
        url=url,
        discovery_page_url="https://mf.nipponindiaim.com/downloads",
        file_ext=".pdf",
        report_month=report_month,
        priority_score=priority,
    )


def test_registry_covers_all_twelve_agents_and_moves_discovery_rules_out_of_downloader():
    assert set(SOURCES) == EXPECTED_AMCS
    assert set(PRODUCTION_TARGET_AMC_AGENT_KEYS) == EXPECTED_AMCS
    for source in SOURCES.values():
        assert source.allowed_host_suffixes
        assert source.factsheet_required_keywords
        assert source.portfolio_required_keywords
        assert source.discovery_strategy


def test_discovery_probe_and_acquisition_capabilities_are_independent(monkeypatch):
    source = replace(get_source("uti"), acquisition_enabled=False)
    downloader = AMCDownloader(source, timeout_seconds=1, user_agent="test")
    candidate = _document("https://www.utimf.com/official/factsheet.pdf", date(2026, 6, 1), 1)
    monkeypatch.setattr(
        amc_downloader,
        "_request_with_retry",
        lambda *_args, **_kwargs: SimpleNamespace(
            content=b"%PDF-1.7 official",
            url=candidate.url,
            headers={"Content-Type": "application/pdf"},
        ),
    )

    probe = downloader.probe_download(candidate, max_bytes=1024)

    assert probe.file_bytes.startswith(b"%PDF")
    with pytest.raises(PermissionError, match="acquisition_disabled"):
        downloader.download(candidate)


def test_current_expected_month_outranks_stale_high_priority_manifest():
    current = _document("https://example.test/june-2026.pdf", date(2026, 6, 1), 10)
    stale = _document("https://example.test/november-2024.pdf", date(2024, 11, 1), 9_999_999)

    ranked = _rank_discovered_documents([stale, current], expected_month=date(2026, 6, 1))

    assert ranked[0] == current


def test_expected_month_filter_prevents_stale_acquisition_fallback():
    current = _document("https://example.test/june-2026.pdf", date(2026, 6, 1), 10)
    stale = _document("https://example.test/may-2026.pdf", date(2026, 5, 1), 20)

    selected = _filter_expected_month_documents([stale, current], date(2026, 6, 1))

    assert selected == [current]


def test_exact_month_duplicate_wins_before_cross_month_conflict(monkeypatch):
    downloaded = DownloadedDocument(
        amc_name="ICICI Prudential Mutual Fund",
        amc_code="ICICI",
        document_type="factsheet",
        source_url="https://www.icicipruamc.com/factsheet-june-2026.pdf",
        discovery_page_url="https://www.icicipruamc.com/downloads",
        file_name="factsheet-june-2026.pdf",
        file_ext=".pdf",
        report_month=date(2026, 6, 1),
        content_type="application/pdf",
        file_size_bytes=4,
        file_bytes=b"test",
    )
    service = IngestionService()
    monkeypatch.setattr(service, "_find_duplicate_document", lambda **_kwargs: "exact-june-document")
    monkeypatch.setattr(
        service,
        "_find_checksum_month_conflict",
        lambda **_kwargs: pytest.fail("cross-month lookup must not override an exact-month duplicate"),
    )
    monkeypatch.setattr(service, "_link_discovery_observation", lambda *_args: None)

    result = service._store_downloaded_document(downloaded, source=get_source("icici"))

    assert result["status"] == "skipped"
    assert result["reason"] == "duplicate_checksum"
    assert result["source_document_id"] == "exact-june-document"


def test_canonical_url_drops_tracking_but_preserves_functional_parameters():
    first = _canonicalize_document_url(
        "https://AMC.example/Fund.pdf?download=1&utm_source=email&timestamp=123#page=2"
    )
    second = _canonicalize_document_url("https://amc.example/Fund.pdf?download=1&ts=999")

    assert first == second == "https://amc.example/Fund.pdf?download=1"


def test_staging_migration_and_workflows_keep_acquisition_and_promotion_separate():
    migration = Path("backend/migrations/20260727_add_mf_extraction_staging_and_promotion.sql").read_text(
        encoding="utf-8"
    )
    acquisition = Path(".github/workflows/acquire-mf-documents.yml").read_text(encoding="utf-8")
    promotion = Path(".github/workflows/promote-mf-disclosures.yml").read_text(encoding="utf-8")
    parser_workflow = Path(".github/workflows/sync-mf-disclosures.yml").read_text(encoding="utf-8")
    retry_workflow = Path(".github/workflows/retry-mf-parser-actions.yml").read_text(encoding="utf-8")
    index_workflow = Path(".github/workflows/index-mf-research.yml").read_text(encoding="utf-8")
    parsing_service = Path("backend/app/mf_ingestion/services/parsing_service.py").read_text(encoding="utf-8")

    assert "raw_scheme_name text not null" in migration
    assert "mapped_scheme_code text" in migration
    assert "candidate_mapping_changed" in migration
    assert "candidate_source_evidence_changed" in migration
    assert "p_expected_report_month date" in migration
    assert "promote_mf_factsheet_candidate" in migration
    assert "promote_mf_holdings_document" in migration
    assert "environment: production-data" in acquisition
    assert "ACQUIRE ${EXPECTED_MONTH} ${SELECTED_AMC}" in acquisition
    assert "parse_pending_documents" not in acquisition
    assert "environment: production-data" in promotion
    assert "PROMOTE ${SOURCE_DOCUMENT_ID} ${EXPECTED_MONTH}" in promotion
    assert "--apply" in promotion
    assert "--expected-report-month" in promotion
    assert 'default: "2026-06"' in acquisition
    assert 'PARSE_ONLY="true"' in parser_workflow
    assert "Acquisition is separated. Use Acquire MF Documents" in parser_workflow
    assert 'if [ "$EDGE_ACQUIRED" = "true" ] && [ "$PARSE_ONLY" != "true" ]; then' in parser_workflow
    assert "capability_keys('portfolio_parser_enabled')" in parser_workflow
    assert "MF_DISCLOSURE_COVERAGE_AMCS=\"$(PYTHONPATH=backend python -c" in parser_workflow
    assert "DISPATCH_AMCS:-$(PYTHONPATH=backend python -c" in parser_workflow
    assert "report_mf_staging_coverage.py" in parser_workflow
    assert "--report-month \"${STAGING_REPORT_MONTH}-01\"" in parser_workflow
    assert "axis,hdfc,sbi,icici,ppfas,nippon" not in parser_workflow
    assert "fromJson(needs.registry-matrix.outputs.amcs)" in parser_workflow
    assert "capability_keys('portfolio_parser_enabled')" in retry_workflow
    assert "capability_keys('runtime_enabled')" in retry_workflow
    assert "capability_keys('runtime_enabled')" in index_workflow
    assert 'supabase.table("mutual_fund_holdings").upsert' not in parsing_service
    assert 'supabase.table("mutual_fund_sectors").upsert' not in parsing_service
    assert 'supabase.table("mutual_fund_core_snapshot").update' not in parsing_service


def test_reviewed_source_manifest_keeps_exact_june_axis_and_absl_fallbacks():
    manifest = json.loads(
        Path("backend/config/mf_document_sources.json").read_text(encoding="utf-8")
    )
    documents = manifest["documents"]

    axis_scopes = {
        row["document_type"]
        for row in documents
        if row["amc"] == "AXIS" and row["report_month"] == "2026-06-01"
    }
    absl_factsheets = [
        row
        for row in documents
        if row["amc"] == "ABSL"
        and row["document_type"] == "factsheet"
        and row["report_month"] == "2026-06-01"
    ]

    assert axis_scopes == {"factsheet", "portfolio_disclosure"}
    assert len(absl_factsheets) == 1
    assert "adityabirlacapital.com" in absl_factsheets[0]["source_url"]


def test_promotion_validation_requires_exact_r2_evidence_and_only_available_scopes():
    expected_month = _parse_report_month("2026-06")
    document = {
        "amc_code": "DSP",
        "report_month": "2026-06-01",
        "parse_status": "parsed_partial",
        "storage_backend": "r2",
        "storage_key": "raw/dsp/june.pdf",
        "checksum": "abc",
    }
    candidate = {
        "id": "candidate-1",
        "amc_code": "DSP",
        "report_month": "2026-06-01",
        "mapping_status": "mapped",
        "mapped_scheme_code": "118989",
        "mapped_family_id": "family-1",
        "mapping_confidence": 98,
        "promotion_status": "staged",
        "storage_key": "raw/dsp/june.pdf",
        "checksum": "abc",
        "aum": 100,
        "expense_ratio": 0.4,
        "benchmark": "NIFTY 500 TRI",
        "risk_level": None,
    }

    assert _validate_source_document(document, expected_month) == []
    assert _validate_candidate(candidate, {"118989": "family-1"}, document, expected_month) == []
    assert _available_core_scopes(
        candidate,
        ["risk", "ter_aum", "benchmark", "manager"],
    ) == ["ter_aum", "benchmark"]

    changed = {**candidate, "checksum": "changed"}
    assert "candidate_checksum_mismatch" in _validate_candidate(
        changed,
        {"118989": "family-1"},
        document,
        expected_month,
    )


def test_promotion_dry_run_pages_every_staged_row(monkeypatch):
    rows = [{"id": index, "source_document_id": "doc-1"} for index in range(2_005)]

    class Query:
        def __init__(self, source_rows):
            self.rows = source_rows
            self.start = 0
            self.end = len(source_rows) - 1

        def select(self, _columns):
            return self

        def eq(self, column, value):
            self.rows = [row for row in self.rows if row.get(column) == value]
            return self

        def range(self, start, end):
            self.start = start
            self.end = end
            return self

        def order(self, _column):
            self.rows.sort(key=lambda row: row["id"])
            return self

        def execute(self):
            return SimpleNamespace(data=self.rows[self.start : self.end + 1])

    class FakeSupabase:
        def table(self, _table):
            return Query(rows.copy())

    monkeypatch.setattr(
        "app.mf_ingestion.jobs.promote_mf_disclosures.supabase",
        FakeSupabase(),
    )

    result = _fetch_all_rows(
        "mf_scheme_holdings",
        "id",
        filters={"source_document_id": "doc-1"},
    )

    assert len(result) == 2_005
    assert result[-1]["id"] == 2_004


def test_holdings_promotion_reports_each_rejection_reason():
    issues = _validate_holding(
        {
            "mapping_status": "needs_review",
            "mapping_confidence": 81,
            "mapped_scheme_code": "118989",
            "mapped_family_id": "old-family",
            "report_month": "2026-05-01",
        },
        {"118989": "current-family"},
        {"report_month": "2026-06-01"},
    )

    assert issues == [
        "holdings_mapping_changed",
        "holdings_mapping_confidence_below_90",
        "holdings_mapping_not_reviewed",
        "holdings_report_month_mismatch",
    ]


def test_read_only_parser_smoke_aggregates_field_and_document_coverage():
    summary = _aggregate_results(
        [
            {
                "amc": "dsp",
                "status": "passed",
                "document_type": "factsheet",
                "record_count": 2,
                "field_counts": {
                    "aum": 2,
                    "expense_ratio": 2,
                    "benchmark": 2,
                    "fund_manager": 1,
                    "risk_level": 2,
                },
            },
            {
                "amc": "dsp",
                "status": "failed",
                "document_type": "portfolio_disclosure",
                "source_document_id": "doc-2",
                "reason": "corrupt",
            },
        ]
    )["dsp"]

    assert summary["documents"] == 2
    assert summary["failed_documents"] == 1
    assert summary["factsheet_field_coverage_percent"]["fund_manager"] == 50.0
    assert summary["failed_document_samples"][0]["source_document_id"] == "doc-2"


@pytest.mark.parametrize(
    ("adapter", "scheme_name"),
    [
        (MiraeAdapter(), "Mirae Asset Large Cap Fund"),
        (UTIAdapter(), "UTI Flexi Cap Fund"),
        (DSPAdapter(), "DSP Mid Cap Fund"),
        (KotakAdapter(), "Kotak Equity Opportunities Fund"),
        (AdityaBirlaAdapter(), "Aditya Birla Sun Life Frontline Equity Fund"),
    ],
)
def test_new_adapters_keep_multi_field_official_rows_separate(adapter, scheme_name):
    frame = pd.DataFrame(
        [
            [scheme_name, None, None, None],
            ["As on 30 June 2026", None, None, None],
            ["Name of the Instrument", "ISIN", "Industry", "% to NAV"],
            ["HDFC Bank Limited", "INE040A01034", "Banks", 60.0],
            ["Infosys Limited", "INE009A01021", "IT - Software", 40.0],
        ]
    )

    records = adapter.parse_excel_frame_many(
        frame,
        ParseContext(source_document_id="doc-1", source_url="official", report_month=None),
    )

    assert len(records) == 1
    assert records[0].scheme_name == scheme_name
    assert records[0].report_month == date(2026, 6, 1)
    assert len(records[0].holdings) == 2
    assert records[0].metrics["total_percent_aum"] == 100.0


def test_uti_adapter_ignores_total_rows_when_locating_scheme_name():
    frame = pd.DataFrame(
        [
            ["SCHEME: UTI Value Fund", None, None],
            ["TOTAL : UTI Quant Fund", None, None],
            ["Name of the Instrument", "ISIN", "% to NAV"],
            ["HDFC Bank Ltd", "INE040A01034", 100.0],
        ]
    )

    records = UTIAdapter().parse_excel_frame_many(
        frame,
        ParseContext(
            source_document_id="uti-june",
            source_url="https://example.test/uti-june.zip",
            report_month=date(2026, 6, 1),
        ),
    )

    assert len(records) == 1
    assert records[0].scheme_name == "SCHEME: UTI Value Fund"
    assert records[0].report_month == date(2026, 6, 1)
    assert len(records[0].holdings) == 1
    assert records[0].metrics["total_percent_aum"] == 100.0
