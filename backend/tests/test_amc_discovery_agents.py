from __future__ import annotations

from datetime import date
from io import BytesIO

import pytest

from app.mf_ingestion.agents.discovery_agent import (
    AGENT_CLASSES,
    TOP_10_AMC_AGENT_KEYS,
    AxisLinkDiscoveryAgent,
    HDFCLinkDiscoveryAgent,
    ICICILinkDiscoveryAgent,
    _dedupe_candidates,
    build_discovery_agent,
)
from app.mf_ingestion.agents.supervisor import AMCDiscoverySupervisor
from app.mf_ingestion.agents.validation import validate_factsheet_content_month
from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument, DownloadedDocument
from app.mf_ingestion.sources.registry import get_source


def _valid_pdf() -> bytes:
    from pypdf import PdfWriter

    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(output)
    return output.getvalue()


class _FakeDownloader:
    def __init__(self, documents=None, *, failure: Exception | None = None, downloads=None):
        self.documents = documents or {}
        self.failure = failure
        self.downloads = downloads or {}

    def list_documents(self, document_type: str):
        if self.failure:
            raise self.failure
        return list(self.documents.get(document_type, []))

    def download(self, discovered: DiscoveredDocument):
        value = self.downloads.get(discovered.url)
        if isinstance(value, Exception):
            raise value
        if value is not None:
            return value
        return _downloaded(discovered, _valid_pdf())


def _discovered(
    amc: str,
    document_type: str,
    url: str,
    *,
    score: int = 100,
    report_month: date | None = date(2026, 4, 1),
) -> DiscoveredDocument:
    source = get_source(amc)
    return DiscoveredDocument(
        amc_name=source.amc_name,
        amc_code=source.amc_code,
        document_type=document_type,
        title=f"{source.amc_code} April 2026 factsheet",
        url=url,
        discovery_page_url=source.factsheet_page_url or url,
        file_ext=".pdf",
        report_month=report_month,
        priority_score=score,
    )


def _downloaded(document: DiscoveredDocument, body: bytes) -> DownloadedDocument:
    return DownloadedDocument(
        amc_name=document.amc_name,
        amc_code=document.amc_code,
        document_type=document.document_type,
        source_url=document.url,
        discovery_page_url=document.discovery_page_url,
        file_name="factsheet.pdf",
        file_ext=".pdf",
        report_month=document.report_month,
        content_type="application/pdf",
        file_size_bytes=len(body),
        file_bytes=body,
    )


def test_hdfc_agent_rejects_non_official_host_and_accepts_valid_probe() -> None:
    third_party = _discovered("hdfc", "factsheet", "https://example.com/hdfc-factsheet.pdf", score=200)
    official = _discovered("hdfc", "factsheet", "https://files.hdfcfund.com/hdfc-factsheet-april-2026.pdf")
    downloader = _FakeDownloader(documents={"factsheet": [third_party, official]})
    agent = HDFCLinkDiscoveryAgent(source=get_source("hdfc"), downloader=downloader)

    result = agent.run(document_types=("factsheet",), expected_month=date(2026, 4, 1))

    assert result.status == "completed"
    assert [document.source_url for document in result.documents] == [official.url]
    assert result.documents[0].probe_status == "passed"
    assert any("non_official_host" in event.detail for event in result.trace)


def test_agent_rejects_html_disguised_as_pdf() -> None:
    official = _discovered("hdfc", "factsheet", "https://files.hdfcfund.com/hdfc-factsheet-april-2026.pdf")
    downloader = _FakeDownloader(
        documents={"factsheet": [official]},
        downloads={official.url: _downloaded(official, b"<html><title>Blocked</title></html>")},
    )
    agent = HDFCLinkDiscoveryAgent(source=get_source("hdfc"), downloader=downloader)

    result = agent.run(document_types=("factsheet",))

    assert result.status == "escalated"
    assert result.documents == []
    assert any("html_response" in event.detail for event in result.trace)


