# MF Disclosure Pipeline Cold-Start Runbook

**Snapshot date:** 2026-09-19
**Reason:** the 2026-09-15 OCI self-hosted cutover recreated the schema from tracked migrations but migrated **no data** (`docs/08_DEPLOYMENT.md`). The disclosure staging pipeline is therefore empty, and several scheduled workflows fail loudly rather than reporting false success. This runbook is the ordered procedure to seed it.

Use alongside `docs/jobs.md` (workflow inventory) and `docs/MF_12_AMC_PRODUCTION_READINESS_RUNBOOK.md` (stage boundaries and approval rules).

## 1. Why the workflows fail on a cold database

These failures are **correct behavior**, not defects. Each job refuses to report success with no upstream data:

| Workflow | Failure | Cause |
|---|---|---|
| `sync-mf-disclosures` (`coverage` job) | exit 1, `failed_strict_amcs: [<amc>]` | strict coverage gate requires promoted data; staging is empty |
| `index-mf-research` | exit 1 | `available_document_count: 0` and the job runs with `--minimum-available 1` |
| `mf-sync` | exit 1, `no_supported_metric_targets` | `supported_metric_targets()` needs `mapped_scheme_code` + `mapped_family_id` from `mf_factsheet_candidates`; returns 0 targets when empty |

A permission error looks similar but is different: `42501 permission denied ... hint: GRANT ... TO anon` means a server component is running with the **anon** key. See section 5.

## 2. Non-negotiable boundaries

- Use only official AMC / AMFI sources.
- Discovery success is not acquisition success; acquisition is not parsing; parsing is not mapping approval; mapping approval is not runtime promotion.
- `sync-mf-disclosures` forces `parse_only=true`. It never acquires. **Acquire first** with `acquire-mf-documents`.
- `acquire-mf-documents` writes live documents to R2 and the database. It is manual, runs in the `production-data` environment, and requires the exact approval phrase.
- `mf_amc_sources` gates scope. Only enabled AMCs are processed.

## 3. Ordered cold-start procedure

### Step 0 — Confirm the server-side keys are service-role

Every Python job connects with `SUPABASE_KEY`. In self-hosted deployments this must be the **service_role** JWT:

- GitHub Actions: repository secret `SUPABASE_KEY`.
- Cloud Run: `SUPABASE_KEY` env on the `fundersai-git` service.
- Local `.env` / `backend/.env`: `SUPABASE_KEY`.

Verify the role without printing the secret:

```powershell
# decode the JWT payload (middle segment) and confirm {"role":"service_role"}
```

See `docs/08_DEPLOYMENT.md` for the Cloud Run verification command. An anon key here produces `42501 permission denied` on every service-role-only table.

### Step 1 — Discover official documents (scheduled)

`discover-mf-documents.yml` runs `15 3 * * 1-5`. It writes `mf_discovery_runs` and `mf_discovery_documents`. Discovery is manifest-only; it does not ingest.

```bash
gh workflow run discover-mf-documents.yml
```

Verify the run row and candidate documents before acquiring.

### Step 2 — Acquire approved documents (manual, gated)

Downloads the official file, stores it in R2, and creates a `mf_raw_documents` row with `parse_status='pending'`.

```bash
gh workflow run acquire-mf-documents.yml \
  -f amc=ppfas \
  -f document_scope=all \
  -f expected_month=2026-08 \
  -f max_documents=3 \
  -f approval_phrase="ACQUIRE 2026-08 ppfas"
```

- `approval_phrase` must be exactly `ACQUIRE <YYYY-MM> <amc>`.
- The run pauses for a required-reviewer approval on the `production-data` environment. Approve it in the Actions UI.
- `document_scope`: `all`, `factsheet`, or `portfolio_disclosure`.

### Step 3 — Parse staged documents (scheduled)

`sync-mf-disclosures.yml` forces `parse_only=true` and parses pending rows into staging.

```bash
gh workflow run sync-mf-disclosures.yml \
  -f amcs=ppfas -f parse_only=true -f parse_limit=50 -f parse_rounds=1
```

This writes `mf_factsheet_candidates`, `mf_scheme_holdings`, and `mf_scheme_monthly_metrics`, and advances `mf_raw_documents.parse_status`.

Note: if `MF_LLM_EXTRACTOR_MODEL` is unset, the parser logs `llm_primary_unavailable reason=mf_llm_extractor_model_missing` and falls back to deterministic extraction. Set the variable if LLM extraction is intended.

### Step 3b — Digital factsheet and complementary-source merge (PPFAS)

PPFAS publishes a **digital (HTML) factsheet** alongside the PDF, at a deterministic per-month URL:

```
https://amc.ppfas.com/downloads/digital-factsheet/<year>/<month>-<year>/
```

