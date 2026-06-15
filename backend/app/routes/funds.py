from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends

from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.fund_category_service import CategoryCompareRequest, FundCategoryService, MutualFundDetailService

router = APIRouter(tags=["funds"])


def get_mutual_fund_repository() -> MutualFundRepository:
    return MutualFundRepository()


def get_category_service(repository: MutualFundRepository = Depends(get_mutual_fund_repository)) -> FundCategoryService:
    return FundCategoryService(repository)


def get_mf_detail_service(repository: MutualFundRepository = Depends(get_mutual_fund_repository)) -> MutualFundDetailService:
    return MutualFundDetailService(repository)


@router.get("/api/funds/category")
def category_funds_endpoint(category: str, service: FundCategoryService = Depends(get_category_service)):
    return service.list_category(category)


@router.post("/api/funds/category/compare")
def category_funds_compare_endpoint(
    req: CategoryCompareRequest,
    service: FundCategoryService = Depends(get_category_service),
):
    return service.compare_category(req)


@router.get("/api/mf/{scheme_code}")
async def get_mutual_fund_details(
    scheme_code: int,
    background_tasks: BackgroundTasks,
    service: MutualFundDetailService = Depends(get_mf_detail_service),
):
    return await service.get_details(scheme_code, background_tasks)