def test_axis_agent_accepts_valid_official_document() -> None:
    official = _discovered(
        "axis",
        "factsheet",
        "https://www.axismf.com/cms/sites/default/files/pdf-factsheets/Axis%20Fund%20Factsheet%20June-2026.pdf",
        report_month=date(2026, 6, 1),
    )
    downloader = _FakeDownloader(documents={"factsheet": [official]})
    agent = AxisLinkDiscoveryAgent(source=get_source("axis"), downloader=downloader)

    result = agent.run(
        document_types=("factsheet",),
        expected_month=date(2026, 6, 1),
        max_candidates_per_type=2,
    )

    assert result.status == "completed"
    assert result.documents[0].source_url == official.url
    assert result.documents[0].probe_status == "passed"


def test_agent_rejects_unknown_or_stale_month_when_expected_month_is_supplied() -> None:
    unknown = _discovered(
        "mirae",
        "factsheet",
        "https://www.miraeassetmf.co.in/docs/factsheet.pdf",
        score=200,
        report_month=None,
    )
    stale = _discovered(
        "mirae",
        "factsheet",
        "https://www.miraeassetmf.co.in/docs/factsheet-may-2026.pdf",
        report_month=date(2026, 5, 1),
    )
    agent = AGENT_CLASSES["mirae"](
        source=get_source("mirae"),
        downloader=_FakeDownloader(documents={"factsheet": [unknown, stale]}),
    )

    result = agent.run(
        document_types=("factsheet",),
        expected_month=date(2026, 6, 1),
        max_candidates_per_type=2,
    )

    assert result.status == "escalated"
    assert all(document.readiness == "needs_review" for document in result.documents)
    assert any("report_month_unknown" in event.detail for event in result.trace)
    assert any("report_month_before_expected" in event.detail for event in result.trace)


def test_discovery_content_month_gate_rejects_mislabeled_factsheet() -> None:
    text = "\n".join(
        [
            "Fund Details as on May 31 2026",
            "Closing AUM as on May 31 2026",
            "Month End AUM as on May 31 2026",
        ]
    )

    assert validate_factsheet_content_month(
        text,
        expected_report_month=date(2026, 6, 1),
    ) == ["factsheet_content_report_month_mismatch:2026-05-01!=2026-06-01"]


def test_discovery_uses_confirmed_content_month_for_next_month_publication(monkeypatch) -> None:
    official = _discovered(
        "aditya_birla",
        "factsheet",
        (
            "https://mutualfund.adityabirlacapital.com/-/media/bsl/files/resources/"
            "factsheets/2026/absl-factsheet_july-2026.pdf"
        ),
        report_month=date(2026, 7, 1),
    )
    agent = AGENT_CLASSES["aditya_birla"](
        source=get_source("aditya_birla"),
        downloader=_FakeDownloader(documents={"factsheet": [official]}),
    )
    monkeypatch.setattr(
        "app.mf_ingestion.agents.discovery_agent.inspect_parser_smoke",
        lambda *_args, **_kwargs: ([], date(2026, 6, 1)),
    )

    result = agent.run(
        document_types=("factsheet",),
        expected_month=date(2026, 6, 1),
    )

    assert result.status == "completed"
    assert result.documents[0].readiness == "promotable"
    assert result.documents[0].report_month == date(2026, 6, 1)
    assert result.documents[0].month_confirmation == "content_confirmed"
    assert not result.documents[0].warnings


@pytest.mark.parametrize(
    ("amc", "official_url"),
    [
        ("sbi", "https://www.sbimf.com/docs/default-source/scheme-factsheets/sbi-factsheet-june-2026.pdf"),
        ("mirae", "https://www.miraeassetmf.co.in/docs/default-source/fachsheet/active-factsheet-june-2026.pdf"),
        ("ppfas", "https://amc.ppfas.com/downloads/factsheet-june-2026.pdf"),
        ("icici", "https://www.icicipruamc.com/downloads/complete-factsheet-june-2026.pdf"),
        ("hdfc", "https://files.hdfcfund.com/hdfc-factsheet-june-2026.pdf"),
        ("nippon", "https://mf.nipponindiaim.com/factsheets/fundamentals-june-2026.pdf"),
        ("kotak", "https://www.kotakmf.com/documents/factsheet-june-2026.pdf"),
        ("aditya_birla", "https://mutualfund.adityabirlacapital.com/documents/factsheet-june-2026.pdf"),
        ("uti", "https://www.utimf.com/documents/fact-sheet-june-2026.pdf"),
        ("dsp", "https://www.dspim.com/downloads/factsheet-june-2026.pdf"),
    ],
)
def test_top_ten_specialists_accept_only_their_official_source(amc: str, official_url: str) -> None:
    document = _discovered(amc, "factsheet", official_url)
    agent_class = AGENT_CLASSES[amc]
    agent = agent_class(
        source=get_source(amc),
        downloader=_FakeDownloader(documents={"factsheet": [document]}),
    )

    result = agent.run(document_types=("factsheet",), expected_month=date(2026, 4, 1))

    assert result.agent_id == f"{amc}_link_discovery_agent_v1"
    assert result.status == "completed"
    assert result.documents[0].source_url == official_url
    assert result.documents[0].probe_status == "passed"


