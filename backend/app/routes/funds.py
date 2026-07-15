from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends

from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.fund_category_service import CategoryCompareRequest, FundCategoryService, MutualFundDetailService
from app.services.compare_data_service import CompareDataService
from app.services.fund_similarity_service import FundSimilarityService
from app.services.document_retrieval_service import DocumentRetrievalService
from pydantic import BaseModel

router = APIRouter(tags=["funds"])


def get_mutual_fund_repository() -> MutualFundRepository:
    return MutualFundRepository()


def get_category_service(repository: MutualFundRepository = Depends(get_mutual_fund_repository)) -> FundCategoryService:
    return FundCategoryService(repository)


def get_mf_detail_service(repository: MutualFundRepository = Depends(get_mutual_fund_repository)) -> MutualFundDetailService:
    return MutualFundDetailService(repository)


def get_fund_similarity_service(repository: MutualFundRepository = Depends(get_mutual_fund_repository)) -> FundSimilarityService:
    return FundSimilarityService(repository)


@router.get("/api/funds/search")
def search_funds_endpoint(
    q: str,
    plan_type: str = "Direct",
    option_type: str = "Growth",
    limit: int = 10,
    repository: MutualFundRepository = Depends(get_mutual_fund_repository)
):
    if not q or len(q.strip()) < 3:
        return {"results": []}
        
    # Clean the pattern for SQL LIKE
    words = [word for word in q.strip().split() if word]
    pattern = f"%{'%'.join(words)}%" if words else "%"
    
    # We pass None if they explicitly want everything, otherwise enforce
    pt = plan_type if plan_type and plan_type.lower() != "all" else None
    ot = option_type if option_type and option_type.lower() != "all" else None
    
    rows = repository.search_mutual_funds(pattern, limit=limit, plan_type=pt, option_type=ot)
    return {"results": rows}


@router.get("/api/funds/category")
def category_funds_endpoint(category: str, service: FundCategoryService = Depends(get_category_service)):
    return service.list_category(category)


@router.post("/api/funds/category/compare")
def category_funds_compare_endpoint(
    req: CategoryCompareRequest,
    service: FundCategoryService = Depends(get_category_service),
):
    return service.compare_category(req)


@router.get("/api/funds/{scheme_code}/similar")
def similar_funds_endpoint(
    scheme_code: int,
    limit: int = 5,
    service: FundSimilarityService = Depends(get_fund_similarity_service),
):
    return service.find_similar(scheme_code, limit=limit)


class DocumentResearchRequest(BaseModel):
    query: str
    amc_code: str | None = None
    document_type: str | None = None
    report_month: str | None = None
    limit: int = 5


@router.post("/api/funds/research/search")
def research_document_search(
    request: DocumentResearchRequest,
    repository: MutualFundRepository = Depends(get_mutual_fund_repository),
):
    filters = {"amc_code": request.amc_code, "document_type": request.document_type, "report_month": request.report_month}
    return DocumentRetrievalService(repository).search(request.query, filters=filters, limit=request.limit)


@router.get("/api/mf/{scheme_code}")
async def get_mutual_fund_details(
    scheme_code: int,
    background_tasks: BackgroundTasks,
    service: MutualFundDetailService = Depends(get_mf_detail_service),
):
    return await service.get_details(scheme_code, background_tasks)

class VerdictRequest(BaseModel):
    fund_names: list[str]


def _verdict_sources(source_freshness: dict | None) -> list[str]:
    if not isinstance(source_freshness, dict):
        return ["FundersAI DB"]
    sources = []
    for name, payload in source_freshness.items():
        if not isinstance(payload, dict):
            continue
        source = payload.get("source") or "FundersAI DB"
        nav_date = payload.get("nav_date") or "NAV date unavailable"
        sources.append(f"{name}: {source}, {nav_date}")
    return sources or ["FundersAI DB"]


@router.post("/api/funds/compare/verdict")
async def generate_compare_verdict(req: VerdictRequest):
    if len(req.fund_names) < 2:
        return {"verdict": "Need at least two funds to compare.", "sources": []}

    try:
        service = CompareDataService(MutualFundRepository())
        payload = await service.build_mutual_fund_compare(req.fund_names[:4])
        quant_data = payload.get("quant_data") or {}
        why_better = quant_data.get("why_better") or {}
        summary = why_better.get("summary") or "Structured comparison is limited by available local data."
        context = why_better.get("verdict_context") or "Research-only comparison from FundersAI local data."
        limitations = why_better.get("data_limitations") or []
        limitation_text = f" Data limits: {'; '.join(str(item) for item in limitations[:2])}." if limitations else ""
        return {
            "verdict": f"{summary} {context}{limitation_text}",
            "sources": _verdict_sources(why_better.get("source_freshness")),
            "coverage_status": payload.get("coverage_status"),
            "resolution": payload.get("resolution", []),
        }
    except Exception:
        return {"verdict": "Could not generate verdict.", "sources": []}
