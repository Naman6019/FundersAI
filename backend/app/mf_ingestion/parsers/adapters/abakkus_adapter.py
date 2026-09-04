from app.mf_ingestion.constants import AMC_ABAKKUS
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class AbakkusAdapter(GenericPortfolioAdapter):
    amc_code = AMC_ABAKKUS
    scheme_markers = ("abakkus ",)
