from __future__ import annotations

from app.mf_ingestion.agents.llm_recovery import BoundedLLMPageRecovery, _select_existing_links_with_llm
from app.mf_ingestion.sources.registry import get_source


def test_llm_recovery_is_disabled_without_its_feature_flag(monkeypatch) -> None:
    def fail_get(*args, **kwargs):
        raise AssertionError("disabled recovery must not fetch")

    monkeypatch.setattr("app.mf_ingestion.agents.llm_recovery.requests.get", fail_get)

    assert BoundedLLMPageRecovery(enabled=False, model="test")(get_source("hdfc"), "factsheet") == []


def test_llm_recovery_discards_urls_not_present_on_the_official_page(monkeypatch) -> None:
    class _Response:
        def json(self):
            return {"choices": [{"message": {"content": '{"urls":["https://evil.test/a.pdf","https://www.hdfcfund.com/a.pdf"]}'}}]}

        def raise_for_status(self):
            return None

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("app.mf_ingestion.agents.llm_recovery.requests.post", lambda *args, **kwargs: _Response())

    result = _select_existing_links_with_llm(
        model="test",
        document_type="factsheet",
        page_url="https://www.hdfcfund.com/factsheets",
        links={"https://www.hdfcfund.com/a.pdf": "June factsheet"},
    )

    assert result == ["https://www.hdfcfund.com/a.pdf"]
