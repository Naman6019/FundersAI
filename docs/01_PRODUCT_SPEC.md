# Product Specification

**Last updated:** 2026-07-21

## Positioning
FundersAI is a research-only product for Indian stocks and mutual funds.  
It does not provide investment advice.

## Core Features (Current)
1. Chat + intent-aware research flow
   - AI response plus deterministic data blocks.
   - Authenticated, user-owned sessions and message restoration.
2. Stock and mutual-fund comparison canvas
   - NAV/price charts
   - return/risk/cost comparisons
   - explicit data limitations when fields are missing
3. Data automation
   - scheduled stock and MF sync workflows
   - enabled AMC disclosure sources for `ppfas`, `hdfc`, `icici`, `sbi`, `axis`, `motilal`, and `nippon`
4. Official-document research
   - deterministic lexical reranking and evidence-coverage abstention by default
   - cited official-source answers through a bounded LangGraph workflow
   - vector retrieval and v3 grading remain opt-in experiments
5. Admin dashboard
   - overview, users, AI usage, data coverage, NAV sync, resolver debug
   - bounded parser reparse, resolve, and skip actions
   - admin-only access enforced server-side
6. R2-first mutual-fund document storage
   - raw factsheet/disclosure files in R2
   - Supabase reserved for query-critical structured rows
7. Authentication and billing
   - Supabase email/Google authentication
   - Razorpay order, verification, subscription, and webhook flows

## Primary Users
- Retail investors doing self-directed research
- Internal operators/admin users monitoring data quality and workflow health

## Out of Scope (Current Phase)
- feature flags manager
- full audit logs UI
- trade execution, portfolio custody, or personalized investment advice
- autonomous parser decisions without bounded admin review
