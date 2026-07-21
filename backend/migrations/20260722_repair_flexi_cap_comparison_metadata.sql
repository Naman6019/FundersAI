with verified_metadata(scheme_code, category, sub_category, benchmark, risk_level, source_url) as (
  values
    (
      '118955',
      'Equity Scheme - Flexi Cap Fund',
      'Flexi Cap',
      'NIFTY 500 TRI',
      'Very High',
      'https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct'
    ),
    (
      '122639',
      'Equity Scheme - Flexi Cap Fund',
      'Flexi Cap',
      'NIFTY 500 TRI',
      'Very High',
      'https://amc.ppfas.com/downloads/digital-factsheet/2026/may-2026/'
    )
)
update public.mutual_fund_core_snapshot as snapshot
set
  category = verified.category,
  sub_category = verified.sub_category,
  benchmark = verified.benchmark,
  risk_level = verified.risk_level,
  provider_payload = coalesce(snapshot.provider_payload, '{}'::jsonb) || jsonb_build_object(
    'comparison_metadata_repair',
    jsonb_build_object(
      'verified_at', '2026-07-22',
      'source', 'official_amc_factsheet',
      'source_url', verified.source_url
    )
  ),
  last_updated = now()
from verified_metadata as verified
where snapshot.scheme_code = verified.scheme_code;

notify pgrst, 'reload schema';
