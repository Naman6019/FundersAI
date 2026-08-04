# Database Schema

**Last updated:** 2026-08-04

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
- `mutual_fund_core_snapshot`: query-critical fund snapshot. `20260722_repair_flexi_cap_comparison_metadata.sql` idempotently repairs verified category, benchmark, and risk metadata for scheme codes `118955` and `122639`, with official source provenance in `provider_payload`.
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
- `mf_scheme_sector_allocations` (`20260728_add_mf_sector_allocation_staging.sql`, locally verified; migration pending)
  - Stores official aggregate sector weights separately from security holdings, with raw scheme names, reviewed scheme/family mappings, source-document evidence, and validation state.
- `mf_report_month_corrections` (`20260728_add_mf_report_month_reconciliation.sql`, locally verified; migration pending)
  - Append-only service-role audit records for body- and checksum-verified raw-document month corrections. The correction clears only that document's stale staging rows and queues it for reparse.
- `mf_staging_holding_coverage_rows` and `mf_staging_sector_coverage_rows` (`20260728_add_mf_staging_coverage_rpc.sql`, locally verified; migration pending)
  - Read-only, service-role-only RPCs that collapse large security-level staging tables to one coverage-evidence row per scheme/family.
- `mf_scheme_monthly_metrics`
- `mf_parse_review_queue`
- `mf_r2_archive_manifests`
- `mf_discovery_runs`
  - One server-only summary per hosted discovery supervisor run.
  - Stores agent/document counts, checksum-addressed R2 evidence keys, and idempotent persistence state.
  - RLS is enabled; `anon` and `authenticated` have no table privileges; `service_role` performs workflow upserts.
- `mf_discovery_documents`
  - Server-only checksum/readiness observations keyed to one discovery run and monthly document identity.
  - Retains last-known-good candidates and evidence without invoking raw-document ingestion.
  - `month_confirmation` accepts `confirmed`, `content_confirmed`, and `unconfirmed`; `content_confirmed` means the downloaded body verified the reporting month.
- `mf_factsheet_candidates` (`20260727_add_mf_extraction_staging_and_promotion.sql`, production presence verified 2026-07-27)
  - Preserves raw and normalized AMC scheme names, reviewed scheme/family mappings, extracted fields, source/R2/checksum evidence, parser version, and per-scope promotion state.
- `mf_promotion_runs` (`20260727_add_mf_extraction_staging_and_promotion.sql`, production presence verified 2026-07-27)
  - Service-role-only audit rows for dry-run validation and applied, scoped promotions.
- `promote_mf_factsheet_candidate(...)` and `promote_mf_holdings_document(...)`
  - Revalidate reviewed mappings and promote only requested scopes. Rejected or partial candidates do not clear last-known-good runtime rows.
  - The four-argument factsheet function is atomic and does not delegate to the legacy RPC. The pending sector-staging migration makes holdings and aggregate-sector promotion independently validated.

Raw document bytes belong in Cloudflare R2. Supabase stores the object location and query-critical structured output.

## Official-Document Research

- `amc_document_chunks`
  - Versioned document chunks with source URL, parser metadata, report month, content hash, embedding metadata, and pgvector embedding.
  - Used by deterministic lexical retrieval and the opt-in vector RPC.
  - `20260721_harden_amc_document_chunks.sql` repairs the additive indexing columns, enforces document/chunk uniqueness, and makes the table service-role-only.
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

## Feedback

- `user_feedback`
  - Stores 1-5 ratings and optional comments for general app, individual response, and post-logout feedback.
  - Authenticated app/response rows store `user_id`; response rows may reference an owned `ai_chat_messages` row, chat session, and trace ID.
  - Logout rows may be anonymous because feedback is collected after the Supabase session is cleared.
  - RLS is enabled. `anon` and `authenticated` have no table privileges; `service_role` is limited to `select` and `insert` for this table.

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
  - stale unfinished `running` rows are reconciled to `timed_out`; the partial `(status, started_at)` index supports bounded reconciliation scans.
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
5. `20260721_harden_amc_document_chunks.sql`
6. `20260721_add_user_feedback.sql`
7. `20260721_ensure_user_feedback_storage.sql` (idempotently creates the table, reapplies least-privilege grants, and reloads the PostgREST schema cache)
8. `20260722_repair_flexi_cap_comparison_metadata.sql`
9. `20260723_add_discovery_v2_history.sql`
10. `20260727_add_mf_extraction_staging_and_promotion.sql` (production schema presence verified 2026-07-27; no promotion was applied during verification)
11. `20260728_allow_content_confirmed_discovery_month.sql` (required before the updated discovery supervisor can persist body-confirmed observations)
12. `20260728_add_mf_sector_allocation_staging.sql`
13. `20260728_add_mf_staging_coverage_rpc.sql`
14. `20260728_add_mf_report_month_reconciliation.sql`
15. `20260728_add_mf_promotion_eligible_coverage_rpc.sql`
16. `20260805_index_stale_data_provider_runs.sql`
16. `20260728_add_mf_thresholded_portfolio_promotion_v2.sql`
17. `20260728_fix_mf_promotion_provider_payload.sql`
18. `20260728_harden_mf_promotion_rpc_contract.sql`
19. `20260728_make_mf_factsheet_promotion_atomic.sql`

Equivalent production SQL is not a substitute for keeping the migration in version control.
