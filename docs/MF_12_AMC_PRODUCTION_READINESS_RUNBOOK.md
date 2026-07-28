# Twelve-AMC Production Readiness Runbook

**Snapshot date:** 2026-07-28 IST  
**Reporting month:** `2026-06-01`  
**Pushed commit inspected:** `763ace5d`  
**Current result:** 5 of 12 AMCs pass the June staging coverage gate. No June disclosure scope has been promoted or activated for users.

This is the execution and verification guide for taking HDFC, SBI, ICICI, Axis, PPFAS, Nippon, Motilal, Mirae, UTI, DSP, Kotak, and Aditya Birla Sun Life from official-source discovery to production runtime data.

## 1. Non-negotiable boundaries

The pipeline is split into six independent stages:

1. Discovery finds and validates official candidates.
2. Acquisition downloads approved files and stores raw evidence in R2.
3. Parsing writes extracted values, mappings, diagnostics, and review state to staging.
4. Indexing prepares official-document evidence for cited research answers.
5. Promotion copies reviewed scopes into runtime tables.
6. Live acceptance verifies API, chat, canvas, and Data & Trust behavior.

The following rules always apply:

- Use only official AMC or AMFI sources.
- Discovery success is not acquisition success.
- Acquisition success is not parser success.
- Parser success is not mapping approval.
- Mapping approval is not runtime promotion.
- Never promote missing overlap as `0%`; represent it as unavailable.
- Preserve last-known-good runtime data when a candidate is partial, rejected, stale, ambiguous, or missing.
- Promote `risk`, `ter_aum`, `benchmark`, `manager`, `holdings`, and `sectors` independently.
- One AMC may fail without modifying or blocking an already accepted AMC.
- Read-only refresh actions must never start discovery, acquisition, parsing, or promotion.

## 2. Current approval, migration, and secret state

### Approved

- Bounded acquisition of official June 2026 documents is approved.
- Per-scope promotion is approved after the AMC passes the staging, mapping, and dry-run gates in this runbook.
- `20260728_allow_content_confirmed_discovery_month.sql` has been applied and its production constraint was verified.
- The `Production-data` GitHub environment exists.
- Required reviewer: `Naman6019`.
- Deployment branch policy: `main`.
- Self-review is allowed.

### Not approved

- Enabling a new AMC for users.
- Deploying backend/frontend behavior for this work.

### Migration state

- `20260727_add_mf_extraction_staging_and_promotion.sql` is present in production. Its staging tables are being queried and written successfully.
- `20260728_allow_content_confirmed_discovery_month.sql` is applied in production.
- Production verification on 2026-07-28 confirmed that `month_confirmation` accepts `confirmed`, `content_confirmed`, and `unconfirmed`.

Applied migration:

```text
backend/migrations/20260728_allow_content_confirmed_discovery_month.sql
```

Verification query:

```sql
select
  conname,
  pg_get_constraintdef(oid) as definition
from pg_constraint
where conrelid = 'public.mf_discovery_documents'::regclass
  and conname = 'mf_discovery_documents_month_confirmation_check';
```

Verified pass condition:

```text
month_confirmation in ('confirmed', 'content_confirmed', 'unconfirmed')
```

### Secrets

No new secret is required. The existing workflows require:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `R2_ENDPOINT`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_RAW_BUCKET`
- `R2_COLD_BUCKET`

Never print secret values in logs, reports, test fixtures, or this document.

## 3. Current June coverage snapshot

The following snapshot was produced with:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe backend\scripts\report_mf_staging_coverage.py `
  --report-month 2026-06-01
