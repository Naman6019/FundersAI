# Backend Guide

## Stack
- FastAPI + Uvicorn
- Supabase Python client
- Provider adapters for NSE, IndianAPI, FinEdge, YFinance, and local-manual mode

## Main Layout

```text
backend/
  app/
    main.py
    routes/
      quant.py
      indianapi.py
    services/
      quant_service.py
      comparison_reasoning.py
      stock_snapshot_service.py
      indianapi_service.py
      indianapi_quota_guard.py
      provider_usage.py
      mf_metrics_service.py
      mfapi_service.py
      fund_similarity_service.py
      review_priority_service.py
    repositories/
      stock_repository.py
    providers/
      base.py
      manual_provider.py
      nse_provider.py
      indianapi_provider.py
      finedge_provider.py
      yfinance_provider.py
      indianapi_client.py
    jobs/
      sync_stock_universe.py
      sync_latest_prices.py
      sync_price_history.py
      sync_fundamentals.py
      calculate_ratios.py
      sync_corporate_events.py
      sync_mf_nav.py
      sync_mf_enrichment_unified.py
  scripts/
    sync_mf.py
    sync_mf_history.py
    sync_mf_metadata.py
    deprecated/
  migrations/
```

## Route Families
- Core: `/`, `/health`, `/api/v1/providers/usage`
- Quant: `/api/quant/*`
- Chat: `POST /api/chat`
- Mutual-fund ML research: `GET /api/funds/{scheme_code}/similar`
- Internal admin review triage: `GET /api/admin/mf-review-priorities` (requires `X-Admin-Key`)
- Optional IndianAPI helper endpoints: `/api/provider/indianapi/*`

## Data Access Rules
- Use repository/service layer (`stock_repository.py`, `quant_service.py`) instead of ad hoc table logic in routes.
- Keep response shapes additive for frontend compatibility.
- Return explicit missing-data metadata when tables are sparse.
- Keep ML outputs versioned and explainable. The current numeric feature version is `mf_similarity_numeric_v1`; review triage is the non-mutating `mf_review_rule_based_v1` baseline.
- Do not turn similarity, clustering, or parser confidence into investment recommendations or automatic document decisions.

## ML Services
- `fund_similarity_service.py` creates category-scoped vectors from `mutual_fund_core_snapshot`, median-imputes missing numeric values, standardizes features, ranks cosine similarity, and assigns a deterministic k-means cluster.
- `review_priority_service.py` ranks only `pending_review` documents from `mf_parse_review_queue`. It is deliberately a rule baseline until reviewer-verified outcomes support supervised evaluation.
- See [11_ML_SYSTEMS.md](11_ML_SYSTEMS.md) for feature definitions, scoring, API examples, limits, and the learning roadmap.

## Provider Selection
- Controlled by `STOCK_DATA_PROVIDER`.
- If selected provider is unavailable, provider registry falls back to `manual` mode.
- Scheduled stock price workflows use NSE path (`STOCK_DATA_PROVIDER=nse`).
- Scheduled stock universe/fundamentals workflows use FinEdge (`STOCK_DATA_PROVIDER=finedge`).
- IndianAPI remains an explicitly enabled paid fallback/research path.

## Important Flags
- `ENABLE_PROVIDER_USAGE_ENDPOINT`
- `ENABLE_STOCK_FUNDAMENTALS_SYNC`
- `ENABLE_STOCK_PRICE_SYNC`
- `ENABLE_MF_NAV_SYNC`
- `ENABLE_MF_OFFICIAL_SOURCE_PARSER_BYPASS`
- `ENABLE_SHAREHOLDING_SYNC`
- `ENABLE_CORPORATE_ACTIONS_SYNC`
- `INDIANAPI_ENABLE_LIVE_CALLS`
- `INDIANAPI_ENABLE_SCHEDULED_SYNC`

## Jobs and Scheduling
- Jobs are executed by GitHub Actions with `python -m backend.app.jobs.<name>` (plus MF scripts).
- Jobs should be idempotent and safe to rerun.
- Provider and sync issues are expected to degrade gracefully when optional tables/features are absent.

## Local Run
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