def test_top_ten_agent_roster_matches_requested_amcs() -> None:
    assert TOP_10_AMC_AGENT_KEYS == (
        "sbi",
        "mirae",
        "ppfas",
        "icici",
        "hdfc",
        "nippon",
        "kotak",
        "aditya_birla",
        "uti",
        "dsp",
    )
    assert all(AGENT_CLASSES[key].expected_adapter_key == key for key in TOP_10_AMC_AGENT_KEYS)


@pytest.mark.parametrize("amc", TOP_10_AMC_AGENT_KEYS)
def test_top_ten_factory_builds_each_specialist(amc: str) -> None:
    agent = build_discovery_agent(amc)

    assert isinstance(agent, AGENT_CLASSES[amc])
    assert agent.source.adapter_key == amc


def test_aditya_birla_factory_alias_is_supported() -> None:
    agent = build_discovery_agent("absl")

    assert agent.source.adapter_key == "aditya_birla"


def test_icici_agent_escalates_when_discovery_fails() -> None:
    agent = ICICILinkDiscoveryAgent(
        source=get_source("icici"),
        downloader=_FakeDownloader(failure=RuntimeError("categories endpoint unavailable")),
    )

    result = agent.run(document_types=("factsheet",), probe_downloads=False)

    assert result.status == "escalated"
    assert result.documents == []
    assert any("categories endpoint unavailable" in event.detail for event in result.trace)
    assert any(event.step == "escalate" for event in result.trace)


def test_supervisor_isolates_specialist_failure_and_emits_manifest() -> None:
    hdfc_doc = _discovered("hdfc", "factsheet", "https://files.hdfcfund.com/hdfc-factsheet-april-2026.pdf")
    hdfc = HDFCLinkDiscoveryAgent(
        source=get_source("hdfc"),
        downloader=_FakeDownloader(documents={"factsheet": [hdfc_doc]}),
    )
    icici = ICICILinkDiscoveryAgent(
        source=get_source("icici"),
        downloader=_FakeDownloader(failure=RuntimeError("temporary ICICI failure")),
    )
    supervisor = AMCDiscoverySupervisor({"hdfc": hdfc, "icici": icici})

    result = supervisor.run(document_types=("factsheet",))
    payload = result.to_dict()

    assert result.status == "partial"
    assert [agent.status for agent in result.agents] == ["completed", "escalated"]
    assert payload["manifest"]["documents"][0]["source_url"] == hdfc_doc.url
    assert payload["manifest"]["documents"][0]["discovery_agent_status"] == "promotable"


def test_agent_action_budget_stops_additional_candidate_probes() -> None:
    first = _discovered("hdfc", "factsheet", "https://files.hdfcfund.com/first.pdf", score=200)
    second = _discovered("hdfc", "factsheet", "https://files.hdfcfund.com/second.pdf", score=100)
    agent = HDFCLinkDiscoveryAgent(
        source=get_source("hdfc"),
        downloader=_FakeDownloader(documents={"factsheet": [first, second]}),
        max_actions=2,
    )

    result = agent.run(document_types=("factsheet",), max_candidates_per_type=2)

    assert result.status == "escalated"
    assert result.actions_used == 1
    assert result.documents == []
    assert any(event.step == "action_budget" for event in result.trace)


