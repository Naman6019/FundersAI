# Database Schema

**Last updated:** 2026-07-21

FundersAI uses Supabase PostgreSQL for structured application data and authentication. Browser access is limited by Row Level Security (RLS); service-role writes are server-side only.

## Core Stock Tables

- `stocks`
- `stock_prices_daily`
- `financial_statements`
- `ratios_snapshot`
- `shareholding_pattern`
- `corporate_events`
- `stock_core_snapshot`

## Core Mutual-Fund Tables

- `mutual_funds`: compatibility/source table
- `mutual_fund_core_snapshot`: query-critical fund snapshot
- `mutual_fund_nav_history`: normalized historical table retained until the archive and drop-readiness gate passes
- `mutual_fund_holdings`
- `mutual_fund_sectors`
- `mutual_fund_family_mapping`

## Runtime Cache Tables

- `nav_api_cache`
  - Server-only cache for complete MFapi NAV-history payloads.
  - RLS enabled; `anon` and `authenticated` have no access; `service_role` has full access.
- `provider_response_cache`
  - Provider/endpoint response cache with expiry metadata.
  - `20260721_harden_provider_response_cache_rls.sql` enables RLS, revokes `public`, `anon`, and `authenticated`, and grants CRUD to `service_role`.
- `provider_endpoint_health`
- `provider_ingestion_logs`

## Official AMC Disclosure Pipeline

- `mf_amc_sources`
- `mf_raw_documents`
  - Stores source, parse status, checksum, report month, R2 location, and parser/debug metadata.
  - Active states include `pending`, `downloaded`, `needs_reparse`, `parsed`, `parsed_partial`, `needs_review`, `failed`, and `skipped_not_supported`.
- `mf_schemes`
- `mf_scheme_holdings`
- `mf_scheme_monthly_metrics`
- `mf_parse_review_queue`
- `mf_r2_archive_manifests`
- `mf_discovery_runs`
  - One server-only summary per hosted discovery supervisor run.
  - Stores agent/document counts and the R2 keys for the immutable report and validated manifest.
  - RLS is enabled; `anon` and `authenticated` have no table privileges; `service_role` performs workflow upserts.

Raw document bytes belong in Cloudflare R2. Supabase stores the object location and query-critical structured output.

## Official-Document Research

- `amc_document_chunks`
  - Versioned document chunks with source URL, parser metadata, report month, content hash, embedding metadata, and pgvector embedding.
  - Used by deterministic lexical retrieval and the opt-in vector RPC.
- `match_document_chunks(...)`
  - pgvector similarity function used only when vector retrieval is enabled.

## User and Access Control

- `user_profiles`
  - `user_id`: Supabase auth user UUID
  - `role`: `user | admin | tester`
  - `tier`: `free | pro | ultra`
  - activity and lifecycle timestamps
- RLS policies allow users to read their own profile; server-side admin checks control privileged reads and role/tier mutations.

## Chat Persistence

### Current owned-session model

- `ai_chat_sessions`
  - Owned by `user_id` and ordered by `updated_at`.
  - RLS policy restricts rows to `auth.uid() = user_id`.
- `ai_chat_messages`
  - Contains `session_id`, `user_id`, `role`, `content`, `metadata`, and `created_at`.
  - Foreign keys require a valid owned session and user.
  - RLS validates both message ownership and matching session ownership.

The Next.js proxy uses the service role only after authenticating the user and checking session ownership.

### Legacy history model

- `chat_messages`
  - Older per-user history used by `/api/chat/history`.
  - RLS restricts select/insert/delete operations to the owning user.

## Billing

- `billing_subscriptions`: Razorpay subscription, plan, tier, status, and period data
- `billing_events`: verified webhook event identifiers and metadata for idempotency
- `ai_usage_events`: token reservation/finalization and tier-budget accounting

## Observability and Job Telemetry

- `data_provider_runs` and legacy-compatible `provider_runs`
- `provider_usage_logs`
- `data_quality_issues`

## Legacy and Drop Safety

- `mutual_fund_history`, `stock_history`, and `stock_fundamentals` were removed or compacted as legacy heavy tables.
- `mutual_fund_nav_history` is a separate normalized table and is not covered by that statement.
- Its manual drop remains gated by an R2 archive, the observation window, zero runtime legacy reads, `check_nav_cache_drop_readiness.py`, and explicit SQL acknowledgement. See `docs/08_DEPLOYMENT.md`.

## Migration Order for the July 2026 Chat/Cache Changes

1. `20260717_nav_api_cache.sql`
2. `20260721_add_ai_chat_sessions_and_messages.sql`
3. `20260721_harden_provider_response_cache_rls.sql`
4. `20260721_add_mf_discovery_runs.sql`

Equivalent production SQL is not a substitute for keeping the migration in version control.