```

The gate requires at least 80% for:

- reviewed core mapping;
- reviewed portfolio mapping;
- AUM;
- TER;
- benchmark;
- manager;
- risk;
- holdings;
- sectors.

| AMC | Core map | Portfolio map | AUM | TER | Benchmark | Manager | Risk | Holdings | Sectors | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| HDFC | 97.67% | 100.00% | 60.71% | 57.14% | 100.00% | 1.19% | 0.00% | 100.00% | 97.62% | Fail |
| SBI | 92.47% | 85.47% | 93.02% | 98.84% | 94.19% | 89.53% | 100.00% | 100.00% | 100.00% | Pass |
| ICICI | 98.48% | 98.56% | 96.92% | 100.00% | 98.46% | 89.23% | 100.00% | 100.00% | 100.00% | Pass |
| Axis | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | Fail |
| PPFAS | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | Pass |
| Nippon | 98.72% | 100.00% | 100.00% | 67.53% | 85.71% | 98.70% | 0.00% | 100.00% | 95.95% | Fail |
| Motilal | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | Fail |
| Mirae | 98.90% | 97.75% | 100.00% | 95.56% | 96.67% | 97.78% | 81.11% | 100.00% | 100.00% | Pass |
| UTI | 90.28% | 97.47% | 100.00% | 4.62% | 36.92% | 12.31% | 6.15% | 100.00% | 98.70% | Fail |
| DSP | 98.57% | 87.21% | 100.00% | 98.55% | 100.00% | 81.16% | 100.00% | 100.00% | 100.00% | Pass |
| Kotak | 95.73% | 0.00% | 97.32% | 96.43% | 98.21% | 96.43% | 99.11% | 0.00% | 0.00% | Fail |
| Aditya Birla | 0.00% | 91.30% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 97.33% | Fail |

Current full passes:

- SBI
- ICICI
- PPFAS
- Mirae
- DSP

A staging pass is necessary but not sufficient. These five AMCs still need reviewed dry-run promotion, approved per-scope promotion, and live acceptance before `runtime_enabled` can be set.

## 4. Acquisition and parser evidence

### Completed bounded acquisition runs

| AMC | GitHub run | Result | Exact evidence |
|---|---:|---|---|
| HDFC | `30305219624` | Success | Factsheet `709eef10-07a1-4098-b1b0-618234709f08`; portfolio scope `d339e170-226d-4dfe-8062-c895a87c2c0d` |
| Nippon | `30306027811` | Success | Factsheet `3467027f-8e1f-403e-9d1c-564847a84aea`; portfolio `4d0896bd-350c-4415-94ed-c7e526c95689` |
| UTI | `30306027002` | Success | Factsheets `b461d757-f0cc-422f-9f93-ae901e02f3b9`, `2d14d3ce-bf13-4c81-ae02-7a679310e68a`, `902d3b93-0f91-4de5-9705-0c0c699b726e`; portfolio `55de0678-55c3-4cb5-806e-635f1d14909c` |
| DSP | `30306027038` | Success | Factsheet `b2d2e47e-dd42-4269-913a-7344af2c1900`; portfolio `5a1f155b-9682-41ba-8792-7b2f5cd50054` |
| Aditya Birla | `30306027790` | Partial | Portfolio `6f7605ce-94fd-4e34-a615-6bd4d4cc1bda`; factsheet not acquired |
| Motilal | `30343045400` | Success | Factsheet `c9672b76-3d3b-40c1-82c1-2c8332b2b5ed`; combined-factsheet portfolio scope `b4cd5573-86de-435e-b1a4-8e69bbbeac94`; checksum `775df336…8187e2` |
| Kotak | `30343047236` | Success | Exact factsheet reused as `c5a4caa8-9333-47b3-b3ef-6818b83499b3`; combined-factsheet portfolio scope `2be39e47-a388-43c4-8247-4c53a7849d5f`; checksum `caac224b…1ff7b0` |
| Aditya Birla | `30343049424` | Success | Exact June factsheet `9c59868e-f45a-489b-9663-2803e8b11599`; checksum `f24c7d81…509738` |

Exact deterministic parser run `30343289910` produced:

- Motilal: 20 schemes and 685 holdings rows per scope; 675 rows valid and 10 held for review.
- Kotak: 76 schemes and 3,571 holdings rows per scope; 2,869 rows valid and 702 held for review.
- Aditya Birla: no mutation; the document stayed `pending` because retry filtering did not resolve `aditya_birla` to database code `ABSL`.

The retry alias fix must be pushed before retrying only ABSL source document `9c59868e-f45a-489b-9663-2803e8b11599`.

### Failed reruns after the reviewed fallback was pushed

| AMC | GitHub run | Failure | Cause |
|---|---:|---|---|
| Axis | `30307496928` | `no_documents_found` for both scopes | The acquisition workflow did not set `MF_SOURCE_MANIFEST_PATH`; the Axis adapter therefore checked only env/page/AMFI. |
| Aditya Birla | `30307492897` | Factsheet `no_documents_found`; portfolio `not_modified` | The reviewed June-content factsheet is published under a July filename. Acquisition did not load the reviewed manifest fallback. |

The local workflow fix adds:

```yaml
MF_SOURCE_MANIFEST_PATH: backend/config/mf_document_sources.json
```

This change must be committed and pushed before rerunning Axis or Aditya Birla acquisition.

### Current exact-month raw parser state

- HDFC: two `parsed_partial` rows.
- SBI: one `parsed`, two `parsed_partial`.
- ICICI: two `parsed`, one `parsed_partial`.
- PPFAS: three `parsed`, two `parsed_partial`.
- Nippon: two `parsed_partial`; one May-content file remains `needs_review`.
- Mirae: 95 `parsed_partial` rows with per-document diagnostics retained.
- UTI: two `parsed`, two `parsed_partial`.
- DSP: two `parsed_partial`.
- Kotak: one factsheet `parsed_partial`; no portfolio row.
- Aditya Birla: one `parsed_partial` portfolio ZIP with 105 parsed schemes, 5,928 staged holdings, and member/worksheet diagnostics; no factsheet row.
- Axis: no exact-June raw row.
- Motilal: no exact-June raw row.

`parsed_partial` is not automatically a failure. It is acceptable only when:

- valid rows were preserved;
- every dropped ZIP member or worksheet has attached diagnostics;
- reviewed mapping and every required field still clear the 80% gate;
- no unresolved current-month critical failure remains.

## 5. Local changes that must be reviewed and pushed

The pushed baseline is `763ace5d`. The current local worktree contains:

1. `.github/workflows/acquire-mf-documents.yml`
   - loads the reviewed official source manifest during acquisition.
2. `backend/app/mf_ingestion/services/parsing_service.py`
   - treats factsheet body dates as authoritative when the filename uses a publication month;
   - retains filename-month rejection for portfolio files.
3. `backend/scripts/smoke_parse_mf_raw_documents.py`
   - adds bounded `--download-only` diagnostics for already acquired R2 files.
4. Focused regression tests for both fixes.

Current focused result:

```text
49 passed
git diff --check: passed
```

Before pushing:

```powershell
git status --short
git diff --check
.\.venv\Scripts\python.exe -m pytest `
  backend\tests\test_mf_parsing_scope.py `
  backend\tests\test_official_document_parser_setup.py `
  backend\tests\test_amc_production_readiness.py -q
```

