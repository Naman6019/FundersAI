# Agent Workflow

**Last updated:** 2026-07-21

## Start of Work

1. Read `Agents.md`, `docs/CURRENT_STATE.md`, and the focused document for the subsystem being changed.
2. Inspect `git status` and preserve unrelated user changes.
3. For codebase questions, use the targeted Graphify query required by `Agents.md` when the tool is operational; otherwise report the failure and inspect source directly.
4. Separate current code, local verification, deployed behavior, and planned work.

## Editing and Coordination

- Use one active editing agent for overlapping files. Parallel agents are safe only for bounded, independent work.
- Do not make database-destructive changes without the documented readiness gate and explicit authorization.
- Do not expose provider, Supabase service-role, Razorpay, R2, or internal proxy secrets.
- Keep browser traffic behind Next.js `/api/*`; internal FastAPI/admin boundaries stay server-side.
- Preserve research-only language and official-AMC-source constraints.

## Verification

1. Run focused tests for the changed behavior.
2. Run the relevant backend/frontend suites in proportion to risk.
3. Run type-check, lint, build, and `git diff --check` when frontend or release contracts change.
4. Live/deployment claims require matching Browser, platform, migration, or runtime-log evidence.

## Documentation Closeout

- Update `CURRENT_STATE.md` for implementation or deployment changes.
- Update `03_API_CONTRACTS.md` when a route, auth rule, rate limit, or error contract changes.
- Update `04_DATABASE_SCHEMA.md` and `08_DEPLOYMENT.md` when migrations or environment requirements change.
- Update `10_TASKS.md` by moving completed work and recording remaining gates.
- Do not turn a local test result into a production claim.
