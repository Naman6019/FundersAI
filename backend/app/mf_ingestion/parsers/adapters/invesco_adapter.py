from app.mf_ingestion.constants import AMC_INVESCO
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class InvescoAdapter(GenericPortfolioAdapter):
    amc_code = AMC_INVESCO
    scheme_markers = ("invesco ",)
