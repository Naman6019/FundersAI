# Product Specification

## Positioning
FundersAI is a research-only product for Indian stocks and mutual funds.  
It does not provide investment advice.

## Core Features (Current)
1. Chat + intent-aware research flow
   - AI response plus deterministic data blocks.
2. Stock and mutual-fund comparison canvas
   - NAV/price charts
   - return/risk/cost comparisons
   - explicit data limitations when fields are missing
3. Data automation
   - scheduled stock and MF sync workflows
   - AMC disclosure ingestion for `ppfas`, `icici`, `hdfc`, `sbi`
4. Admin dashboard (Phase 1)
   - overview, users, AI usage, data coverage, NAV sync, resolver debug
   - admin-only access enforced server-side
5. R2-first mutual-fund document storage
   - raw factsheet/disclosure files in R2
   - Supabase reserved for query-critical structured rows

## Primary Users
- Retail investors doing self-directed research
- Internal operators/admin users monitoring data quality and workflow health

## Out of Scope (Current Phase)
- Payments/subscriptions operations UI
- feature flags manager
- full audit logs UI
- full parser operations console with write actions
