from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends

from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.fund_category_service import CategoryCompareRequest, FundCategoryService, MutualFundDetailService
from app.services.compare_data_service import CompareDataService
from app.services.fund_similarity_service import FundSimilarityService
from app.services.document_retrieval_service import DocumentRetrievalService
from app.workflows.fund_research_graph import run_fund_research_workflow
from pydantic import BaseModel
import time
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.admin_ops_repository import AdminOpsRepository
from app.services.data_health_service import DataHealthService

router = APIRouter(tags=["funds"])
JUDGE_REPORT_PATH = Path(__file__).resolve().parents[2] / "evals" / "fund_research_v1" / "judge_report.json"


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
    return DocumentRetrievalService.configured(repository).search(request.query, filters=filters, limit=request.limit)


@router.post("/api/funds/research/answer")
def research_document_answer(
    request: DocumentResearchRequest,
    repository: MutualFundRepository = Depends(get_mutual_fund_repository),
):
    filters = {"amc_code": request.amc_code, "document_type": request.document_type, "report_month": request.report_month}
    service = DocumentRetrievalService.configured(repository)
    return run_fund_research_workflow(service, query=request.query, filters=filters, limit=request.limit)


@router.get("/api/funds/research/evaluation")
def research_evaluation_report():
    if not JUDGE_REPORT_PATH.exists():
        return {
            "status": "not_generated",
            "message": "Run `python -m evals.run_retrieval_evaluation --variant compare --output evals/fund_research_v1/judge_report.json`.",
        }
    return json.loads(JUDGE_REPORT_PATH.read_text(encoding="utf-8"))


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


_TICKER_CACHE = None
_TICKER_CACHE_TIME = 0

@router.get("/api/funds/ticker")
def get_live_ticker_data():
    global _TICKER_CACHE, _TICKER_CACHE_TIME
    now = time.time()
    
    # 5 minute cache
    if _TICKER_CACHE and (now - _TICKER_CACHE_TIME) < 300:
        return _TICKER_CACHE

    repo = MutualFundRepository()
    
    # 1. Fetch Top 5 by AUM
    top_aum = repo.table("mutual_fund_core_snapshot").select("scheme_name, nav, return_1y, aum").order("aum", desc=True, nullsfirst=False).limit(5).execute().data or []
    
    # 2. Fetch Top 5 popular AMCs manually
    popular_names = [
        "Parag Parikh Flexi Cap Fund",
        "Nippon India Small Cap Fund",
        "SBI Small Cap Fund",
        "HDFC Mid-Cap Opportunities Fund",
        "ICICI Prudential Bluechip Fund"
    ]
    popular_funds = []
    for name in popular_names:
        res = repo.table("mutual_fund_core_snapshot").select("scheme_name, nav, return_1y").ilike("scheme_name", f"%{name}%").limit(1).execute().data
        if res:
            popular_funds.append(res[0])
            
    # 3. System Metrics
    admin_repo = AdminOpsRepository()
    health_service = DataHealthService(admin_repo)
    health_data = health_service.get_data_health()
    
    amc_quality = health_data.get("amc_quality", [])
    total_amcs = len(amc_quality)
    total_funds = sum([h.get("total_funds", 0) for h in amc_quality])
    
    system_metrics = {
        "total_amcs": total_amcs,
        "total_funds": total_funds,
    }
    
    # 4. Indices (NIFTY 50 and SENSEX)
    yf_provider = YFinanceProvider()
    indices = []
    
    try:
        nifty_hist = yf_provider.get_price_history("NIFTY", period="5d")
        if nifty_hist and len(nifty_hist) >= 2:
            latest = nifty_hist[-1]
            prev = nifty_hist[-2]
            ret = ((latest["close"] - prev["close"]) / prev["close"]) * 100
            indices.append({"name": "NIFTY 50", "value": latest["close"], "return_1d": ret})
            
        sensex_hist = yf_provider.get_price_history("^BSESN", period="5d")
        if sensex_hist and len(sensex_hist) >= 2:
            latest = sensex_hist[-1]
            prev = sensex_hist[-2]
            ret = ((latest["close"] - prev["close"]) / prev["close"]) * 100
            indices.append({"name": "SENSEX", "value": latest["close"], "return_1d": ret})
    except Exception:
        pass

    _TICKER_CACHE = {
        "top_aum": top_aum,
        "popular_funds": popular_funds,
        "system_metrics": system_metrics,
        "indices": indices
    }
    _TICKER_CACHE_TIME = now
    return _TICKER_CACHE