After pushing:

```powershell
git rev-parse HEAD
git rev-parse origin/main
```

Pass condition: both hashes match the intended tested commit.

## 6. Execution plan

### Step 1: Verify the applied discovery constraint migration

Applied migration:

```text
backend/migrations/20260728_allow_content_confirmed_discovery_month.sql
```

Run the constraint query in section 2 before rerunning discovery.

Do not continue to the hosted discovery rerun if `content_confirmed` is absent from the check constraint.

### Step 2: Push the local workflow and date-guard fixes

Run the focused checks in section 5, inspect the diff, then commit and push.

Do not rerun Axis or Aditya Birla from `763ace5d`; that commit does not load the reviewed manifest in the acquisition workflow.

### Step 3: Rerun bounded discovery

Use:

```powershell
gh workflow run "Discover Official AMC Documents" --ref main `
  -f "amcs=hdfc,sbi,icici,axis,ppfas,nippon,motilal,mirae,uti,dsp,kotak,aditya_birla" `
  -f "document_scope=all" `
  -f "expected_month=2026-06" `
  -f "expected_month_grace_days=14" `
  -f "minimum_completed=12" `
  -f "max_actions=12" `
  -f "max_candidates=3" `
  -f "probe_downloads=true" `
  -f "browser_fallback=false"
