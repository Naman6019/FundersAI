from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class SectorAllocation(BaseModel):
    sector_name: str
    weight_pct: float

class FundHolding(BaseModel):
    security_name: Optional[str] = None
    isin: Optional[str] = None
    sector: Optional[str] = None
    weight_pct: Optional[float] = None
    source: Optional[str] = None
    provider_payload: Optional[Dict[str, Any]] = None

class RiskMetrics(BaseModel):
    stdDev: Optional[float] = None
    sharpeRatio: Optional[float] = None
    sortinoRatio: Optional[float] = None
    maxDrawdown: Optional[float] = None
    alpha_vs_nifty: Optional[float] = None
    beta: Optional[float] = None

class FundReturns(BaseModel):
    model_config = {"populate_by_name": True}
    return_1y: Optional[float] = Field(None, alias="1Y")
    return_3y: Optional[float] = Field(None, alias="3Y")
    return_5y: Optional[float] = Field(None, alias="5Y")

class NavHistoryPoint(BaseModel):
    date: str
    value: float

class FundDetails(BaseModel):
    scheme_code: str
    scheme_name: str
    amc: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    aum: Optional[float] = None
    expense_ratio: Optional[float] = None
    risk_level: Optional[str] = None
    launch_date: Optional[str] = None
    benchmark: Optional[str] = None
    
    # Returns
    return_1y: Optional[float] = None
    return_3y: Optional[float] = None
    return_5y: Optional[float] = None
    
    # Risk
    volatility_1y: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown_1y: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None

    # Enriched data
    holdings: List[FundHolding] = []
    sector_allocation: List[SectorAllocation] = []

class FundDataQuality(BaseModel):
    nav_points_count: int
    first_nav_date: Optional[str] = None
    last_nav_date: Optional[str] = None
    is_stale: bool = False
    warning: Optional[str] = None

class FundProfileResponse(BaseModel):
    details: FundDetails
    returns: FundReturns
    risk_metrics: RiskMetrics
    nav_history: List[NavHistoryPoint] = []
    data_quality: FundDataQuality
