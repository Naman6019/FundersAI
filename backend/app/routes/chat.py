from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.chat_service import ChatRequest, ChatService

router = APIRouter(tags=["chat"])


def get_mutual_fund_repository() -> MutualFundRepository:
    return MutualFundRepository()


def get_chat_service(repository: MutualFundRepository = Depends(get_mutual_fund_repository)) -> ChatService:
    return ChatService(repository)


@router.post("/api/chat")
async def chat_endpoint(
    req: ChatRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_tier: str | None = Header(default=None, alias="X-User-Tier"),
    x_internal_proxy_key: str | None = Header(default=None, alias="X-Internal-Proxy-Key"),
    service: ChatService = Depends(get_chat_service),
):
    return await service.handle_chat(req, x_user_id, x_user_tier, x_internal_proxy_key)