```

Monitor:

```powershell
gh run list --workflow "Discover Official AMC Documents" --limit 5
gh run view <RUN_ID> --json status,conclusion,url,jobs
gh run view <RUN_ID> --log-failed
```

Verify the downloaded `report.json` and `manifest.json`:

- expected month is `2026-06`;
- all URLs use an allowed official host;
- the body is a real PDF/XLS/XLSX/ZIP, not HTML;
- `content_confirmed` documents persisted successfully;
- stale candidates are not marked promotable;
- acquisition count remains zero;
- promotion count remains zero.

### Step 4: Complete remaining acquisition

Acquisition remains bounded to one AMC, one month, and at most three documents per type.

Example:

```powershell
gh workflow run "Acquire MF Documents" --ref main `
  -f "amc=axis" `
  -f "document_scope=all" `
  -f "expected_month=2026-06" `
  -f "max_documents=3" `
  -f "approval_phrase=ACQUIRE 2026-06 axis"
```

Next bounded acquisitions:

- Motilal: exact official `Factsheet June 2026 Active`, reused for factsheet and embedded portfolio scopes.
- Kotak: exact official `KotakMFFactsheetJune2026.pdf`, reused for factsheet and embedded portfolio scopes.
- Aditya Birla: exact official `Empower Factsheet - June 2026`; the existing portfolio row should remain separate.

Do not use third-party fund data or relabel stale files. All three reviewed URLs are official AMC-hosted sources and must still pass checksum, report-month, R2, parser, mapping, and promotion gates.

Verify every acquired row:

```sql
select
  id,
  amc_code,
  document_type,
  report_month,
  parse_status,
  storage_backend,
  storage_bucket,
  storage_key,
  checksum,
  source_url
from public.mf_raw_documents
where report_month = date '2026-06-01'
order by amc_code, document_type, downloaded_at desc;
```

Pass conditions:

- `storage_backend = 'r2'`;
- R2 bucket/key are present;
- checksum is present;
- source URL is official;
- report month is exact;
- duplicate bodies reuse the existing document;
- a cross-month checksum conflict is sent to review.

### Step 5: Parse only pending exact-month rows

Use the parser-only workflow or the local job.

Local bounded example:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe `
  -m backend.app.mf_ingestion.jobs.parse_pending_documents `
  --limit 20 `
  --amc absl `
  --report-month 2026-06-01
```

Hosted parser-only example:

```powershell
gh workflow run "Sync MF Disclosures" --ref main `
  -f "amcs=aditya_birla" `
  -f "parse_only=true" `
  -f "parse_limit=20" `
  -f "parse_rounds=1" `
  -f "report_month=2026-06"
```

Pass conditions:

- the workflow does not call the Edge acquisition path;
- parser writes do not update runtime comparison tables;
- raw scheme name is preserved;
- mapped scheme code and family are nullable until reviewed;
- corrupt ZIP members and worksheets have diagnostics;
- one bad ZIP member plus valid rows becomes `parsed_partial`;
- all members failing becomes `failed`;
- recognized files with no usable holdings become `needs_review`.

### Step 6: Fix field extraction using exact official fixtures

Do this AMC by AMC. Never add a generic regex based only on guessed formatting.

#### HDFC

Current production-staging blockers before reacquisition and reparse:

- AUM 60.71%;
- TER 57.14%;
- manager 1.19%;
- risk 0%.

Locally implemented and verified:

- parse the `FUND MANAGER / Name / Since / Total Exp` table;
- extract the first dated month-end AUM value from `ASSETS UNDER MANAGEMENT`;
- handle `Regular:` and `Direct:` rows under `EXPENSE RATIO`;
- accept the `BENCHMARK AND SCHEME RISKOMETERS` page heading;
- map only the Scheme Riskometer needle, not the benchmark needle;
- abstain on row-count or scheme-order mismatch;
- combine the main and Index Solutions factsheets, reaching local raw-field coverage of AUM 100%, TER 81.44%, benchmark 100%, manager 87.63%, and risk 100% across 97 unique scheme keys.

