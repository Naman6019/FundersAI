# MarketMind Project Summary

MarketMind is a research-first app for Indian stocks and mutual funds.  
The product emphasizes deterministic data, transparent coverage, and explainable comparisons instead of recommendation-style outputs.

## Current Product Surface
- Authenticated dashboard (`/dashboard`) for chat + comparison workflows
- Public landing page (`/`) with research-first positioning
- Admin dashboard (`/admin`) for ops visibility

## Core Capabilities
- AI chat with deterministic data context
- Stock and mutual-fund comparison views
- Supabase-first runtime reads for predictable latency
- Workflow-driven data ingestion and sync health tracking
- Admin monitoring for:
  - users and usage
  - AI usage
  - mutual-fund coverage
  - NAV sync health
  - resolver diagnostics
  - parse `needs_review` visibility

## Data Infrastructure
- Supabase for query-critical structured data
- R2 for raw mutual-fund documents and cold archive storage
- GitHub Actions for stock sync, MF sync, disclosure ingestion, and storage compaction

## Scope Note
Payments, feature flags, full parser control center, and audit logs are planned but not yet complete in the shipped admin phase.
