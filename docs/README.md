# Documentation Index

**Last updated:** 2026-09-17

## Authoritative Current Documents

Read these in order for current implementation work:

1. `../Agents.md` — repository rules, runtime boundaries, test conventions
2. `CURRENT_STATE.md` — implemented, locally verified, deployed, and remaining gaps
3. `00_PROJECT_OVERVIEW.md` — product and repository orientation
4. `01_PRODUCT_SPEC.md` — current product scope
5. `02_ARCHITECTURE.md` — component and data-flow boundaries
6. `03_API_CONTRACTS.md` — frontend/backend routes, authentication, rate limits, errors
7. `04_DATABASE_SCHEMA.md` — tables, ownership, RLS, caches, migration order
8. `05_FRONTEND_GUIDE.md` and `06_BACKEND_GUIDE.md` — implementation guides
9. `08_DEPLOYMENT.md` — production topology, self-hosted Supabase operations, environment, migration, and release checks
10. `09_DECISIONS.md` — accepted architectural decisions
11. `10_TASKS.md` — active work, completed work, and known issues
12. `11_ML_SYSTEMS.md` — implemented/experimental ML and retrieval boundaries

`jobs.md`, `providers.md`, `12_INTERVIEW_GUIDE.md`, `13_DISCOVERY_AGENTS.md`, `14_BUILD_WEEK_DEMO_VIDEO.md`, and `MF_COMPARISON_COVERAGE_REPAIR.md` are maintained supporting references.

Use `MF_12_AMC_PRODUCTION_READINESS_RUNBOOK.md` for the current June 2026 twelve-AMC execution order, approval boundaries, coverage gates, and production verification steps.

Use `MF_DISCLOSURE_COLD_START_RUNBOOK.md` when the disclosure staging tables are empty (for example after the self-hosted cutover) and the scheduled MF workflows fail on missing upstream data. It records the ordered discovery → acquisition → parse → family-mapping → review/promotion procedure.

## Evidence Snapshots

These files describe a specific test or implementation stage. Their dates and tested commit take precedence over generic words such as “current” inside the report:

- `LIVE_LOGIN_CHAT_E2E_2026-07-21.md`
- `DAY_12_EVALUATION.md`
- `DAY_13_OBSERVABILITY.md`
- `mf_pipeline_verification_report.md`

Do not use an evidence snapshot to claim that a later commit is deployed unless the report explicitly tested that commit.

## Historical and Supplemental Documents

- `HISTORY.md` records concise, dated evidence that no longer belongs in current-state documentation.
- `MF_12_AMC_PRODUCTION_READINESS_RUNBOOK.md`, `MF_CATALOG_ROLLOUT.md`, and `AWS_K3S_DEPLOYMENT.md` are operator runbooks. Follow them only alongside the current architecture and deployment documents.

Stale root-level summaries and the earlier duplicate overview/schema documents were removed on 2026-09-17. Use this index rather than retaining parallel architecture narratives.

## Maintenance Rules

- Route/auth/rate-limit changes: update `03_API_CONTRACTS.md`.
- Database, auth, or self-hosted Supabase changes: update `CURRENT_STATE.md`, `02_ARCHITECTURE.md`, `04_DATABASE_SCHEMA.md`, and `08_DEPLOYMENT.md`.
- Provider/workflow changes: update `providers.md`, `jobs.md`, and `CURRENT_STATE.md`.
- Product feature changes: update `01_PRODUCT_SPEC.md`, `CURRENT_STATE.md`, and `10_TASKS.md`.
- Live verification: record domain, tested commit, timestamp, result, and production logs without overwriting historical evidence.