Verify against:

```text
C:\tmp\hdfc-june-parser-debug\hdfc-factsheet-709eef10-07a1-4098-b1b0-618234709f08.pdf
```

The temp path is diagnostic evidence only and must not be committed.

#### Nippon

Current production-staging blockers before reparse:

- TER 67.53%;
- risk 0%.

Locally implemented and verified:

- parse Nippon's no-percent Regular/Direct TER layout;
- map the scheme-riskometer vector needle by geometry rather than OCR;
- keep the May-content file `b4f4f6b0-c088-4455-a071-b0911f2fb75c` in review;
- parse the July-named PDF only because its body is confirmed as June 30;
- local raw-field coverage is AUM 100%, TER 87.18%, benchmark 85.90%, manager 98.72%, and risk 98.72% across 78 records.

#### UTI

Current production-staging blockers before exact-source acquisition and reparse:

- TER 4.62%;
- benchmark 36.92%;
- manager 12.31%;
- risk 6.15%.

Source correction and local implementation:

- reject the June-publication Fund Watch files for this gate because their body contains May data;
- acquire the official July active and passive Fund Watch files whose body contains June 30 data;
- parse page-aligned AUM, TER, benchmark, manager, YTD TER annexure, and riskometer vector layouts;
- merge duplicate scheme records only by normalized scheme identity;
- prevent one scheme section from borrowing the next scheme’s values;
- local combined raw-field coverage is AUM 93.83%, TER 92.59%, benchmark 86.42%, manager 95.06%, and risk 83.95% across 81 unique scheme keys.

#### Axis

Current blocker: no acquired June row.

Required order:

1. Push the manifest workflow fix.
2. Acquire the reviewed June combined factsheet.
3. Parse factsheet and embedded holdings independently.
4. Run mapping and field coverage.

#### Aditya Birla

Current blocker: portfolio coverage passes, but the exact June factsheet has not yet been acquired and its local AUM/risk extraction is below the gate.

Required order:

1. Acquire the exact official `empower-factsheet---june-2026.pdf`.
2. Parse the factsheet.
3. Harden AUM/risk extraction, then review mappings and field coverage.

Current portfolio evidence:

- 92 observed portfolio groups;
- 84 mapped portfolio families;
- 91.30% portfolio mapping;
- 100% holdings coverage;
- 97.33% sector coverage.

#### Kotak

Current blocker: the exact official combined factsheet is locally verified but not yet acquired or staged.

The June PDF contains factsheet fields, holdings, and sector allocation per fund. Local deterministic extraction yields 76 portfolio records, with 64 inside the valid allocation band. Acquire it once for each document scope, stage out-of-band records for review, and promote only rows whose `validation_status` is `valid`.

#### Motilal

Current blocker: the exact official active factsheet is locally verified but not yet acquired or staged.

The July-published `Factsheet June 2026 Active` PDF contains June 30 factsheet, holdings, and sector data. Local deterministic extraction yields 20 portfolio records, with 19 inside the valid allocation band. The remaining record must stay in review; do not promote it as complete.

### Step 7: Reconcile mappings

Staging must preserve:

- `raw_scheme_name`;
- `normalized_scheme_name`;
- reviewed `mapped_scheme_code`;
- reviewed `mapped_family_id`;
- mapping confidence and status.

Run:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe `
  -m backend.app.mf_ingestion.jobs.reconcile_staged_mappings `
  --amc hdfc `
  --report-month 2026-06-01
```

The command above is a dry-run. Repeat it for each AMC. After reviewing the proposals, use `--apply` to update staging mappings only; it never writes runtime tables.

Review unresolved candidates before promotion:

```sql
select
  amc_code,
  raw_scheme_name,
  normalized_scheme_name,
  mapped_scheme_code,
  mapped_family_id,
  mapping_confidence,
  mapping_status,
  validation_issues
from public.mf_factsheet_candidates
where report_month = date '2026-06-01'
  and (
    mapping_status <> 'mapped'
    or mapped_scheme_code is null
    or mapped_family_id is null
  )
order by amc_code, raw_scheme_name;
```