It is server-rendered HTML containing every scheme's AUM, expense ratio and benchmark in one page, so it fills the `aum` gap the PDF path leaves:

| Field | PDF factsheet | Digital factsheet |
|---|---|---|
| `aum` | not extracted | **7/7** |
| `expense_ratio` | 3/7 | **7/7** |
| `benchmark` | 7/7 (some table-header noise) | **7/7** |
| `fund_manager` | 7/7 | 7/7 |
| `risk_level` | **7/7** (text Risk-o-Meter) | varies — image, and some months omit the table |

Because the two sources are complementary, both are ingested and their fields are **merged per scheme** (`backend/app/mf_ingestion/services/field_merge.py`):

- `aum`, `expense_ratio`, `benchmark`, `fund_manager` prefer the digital sheet.
- `risk_level` prefers the PDF.
- The winning source per field is recorded in `field_sources`, so provenance is inspectable.
- The merge is order-independent and idempotent, and only fills gaps — it never overwrites a value the selected document already produced.

This runs automatically inside `parse_pending_documents` after parsing (`_reconcile_factsheet_field_merges`). Discovery for PPFAS returns the digital candidate alongside the PDF candidates; because the digital sheet is scored higher it sorts first, and the merge guarantees the PDF's `risk_level` still reaches the same candidate rows.

Configuration: `MF_PPFAS_DIGITAL_FACTSHEET_BASE_URL` overrides the base URL. Set it to empty to disable digital discovery for PPFAS.

### Step 3c — Layout-drift detection (the self-healing signal)

Official factsheets change shape without notice and the parser reports no error — a field simply stops extracting. The 2026-08 vs 2026-07 PPFAS digital sheets are a concrete case: the Risk-o-Meter table exists in August and is absent entirely in July, so `risk_level` yield collapses from 6/7 to 0/7.

Every factsheet parse now records a **layout fingerprint** (per-field yield) into `mf_raw_documents.storage_metadata.layout_fingerprint`, and compares it against the previous factsheet for the same AMC. When a field the previous layout supplied reliably collapses, the document gets a `layout_drift_field_yield_lost` issue and a warning log line `event=layout_drift_detected`.

This is **detection only, by design**: the agent flags the drift and routes the document to review. It never rewrites parser code or auto-applies a fix. The fingerprint and drift evidence are stored so an operator can see exactly which field was lost and compare the current vs baseline yields.

Inspect drift evidence:

```sql
select id, source_url,
       storage_metadata -> 'layout_fingerprint' as fingerprint,
       storage_metadata -> 'layout_drift'       as drift,
       validation_issues
from public.mf_raw_documents
where storage_metadata ? 'layout_drift'
order by parsed_at desc;
```

### Step 4 — Generate the fund family mapping (manual, not wired to any workflow)

`mf_factsheet_candidates.mapped_family_id` and the promotion jobs both depend on `mutual_fund_family_mapping`. **No workflow populates it.** Run the script locally with a service-role key:

```powershell
.\.venv\Scripts\python.exe backend\scripts\generate_family_mapping.py
```

It reads `mutual_fund_core_snapshot.scheme_name`, derives a cleaned family name, and upserts `scheme_code / family_id / confidence / source='auto-group-script-v1'`.

Preview before writing when the scheme universe has changed. The script has no `--dry-run`; compute the mapping read-only first and confirm:

- distinct families and the largest family sizes;
- singleton families (a large singleton share is normal — most schemes are unique);
- **families spanning more than one AMC**, which indicate an over-broad name merge and must be investigated before promotion.

Run this **before** parsing. Candidates are mapped at parse time, so a parse that runs first writes `needs_review` for every scheme whose family is not yet known. Re-parsing after this step is idempotent but costs a full parse cycle.

### Step 4b — Backfill `amc_name` (manual, not wired to any workflow)

`mutual_fund_core_snapshot.amc_name` is NULL for most AMFI NAVAll rows. The parser, family-invariant propagation, and promotion conflict detection all resolve the AMC from this column, so a NULL demotes every affected scheme to review.

```powershell
.\.venv\Scripts\python.exe backend\scripts\backfill_mf_amc_name.py --dry-run
.\.venv\Scripts\python.exe backend\scripts\backfill_mf_amc_name.py
```

- Fills NULL/empty values only; an existing label is never overwritten.
- Writes the canonical registry label (for example `HDFC Mutual Fund`) for rows whose scheme name resolves to a supported AMC.
- Leaves unsupported AMCs (Franklin, ITI, Union, Samco, TRUSTMF, …) untouched.

Runtime resolution no longer depends on the column: `parsing_service._snapshot_matches_amc`, `promote_mf_disclosures.build_family_invariant_propagation_plan`, and `promotion_review_service` fall back to the scheme name through the shared marker map. The backfill keeps the data accurate and makes the column usable for display and diagnostics.

