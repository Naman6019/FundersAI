from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.mf_ingestion.downloaders import amc_downloader
from app.mf_ingestion.downloaders.amc_downloader import (
    _discover_choice_documents,
    _host_allowed_for_source,
    _iter_choice_documents,
)
from app.mf_ingestion.sources.registry import get_source

API_BODY = [
    {
        "name": "Scheme Documents",
        "children": [
            {
                "name": "Fund Factsheets",
                "financial_years": [
                    {
                        "financial_year": "2026-27",
                        "files": [
                            {
                                "doc_name": "Choice Mutual Fund Factsheet Full July 2026.pdf",
                                "month": "july",
                                "file_type": ".pdf",
                                "open_file_url": "https://choicemf.com/api/document/08XRdjsiiZ/Choice-Factsheet-July-2026.pdf",
                            },
                            {
                                "doc_name": "Choice Mutual Fund Factsheet Full June 2026.pdf",
                                "month": "june",
                                "file_type": ".pdf",
                                "open_file_url": "https://choicemf.com/api/document/aaaaaaaaaa/Choice-Factsheet-June-2026.pdf",
                            },
                        ],
                    }
                ],
            },
            {
                "name": "Key Information Memorandum (KIM)",
                "financial_years": [
                    {
                        "financial_year": "2026-27",
                        "files": [
                            {
                                "doc_name": "KIM July 2026.pdf",
                                "file_type": ".pdf",
                                "open_file_url": "https://choicemf.com/api/document/kkkkkkkkkk/KIM-July-2026.pdf",
                            }
                        ],
                    }
                ],
            },
        ],
    },
    {
        "name": "Regulatory Compliance",
        "children": [
            {
                "name": "Monthly Portfolio",
                "financial_years": [
                    {
                        "financial_year": "2026-27",
                        "files": [
                            {
                                "doc_name": "Choice Gold ETF - February 2026.xls",
                                "file_type": ".xls",
                                "open_file_url": "https://choicemf.com/api/document/jTGqTq7sW8/Choice-Gold-ETF-February-2026.xls",
                            }
                        ],
                    }
                ],
            },
            {
                "name": "Fortnight Portfolio",
                "financial_years": [
                    {
                        "financial_year": "2026-27",
                        "files": [
                            {
                                "doc_name": "CLONTF - Fortnightly Portfolio 31 July 2026.xlsx",
                                "file_type": ".xlsx",
                                "open_file_url": "https://choicemf.com/api/document/ffffffffff/Fortnightly-31-July-2026.xlsx",
                            }
                        ],
                    }
                ],
            },
        ],
    },
]


@pytest.fixture
def stub_api(monkeypatch):
    def _install(payload):
        monkeypatch.setattr(
            amc_downloader,
            "_request_with_retry",
            lambda *_a, **_k: SimpleNamespace(json=lambda: payload, text="", url=""),
        )

    return _install


def test_category_tree_is_flattened_with_its_path():
    rows = _iter_choice_documents(API_BODY)

    paths = {" > ".join(path) for path, _file in rows}
    assert "Scheme Documents > Fund Factsheets" in paths
    assert "Regulatory Compliance > Monthly Portfolio" in paths
    assert len(rows) == 5


def test_factsheets_are_discovered_from_the_api(stub_api):
    """The listing page renders client-side, so both a plain fetch and a rendered-DOM
    scrape saw only a stray CAMS branch list. The page's own API carries the real tree."""
    stub_api({"body": API_BODY})

    documents = _discover_choice_documents(
        get_source("choice"), document_type="factsheet", timeout_seconds=20, user_agent="test"
    )

    titles = [doc.title for doc in documents]
    assert "Choice Mutual Fund Factsheet Full July 2026.pdf" in titles
    assert not any("KIM" in title for title in titles), "only the factsheet category counts"
    newest = documents[0]
    assert newest.report_month is not None and newest.report_month.month == 7


def test_monthly_portfolio_is_taken_but_fortnightly_is_not(stub_api):
    """Fortnightly and half-yearly portfolios sit in sibling categories; the ingestion
    contract wants the monthly scheme portfolio."""
    stub_api({"body": API_BODY})

    documents = _discover_choice_documents(
        get_source("choice"), document_type="portfolio_disclosure", timeout_seconds=20, user_agent="test"
    )

    titles = [doc.title for doc in documents]
    assert titles == ["Choice Gold ETF - February 2026.xls"]


def test_an_unexpected_payload_shape_yields_nothing_rather_than_raising(stub_api):
    stub_api({"message": "error", "body": None})

    assert (
        _discover_choice_documents(
            get_source("choice"), document_type="factsheet", timeout_seconds=20, user_agent="test"
        )
        == []
    )


def test_api_failure_is_contained(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("network down")

    monkeypatch.setattr(amc_downloader, "_request_with_retry", _boom)

    assert (
        _discover_choice_documents(
            get_source("choice"), document_type="factsheet", timeout_seconds=20, user_agent="test"
        )
        == []
    )


def test_documents_are_confined_to_the_amcs_declared_hosts(stub_api):
    """A document URL served from somewhere other than the AMC's own hosts must not be
    ingested as official evidence."""
    hijacked = [
        {
            "name": "Scheme Documents",
            "children": [
                {
                    "name": "Fund Factsheets",
                    "financial_years": [
                        {
                            "financial_year": "2026-27",
                            "files": [
                                {
                                    "doc_name": "Choice Factsheet July 2026.pdf",
                                    "file_type": ".pdf",
                                    "open_file_url": "https://not-choicemf.example.com/factsheet-july-2026.pdf",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    stub_api({"body": hijacked})

    assert (
        _discover_choice_documents(
            get_source("choice"), document_type="factsheet", timeout_seconds=20, user_agent="test"
        )
        == []
    )


def test_host_check_accepts_subdomains_of_a_declared_suffix():
    source = get_source("choice")

    assert _host_allowed_for_source(source, "https://choicemf.com/api/document/x/y.pdf")
    assert _host_allowed_for_source(source, "https://cdn.choicemf.com/y.pdf")
    assert not _host_allowed_for_source(source, "https://choicemf.com.evil.example/y.pdf")