Pass conditions:

- raw AMC spelling remains unchanged;
- mapping belongs to the same AMC;
- ambiguous and low-confidence mappings remain review-only;
- promotion never rematches names during `--apply`.

### Step 8: Recalculate all 12 coverage gates

Run:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe backend\scripts\report_mf_staging_coverage.py `
  --report-month 2026-06-01 `
  --threshold 80
```

Do not promote an AMC unless:

- `passes_all_fields = true`;
- core mapping is at least 80%;
- portfolio mapping is at least 80%;
- every required field is at least 80%;
- no unresolved current-month critical failure remains;
- one selected acceptance fund reaches 100% end to end.

### Step 9: Run promotion dry-runs

Dry-run does not require promotion approval, but the protected environment reviewer still controls workflow execution.

Example:

```powershell
gh workflow run "Promote MF Disclosures" --ref main `
  -f "source_document_id=<UUID>" `
  -f "scopes=risk,ter_aum,benchmark,manager" `
  -f "expected_month=2026-06" `
  -f "apply=false" `
  -f "approval_phrase="
```

Run holdings/sectors separately:

```powershell
gh workflow run "Promote MF Disclosures" --ref main `
  -f "source_document_id=<PORTFOLIO_UUID>" `
  -f "scopes=holdings,sectors" `
  -f "expected_month=2026-06" `
  -f "apply=false" `
  -f "approval_phrase="
```

Dry-run pass conditions:

- exact source document and checksum are shown;
- expected month is exact;
- reviewed mapping has not changed;
- candidate evidence has not changed;
- rejected rows are listed without modifying runtime tables;
- each scope reports its independent candidate count.

### Step 10: Apply the approved promotion one scope at a time

Promotion authorization was recorded on 2026-07-28. The workflow phrase remains mandatory and does not replace the staging gates.

Required approval phrase:

```text
PROMOTE <SOURCE_DOCUMENT_ID> 2026-06
```

Example:

```powershell
gh workflow run "Promote MF Disclosures" --ref main `
  -f "source_document_id=<UUID>" `
  -f "scopes=risk" `
  -f "expected_month=2026-06" `
  -f "apply=true" `
  -f "approval_phrase=PROMOTE <UUID> 2026-06"
```

Apply one AMC and one scope at a time. Verify runtime values before applying the next scope.

### Step 11: Enable and deploy one AMC at a time

Requires explicit runtime/deployment approval.

For each AMC:

1. Set the registry runtime flag only after all gates pass.
2. Deploy backend changes.
3. Deploy frontend only when frontend behavior changed.
4. Verify live health and disclosure dates.
5. Run one selected acceptance fund.
6. Keep already accepted AMCs unchanged.

## 7. Production verification

### API and health

```powershell
Invoke-RestMethod https://www.fundersai.co.in/api/data-health
Invoke-RestMethod https://www.fundersai.co.in/api/mf/118989
Invoke-RestMethod https://www.fundersai.co.in/api/mf/118668
```

Verify:

- MF NAV freshness is independent of AMC document processing;
- AUM/TER, risk, and AMC-document labels use the same shared status model;
- “AMC docs processing” never becomes “MF data lagging” when NAV is fresh;
- last checked and data last updated are different timestamps;
- refresh only rereads status.

### Exact HDFC/Nippon acceptance comparison

Acceptance pair:

- HDFC scheme code `118989`
- Nippon scheme code `118668`

Verify:

- both IDs resolve;
- canvas opens because the backend returned a valid `COMPARE` action;
- chat shows a concise Trend Observation;
- no Ask AI button appears in a chat-triggered comparison;
- Research frame and Decision clarity are hidden when empty;
- risk, TER, benchmark, manager, holdings, and sectors use promoted official data;
- coverage is not pending when every required field is present;
- missing overlap is shown as unavailable, not `0%`;
- Claim sources remain directly below cited official-document answers;
- As of, freshness, coverage, confidence, missing fields, and reasoning labels remain visible;
- hover/focus/tap popovers expose explanations and read-only actions.

