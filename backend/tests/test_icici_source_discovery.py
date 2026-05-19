from __future__ import annotations

from datetime import date

from app.mf_ingestion.downloaders import amc_downloader
from app.mf_ingestion.downloaders.amc_downloader import AMCDownloader
from app.mf_ingestion.sources.registry import AMCDocumentSource


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http_{self.status_code}")

    def json(self) -> dict:
        return self._payload


class _FakeSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.files_requests: list[dict] = []

    def request(
        self,
        method: str,
        url: str,
        timeout: float | None = None,
        headers: dict | None = None,
        params: dict | None = None,
        json: dict | None = None,
    ) -> _FakeResponse:
        if method.upper() == "GET":
            return self.get(url, params=params, timeout=timeout)
        elif method.upper() == "POST":
            return self.post(url, json=json, timeout=timeout)
        raise ValueError(f"Unsupported method: {method}")

    def get(self, url: str, params: dict | None = None, timeout: float | None = None) -> _FakeResponse:
        assert url == amc_downloader.ICICI_CATEGORIES_ENDPOINT
        assert params == {"userType": "Investor"}
        return _FakeResponse(
            {
                "success": {
                    "data": [
                        {
                            "title": {"code": "OTHERS"},
                            "internalName": "other scheme disclosures",
                            "subCategory": [
                                {
                                    "id": "sub-monthly",
                                    "internalName": "monthly-portfolio-disclosures",
                                }
                            ],
                        },
                        {
                            "title": {"code": "HISTORICAL_FACTSHEET"},
                            "internalName": "historical-factsheets",
                            "subCategory": [
                                {
                                    "id": "sub-complete",
                                    "internalName": "complete-factsheet",
                                }
                            ],
                        },
                    ]
                }
            }
        )

    def post(self, url: str, json: dict | None = None, timeout: float | None = None) -> _FakeResponse:
        assert url == amc_downloader.ICICI_FILES_ENDPOINT
        payload = dict(json or {})
        self.files_requests.append(payload)
        if payload.get("categoryId") == "sub-monthly":
            return _FakeResponse(
                {
                    "success": {
                        "data": {
                            "files": [
                                {
                                    "title": {"text": "Monthly Portfolio Disclosure April 2026"},
                                    "url": "/downloads/monthly-apr-2026.zip",
                                    "applicableMonth": 1777525200000,
                                }
                            ],
                            "isNext": False,
                        }
                    }
                }
            )

        return _FakeResponse(
            {
                "success": {
                    "data": {
                        "files": [
                            {
                                "title": {"text": "Complete Factsheet April 2026"},
                                "url": "/downloads/complete-apr-2026.pdf",
                                "fileDate": 1777525200000,
                            }
                        ],
                        "isNext": False,
                    }
                }
            }
        )



def _icici_source() -> AMCDocumentSource:
    return AMCDocumentSource(
        amc_name="ICICI Prudential Mutual Fund",
        amc_code="ICICI",
        adapter_key="icici",
        factsheet_page_url="https://www.icicipruamc.com/media-center/downloads",
        portfolio_disclosure_page_url="https://www.icicipruamc.com/media-center/downloads",
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
    )


def test_icici_discovery_uses_live_category_and_files_contract(monkeypatch):
    fake_session = _FakeSession()
    monkeypatch.setattr(amc_downloader.requests, "Session", lambda: fake_session)

    downloader = AMCDownloader(source=_icici_source(), timeout_seconds=10, user_agent="test-agent")
    docs = downloader.list_documents("portfolio_disclosure")

    assert len(docs) == 1
    assert docs[0].file_ext == ".zip"
    assert docs[0].report_month == date(2026, 4, 1)
    assert docs[0].url == "https://www.icicipruamc.com/downloads/monthly-apr-2026.zip"
    assert fake_session.files_requests[0]["categoryId"] == "sub-monthly"
    assert fake_session.files_requests[0]["categoryName"] == "OTHERS"
    assert fake_session.files_requests[0]["fileType"] == "All"


def test_icici_factsheet_discovery_maps_complete_factsheet_subcategory(monkeypatch):
    fake_session = _FakeSession()
    monkeypatch.setattr(amc_downloader.requests, "Session", lambda: fake_session)

    downloader = AMCDownloader(source=_icici_source(), timeout_seconds=10, user_agent="test-agent")
    docs = downloader.list_documents("factsheet")

    assert len(docs) == 1
    assert docs[0].file_ext == ".pdf"
    assert docs[0].report_month == date(2026, 4, 1)
    assert docs[0].url == "https://www.icicipruamc.com/downloads/complete-apr-2026.pdf"
    assert fake_session.files_requests[0]["categoryId"] == "sub-complete"
    assert fake_session.files_requests[0]["categoryName"] == "HISTORICAL_FACTSHEET"