def test_exact_month_candidates_do_not_starve_later_document_types() -> None:
    expected_month = date(2026, 6, 1)
    exact_factsheet = _discovered(
        "sbi",
        "factsheet",
        "https://www.sbimf.com/docs/factsheet-june-2026.pdf",
        score=300,
        report_month=expected_month,
    )
    stale_factsheet = _discovered(
        "sbi",
        "factsheet",
        "https://www.sbimf.com/docs/factsheet-may-2026.pdf",
        score=200,
        report_month=date(2026, 5, 1),
    )
    portfolio = _discovered(
        "sbi",
        "portfolio_disclosure",
        "https://www.sbimf.com/docs/portfolio-june-2026.xlsx",
        score=300,
        report_month=expected_month,
    )
    agent = AGENT_CLASSES["sbi"](
        source=get_source("sbi"),
        downloader=_FakeDownloader(
            documents={
                "factsheet": [exact_factsheet, stale_factsheet],
                "portfolio_disclosure": [portfolio],
            }
        ),
        max_actions=6,
    )

    result = agent.run(
        document_types=("factsheet", "portfolio_disclosure"),
        expected_month=expected_month,
        max_candidates_per_type=3,
    )

    assert result.status == "completed"
    assert [document.source_url for document in result.documents] == [
        exact_factsheet.url,
        portfolio.url,
    ]
    assert result.actions_used == 6


def test_combined_factsheet_is_reused_for_portfolio_from_registry_capability() -> None:
    expected_month = date(2026, 6, 1)
    factsheet = _discovered(
        "hdfc",
        "factsheet",
        "https://files.hdfcfund.com/hdfc-factsheet-june-2026.pdf",
        report_month=expected_month,
    )
    agent = HDFCLinkDiscoveryAgent(
        source=get_source("hdfc"),
        downloader=_FakeDownloader(
            documents={
                "factsheet": [factsheet],
                "portfolio_disclosure": [],
            }
        ),
    )

    result = agent.run(
        document_types=("factsheet", "portfolio_disclosure"),
        expected_month=expected_month,
    )

    assert result.status == "completed"
    assert [document.document_type for document in result.documents] == [
        "factsheet",
        "portfolio_disclosure",
    ]
    assert {document.source_url for document in result.documents} == {factsheet.url}
    assert any(event.strategy == "registry_combined_factsheet" for event in result.trace)


def test_current_combined_factsheet_replaces_stale_factsheet_portfolio_alias() -> None:
    expected_month = date(2026, 6, 1)
    current = _discovered(
        "kotak",
        "factsheet",
        "https://www.kotakmf.com/factsheet/June_2026/Kotak%20MF%20Factsheet%20June%202026.pdf",
        report_month=expected_month,
    )
    stale_alias = _discovered(
        "kotak",
        "portfolio_disclosure",
        "https://vatseelabs-s3.kotakmf.com/FormsDownloads/Factsheet/KotakMFFactsheetJune2026.pdf",
        report_month=expected_month,
    )
    agent = AGENT_CLASSES["kotak"](
        source=get_source("kotak"),
        downloader=_FakeDownloader(
            documents={
                "factsheet": [current],
                "portfolio_disclosure": [],
            }
        ),
        last_known_good_loader=lambda _source, document_type: (
            [stale_alias] if document_type == "portfolio_disclosure" else []
        ),
    )

    result = agent.run(
        document_types=("factsheet", "portfolio_disclosure"),
        expected_month=expected_month,
    )

    portfolio_urls = [
        document.source_url
        for document in result.documents
        if document.document_type == "portfolio_disclosure"
    ]
    assert portfolio_urls == [current.url]


def test_discovery_dedupes_encoded_and_unencoded_urls() -> None:
    expected_month = date(2026, 6, 1)
    encoded = _discovered(
        "kotak",
        "factsheet",
        "https://www.kotakmf.com/factsheet/June_2026/Kotak%20MF%20Factsheet.pdf",
        score=200,
        report_month=expected_month,
    )
    unencoded = _discovered(
        "kotak",
        "factsheet",
        "https://www.kotakmf.com/factsheet/June_2026/Kotak MF Factsheet.pdf",
        score=100,
        report_month=expected_month,
    )

    assert _dedupe_candidates(
        [unencoded, encoded],
        expected_month=expected_month,
    ) == [encoded]
