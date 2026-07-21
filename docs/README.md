# Documentation Index

**Last updated:** 2026-07-22

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
9. `08_DEPLOYMENT.md` — production topology, environment, migration, and release checks
10. `09_DECISIONS.md` — accepted architectural decisions
11. `10_TASKS.md` — active work, completed work, and known issues
12. `11_ML_SYSTEMS.md` — implemented/experimental ML and retrieval boundaries

`jobs.md`, `providers.md`, `12_INTERVIEW_GUIDE.md`, `13_DISCOVERY_AGENTS.md`, `14_BUILD_WEEK_DEMO_VIDEO.md`, and `MF_COMPARISON_COVERAGE_REPAIR.md` are maintained supporting references.

## Evidence Snapshots

These files describe a specific test or implementation stage. Their dates and tested commit take precedence over generic words such as “current” inside the report:

- `LIVE_LOGIN_CHAT_E2E_2026-07-21.md`
- `DAY_12_EVALUATION.md`
- `DAY_13_OBSERVABILITY.md`
- `mf_pipeline_verification_report.md`

Do not use an evidence snapshot to claim that a later commit is deployed unless the report explicitly tested that commit.

## Legacy or Supplemental Documents

`PROJECT_SUMMARY.md`, `TECHNICAL_OVERVIEW.md`, `data-architecture.md`, `database-schema.md`, `deprecated-stock-paths.md`, and `no-screener-migration.md` preserve earlier context. When they conflict with the authoritative list above, use the authoritative document and current source code.

## Maintenance Rules

- Route/auth/rate-limit changes: update `03_API_CONTRACTS.md`.
- Migration/table/RLS changes: update `04_DATABASE_SCHEMA.md` and `08_DEPLOYMENT.md`.
- Provider/workflow changes: update `providers.md`, `jobs.md`, and `CURRENT_STATE.md`.
- Product feature changes: update `01_PRODUCT_SPEC.md`, `CURRENT_STATE.md`, and `10_TASKS.md`.
- Live verification: record domain, tested commit, timestamp, result, and production logs without overwriting historical evidence.
