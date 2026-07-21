from __future__ import annotations

import asyncio
import contextlib
import json
import logging

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse

from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.chat_service import ChatRequest, ChatService

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


def get_mutual_fund_repository() -> MutualFundRepository:
    return MutualFundRepository()


def get_chat_service(repository: MutualFundRepository = Depends(get_mutual_fund_repository)) -> ChatService:
    return ChatService(repository)


@router.post("/api/chat")
async def chat_endpoint_route(
    req: ChatRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_tier: str | None = Header(default=None, alias="X-User-Tier"),
    x_internal_proxy_key: str | None = Header(default=None, alias="X-Internal-Proxy-Key"),
    service: ChatService = Depends(get_chat_service),
):
    q: asyncio.Queue[str | None] = asyncio.Queue()

    async def status_callback(msg: dict) -> None:
        await q.put(f"data: {json.dumps(msg)}\n\n")

    async def worker() -> None:
        try:
            res = await service.handle_chat(req, x_user_id, x_user_tier, x_internal_proxy_key, status_callback=status_callback)
            await q.put(f"data: {json.dumps({'type': 'final', 'payload': res})}\n\n")
        except Exception:
            logger.exception("Chat stream worker failed")
            await q.put(
                f"data: {json.dumps({'type': 'error', 'message': 'FundersAI research service could not complete the request.'})}\n\n"
            )
        finally:
            await q.put(None)

    async def event_generator():
        task = asyncio.create_task(worker())
        try:
            while True:
                msg = await q.get()
                if msg is None:
                    break
                yield msg
        finally:
            if not task.done():
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
