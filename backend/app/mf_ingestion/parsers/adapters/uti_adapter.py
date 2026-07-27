from app.mf_ingestion.constants import AMC_UTI
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class UTIAdapter(GenericPortfolioAdapter):
    amc_code = AMC_UTI
    scheme_markers = ("uti ",)
