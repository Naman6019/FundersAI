from __future__ import annotations

import asyncio
import json

from app.routes.chat import chat_endpoint_route
from app.services.chat_service import ChatRequest


async def _response_text(response) -> str:
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return "".join(chunks)


async def _invoke(service):
    response = await chat_endpoint_route(ChatRequest(query="Explain this fund"), service=service)
    return response, await _response_text(response)


def test_chat_route_streams_status_then_final_payload():
    class _Service:
        async def handle_chat(self, *_args, status_callback=None, **_kwargs):
            await status_callback({"type": "status", "message": "Loading data..."})
            return {"answer": "Research result"}

    response, body = asyncio.run(_invoke(_Service()))
    frames = [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]

    assert response.media_type == "text/event-stream"
    assert frames == [
        {"type": "status", "message": "Loading data..."},
        {"type": "final", "payload": {"answer": "Research result"}},
    ]


def test_chat_route_returns_safe_error_event(caplog):
    class _Service:
        async def handle_chat(self, *_args, **_kwargs):
            raise RuntimeError("provider-secret-detail")

    _response, body = asyncio.run(_invoke(_Service()))
    frames = [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]

    assert frames == [
        {
            "type": "error",
            "message": "FundersAI research service could not complete the request.",
        }
    ]
    assert "provider-secret-detail" not in str(frames)
    assert "Chat stream worker failed" in caplog.text
