from __future__ import annotations

import asyncio


def test_llm_generation_falls_back_from_openrouter_to_groq(monkeypatch):
    from app.services import chat_service as service

    calls: list[str] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "llama-3.3-70b-versatile",
                "choices": [{"message": {"content": "Groq fallback answer"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 4, "total_tokens": 9},
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **_kwargs):
            calls.append(url)
            if "openrouter.ai" in url:
                raise RuntimeError("openrouter unavailable")
            return FakeResponse()

    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setattr(service.httpx, "AsyncClient", lambda **_kwargs: FakeClient())

    answer = asyncio.run(
        service.function_ollama_chat(
            [
                {"role": "system", "content": "Explain clearly."},
                {"role": "user", "content": "What is an expense ratio?"},
            ],
            format="text",
            max_retries=1,
        )
    )

    assert answer == "Groq fallback answer"
    assert calls == [
        service.OPENROUTER_BASE_URL,
        "https://api.groq.com/openai/v1/chat/completions",
    ]


def test_general_expense_ratio_uses_useful_deterministic_fallback(monkeypatch):
    from app.services import chat_service as service

    async def unavailable_model(*_args, **_kwargs):
        return None

    monkeypatch.setattr(service, "function_ollama_chat", unavailable_model)
    metadata: dict = {}

    answer = asyncio.run(
        service.synthesis_response(
            query="Explain mutual fund expense ratio in simple terms.",
            intent_info={"intent": "general", "ticker": None},
            quant_data={},
            news_data=[],
            explanation_mode="beginner",
            response_meta=metadata,
        )
    )

    assert "yearly operating cost" in answer
    assert "not a recommendation" in answer
    assert metadata["answer_mode"] == "general_education"
    assert metadata["model_status"] == "deterministic_fallback"
    assert metadata["status_flag"] == "deterministic_fallback"
