from app.mf_ingestion.constants import AMC_ANGEL_ONE
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class AngelOneAdapter(GenericPortfolioAdapter):
    amc_code = AMC_ANGEL_ONE
    # The workbooks spell the house name closed up -- "AngelOne Nifty 1D Rate Liquid
    # ETF" -- so neither "angel one " nor "angel " matched a single scheme heading and
    # the whole portfolio parsed to zero holdings.
    scheme_markers = ("angelone ", "angel one ", "angel ")
    # "% To Net Assets" is published as a fraction of 1 (0.999677 + 0.000323 = 1.0),
    # not as a percentage.
    fractional_percent_cells = True
