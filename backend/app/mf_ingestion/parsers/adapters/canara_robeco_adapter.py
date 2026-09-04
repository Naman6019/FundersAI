from app.mf_ingestion.constants import AMC_CANARA_ROBECO
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class CanaraRobecoAdapter(GenericPortfolioAdapter):
    amc_code = AMC_CANARA_ROBECO
    scheme_markers = ("canara robeco ", "canara ")