### Step 5 — Review and promote (manual, gated)

Parsed candidates land in `needs_review`. Promotion is a separate deliberate step:

- Resolve candidates via `promote-mf-disclosures.yml` (manual, `production-data` environment) or the admin promotion-review surface.
- Review the 7-field scope independently: `risk`, `ter_aum`, `benchmark`, `manager`, `holdings`, `sectors`.
- Never promote missing overlap as `0%`; represent it as unavailable.

### Step 6 — Index official documents (scheduled)

`index-mf-research.yml` runs `15 10 * * 1-5` and writes `amc_document_chunks`. It needs parsed PDF rows:

- `--minimum-available 1` means it exits 1 when there are no parsed PDFs (the cold-start symptom).
- Direct OpenAI embeddings need `OPENAI_API_KEY`; lexical-only chunks remain usable by the default retrieval path.

### Step 7 — Verify

- `GET /api/data-health`: the `AMC docs` metric moves off `Missing`.
- `GET /api/mf/<scheme_code>` returns 200 for a funded scheme.
- Re-run `sync-mf-disclosures` and confirm the `coverage` job passes.

## 4. Known non-blocking warnings

- `Langfuse client initialized without public_key` — tracing is optional and feature-flagged; the client disables itself.
- `no_links_found:<AMC>` during preflight — expected when a source page has nothing new for the target month.
- `amfi_missing_supported_amc:<AMC>` — AMFI did not list that AMC's schemes for the checked month.

## 5. Permission-denied triage

```
42501 permission denied for table <t>, hint: GRANT ... TO anon
```

- **Service-role-only table** (e.g. `mf_raw_documents`, `mf_factsheet_candidates`, `mf_discovery_runs`, `nav_api_cache`, `mutual_funds`): the caller is using the anon key. Fix the key; do not grant anon access.
- **Public reference table**: check that `20260919_harden_public_schema_privileges.sql` is applied and that the caller is server-side.

## 6. Cold-start state recorded (2026-09-19)

After the OCI cutover and before recovery, the disclosure tables were empty (`mf_raw_documents`, `mf_factsheet_candidates`, `mf_scheme_monthly_metrics`, `mutual_fund_family_mapping`, `amc_document_chunks` all 0), which is what triggered the workflow failures above.

Recovery steps executed in this order (PPFAS, report month `2026-08`):

1. `discover-mf-documents` — 3 candidate documents recorded.
2. `acquire-mf-documents` — 4 raw documents stored to R2 (`raw/ppfas/2026-08/...`), `parse_status='pending'`.
3. `sync-mf-disclosures` (parse) — 3 documents `parsed`, 1 `needs_review`.
4. `generate_family_mapping.py` — 2,333 mappings across 2,167 families.

Resulting state:

| Table | Rows |
|---|---|
| `mf_raw_documents` | 4 (3 parsed, 1 needs_review) |
| `mf_factsheet_candidates` | 7 (all `needs_review`) |
| `mf_scheme_holdings` | 212 |
| `mf_scheme_monthly_metrics` | 3 |
| `mutual_fund_family_mapping` | 2,333 (2,167 families) |
| `amc_document_chunks` | 0 |
| `mutual_fund_core_snapshot` | 2,333 |
| `mf_amc_sources` enabled | 1 / 1 (PPFAS) |

Follow-up on 2026-09-19 resolved the candidate review state:

- `backfill_mf_amc_name.py` filled 2,005 of 2,229 NULL `amc_name` rows (224 unsupported AMCs left NULL), reducing the NULL count from 2,229 to 224.
- The candidate-mapping code now infers the AMC from the scheme name when `amc_name` is missing, so mapping no longer depends on the backfill.
- All 4 PPFAS documents were re-parsed: `mf_raw_documents` = 4 parsed, and all **7 candidates are `mapped` at 100.00 confidence with `promotion_status='staged'`** (`needs_review` = 0).

Remaining work is the **review and promotion** stage, which is human-gated by design. `index-mf-research` stays failing until parsed PDFs exist; `mf-sync` stops reporting `no_supported_metric_targets` once candidates are promoted.

### Open items

- The 7 PPFAS candidates are now `staged` and await promotion decision (`promote-mf-disclosures.yml`, manual, `production-data` gate).
- `MF_LLM_EXTRACTOR_MODEL` is unset, so `llm_then_deterministic` silently degrades to deterministic extraction.
- Only PPFAS is enabled in `mf_amc_sources`. Widening scope is a deliberate operator decision.
- 224 snapshot rows for unsupported AMCs keep a NULL `amc_name`. They are out of supported scope; add the AMC to `sources/registry.py` before expecting them to resolve.
