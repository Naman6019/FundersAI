from app.mf_ingestion.constants import AMC_DSP
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class DSPAdapter(GenericPortfolioAdapter):
    amc_code = AMC_DSP
    scheme_markers = ("dsp ",)
