from __future__ import annotations

from app.mf_ingestion.constants import AMC_MIRAE
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class MiraeAdapter(GenericPortfolioAdapter):
    amc_code = AMC_MIRAE
    scheme_markers = ("mirae asset",)
    fractional_percent_cells = True