### Data & Trust page

Open:

```text
https://www.fundersai.co.in/dashboard/data-trust
```

Verify:

- all four health cards render;
- per-AMC current month and field coverage render;
- pipeline stages remain separate;
- public landing preview does not expose live operational data;
- one-minute polling pauses in background tabs;
- manual Refresh never starts ingestion or promotion.

## 8. Test and release checklist

Run focused tests first:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  backend\tests\test_mf_parsing_scope.py `
  backend\tests\test_factsheet_parser.py `
  backend\tests\test_holdings_parser.py `
  backend\tests\test_amc_production_readiness.py `
  backend\tests\test_discovery_run_persistence.py `
  backend\tests\test_mf_document_link_preflight.py -q
```

Then run the relevant full checks:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests

Set-Location frontend
node --test tests/*.test.mjs
npx tsc --noEmit
npm run lint
npm run build
Set-Location ..

git diff --check
uvx graphify update .
```

If Graphify reports that no installable `graphify` version exists, record it as unavailable tooling. It is not an application test failure.

Validate workflow YAML:

```powershell
.\.venv\Scripts\python.exe -c "import pathlib,yaml; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in pathlib.Path('.github/workflows').glob('*.yml')]; print('workflow_yaml_ok')"
```

## 9. Troubleshooting map

| Symptom | Stage | Required action |
|---|---|---|
| `no_documents_found` | Discovery | Inspect official source/manifest wiring; do not run parser or promotion. |
| `content_confirmed` constraint violation | Discovery persistence | Stop discovery and recheck the applied 20260728 constraint; do not write a weaker status. |
| `r2_required_for_raw_storage` | Acquisition | Verify existing R2 secrets and bucket names. |
| `not_modified` | Acquisition | Reuse the existing raw document; do not redownload or reparse. |
| `checksum_month_conflict` | Acquisition | Send to review; do not relabel or promote. |
| `factsheet_content_report_month_mismatch` | Parsing | Keep in review unless official body evidence confirms the expected month. |
| `factsheet_partial_scheme_matching` | Mapping | Review unmatched raw names; do not rematch during promotion. |
| `percent_aum_out_of_band` | Holdings validation | Inspect sheet/member diagnostics and totals before accepting partial output. |
| Field coverage below 80% | Parser | Add an exact official fixture and deterministic extractor; reparse staging. |
| Dry-run says mapping/evidence changed | Promotion | Re-review and regenerate the staged candidate. |
| Live API differs from staging | Deployment/runtime | Stop the next scope; verify deployed commit, runtime flag, and promotion audit. |

## 10. Rollback and last-known-good behavior

If a promoted scope fails live acceptance:

1. Stop further promotions for that AMC.
2. Disable only that AMC’s new runtime flag if it was enabled.
3. Restore the previous accepted runtime snapshot for the affected scope.
4. Preserve the raw R2 document, staging rows, promotion audit, and diagnostics.
5. Record the failed source document ID, checksum, scope, deployed commit, and live response.
6. Fix and dry-run again; never overwrite evidence to make the failed run appear successful.

Do not delete raw documents, staging candidates, review rows, or promotion audits as part of rollback.

## 11. Definition of production-ready

An AMC is production-ready only when all of the following are true:

- exact June 2026 official discovery passed;
- official host and file body passed validation;
- raw file is checksum-addressed in R2;
- factsheet and portfolio parsing completed with reviewable diagnostics;
- raw scheme names and reviewed mappings are preserved;
- mapping coverage is at least 80%;
- AUM, TER, benchmark, manager, risk, holdings, and sectors each meet the 80% gate;
- no current-month critical failure is unresolved;
- dry-run passes for every intended scope;
- each scope was explicitly approved and applied independently;
- one selected fund passes 100% end to end;
- live API, chat, canvas, and Data & Trust checks pass;
- implemented, locally verified, pushed, deployed, promoted, and activated states are recorded separately in `docs/CURRENT_STATE.md`.

Until all of these conditions are met, the AMC must remain disabled for new runtime disclosure data.
