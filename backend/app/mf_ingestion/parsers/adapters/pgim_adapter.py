from app.mf_ingestion.constants import AMC_PGIM
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class PGIMAdapter(GenericPortfolioAdapter):
    amc_code = AMC_PGIM
    scheme_markers = ("pgim india ", "pgim ")
