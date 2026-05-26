# Providers

Provider selection is controlled by environment variables.

```env
STOCK_DATA_PROVIDER=manual
FINEDGE_API_KEY=
FINEDGE_BASE_URL=https://data.finedgeapi.com
INDIANAPI_BASE_URL=https://stock.indianapi.in
INDIANAPI_KEY=
INDIANAPI_MONTHLY_LIMIT=5000
INDIANAPI_MONTHLY_RESERVE=500
INDIANAPI_DAILY_SOFT_LIMIT=120
INDIANAPI_ENABLE_LIVE_CALLS=false
INDIANAPI_ENABLE_SCHEDULED_SYNC=true
ENABLE_STOCK_FUNDAMENTALS_SYNC=true
ENABLE_STOCK_PRICE_SYNC=true
ENABLE_MF_NAV_SYNC=true
ENABLE_MF_ENRICHMENT_SYNC=false
ENABLE_MFDATA_FALLBACK_SYNC=false
ENABLE_MF_OFFICIAL_SOURCE_PARSER_BYPASS=true
MFDATA_BASE_URL=https://mfdata.in/api/v1
MFDATA_SYNC_SCHEME_LIMIT=200
MFDATA_REQUEST_SLEEP_SECONDS=6.5
ENABLE_ANALYST_DATA=false
ENABLE_STOCK_NEWS=false
ENABLE_SHAREHOLDING_SYNC=false
ENABLE_CORPORATE_ACTIONS_SYNC=false
GLOBALDATAFEEDS_API_KEY=
STOCK_INFO_ENRICH_LIMIT=120
FUNDAMENTALS_WATCHLIST_SYMBOLS=TCS,RELIANCE,HDFCBANK
FUNDAMENTALS_WEEKLY_LIMIT=100
FUNDAMENTALS_MONTHLY_LIMIT=500
INDIANAPI_REQUEST_SLEEP_SECONDS=1.05
STOCK_YFINANCE_FALLBACK_LIMIT=150
```

## Active Providers
- `manual`: reads local Supabase source-neutral tables.
- `nse`: official NSE bhavcopy EOD price data and historical backfill.
- `yfinance`: fallback for price/history only, not a primary fundamentals provider.
- `finedge`: primary stock enrichment provider for company profile, fundamentals, ratios, shareholding, and corporate events (`FINEDGE_API_KEY` required).
- `indianapi`: paid gap-filler for targeted stock research only (`INDIANAPI_KEY` required), not a scheduled mutual-fund source.
- `mfapi`: primary mutual fund NAV/history provider (`https://api.mfapi.in`).
- `amfi`: official mutual fund NAV, TER, AUM, and scheme-wise disclosure source.
- `amc_disclosure`: AMC factsheets and portfolio disclosures stored raw in R2, parsed only for missing fields.
- `mfdata`: optional monthly mutual fund enrichment fallback for blanks (`https://mfdata.in/api/v1`).

IndianAPI v1 base URL defaults to `https://stock.indianapi.in` and can be overridden with `INDIANAPI_BASE_URL`.
Fundamentals refresh uses `sync_fundamentals --scope watchlist|full|all-active` or `--symbols TCS,RELIANCE`. Weekly watchlist refresh defaults to 100 symbols; monthly full refresh defaults to `NIFTY500` and 500 symbols.
FinEdge authenticates with `token=<apiKey>` in the URL query string.
NSE EOD history uses `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip`.
IndianAPI `/historical_data`, analyst endpoints, and corporate-event fallback are feature-flagged off by default. IndianAPI is not used for scheduled mutual fund ingestion.
Scheduled daily/history price workflows use NSE CM-UDiFF bhavcopy and do not consume IndianAPI quota.
Scheduled stock fundamentals/universe workflows use FinEdge and do not consume IndianAPI quota.
Daily MF NAV/history uses AMFI and MFapi. AMFI enrichment fills TER, AUM, and holdings before AMC parsers run. Monthly MFdata enrichment remains an optional fallback and respects public rate limits.
All provider attempts are logged in `provider_usage_logs` with cache-hit and quota-skip markers.

If a selected paid provider is unavailable, backend code logs a warning and falls back to `manual`.

## Adding a Paid Provider
1. Implement the adapter in `backend/app/providers/`.
2. Normalize responses into `financial_statements`, `ratios_snapshot`, `shareholding_pattern`, and `corporate_events`.
3. Store provider name in `source`.
4. Leave unavailable fields as `null`.
5. Add provider-run logging in `data_provider_runs`.
