from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends

from app.fetcher import run_eod_fetch
from app.services.provider_usage_service import ProviderUsageService

router = APIRouter(tags=["providers"])


def get_provider_usage_service() -> ProviderUsageService:
    return ProviderUsageService()


@router.get("/api/v1/providers/usage")
def provider_usage_dashboard(service: ProviderUsageService = Depends(get_provider_usage_service)):
    return service.usage_dashboard()


@router.get("/api/trigger-fetch")
async def trigger_eod_fetch(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_eod_fetch)
    return {"message": "Background fetch process triggered successfully."}
