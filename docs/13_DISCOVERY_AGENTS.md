# AMC Link Discovery Agents

**Last updated:** 2026-07-23

FundersAI has a default top-10 supervisor roster for official AMC document discovery:

- SBI
- Mirae Asset
- PPFAS
- ICICI Prudential
- HDFC
- Nippon India
- Kotak Mahindra
- Aditya Birla Sun Life
- UTI
- DSP

One supervisor runs the specialists concurrently and isolates failures by AMC.

Axis has an additional bounded specialist used by the active ingestion workflow but is not part of the historical top-10 roster. Motilal Oswal is enabled in the source registry but does not currently have a class in `AGENT_CLASSES`; do not claim supervisor-agent coverage for it.

## Safety contract

- Only approved official AMC hosts and explicitly verified first-party CDN hosts are accepted.
- Every run has a fixed action budget.
- Run status is separate from document readiness. A run can complete while a document remains `needs_review`.
- Document identity is AMC + document type + report month; checksum-versioned observations retain prior months.
- Expected-month runs require an exact month after the 14-day publication grace period. Undated or non-exact candidates remain reviewable but cannot be promoted.
- Candidate URLs pass metadata validation, a ranged GET probe, content validation, and a parser smoke test before becoming `promotable`.
- HTML block pages and invalid PDF, Excel, and ZIP bodies are rejected.
- A specialist escalates instead of guessing a URL.
- Agents emit evidence-rich manifests; ingestion, raw R2 storage, parsing, and user-facing promotion remain separate stages.
- Browser fallback is disabled unless `MF_DISCOVERY_BROWSER_ENABLED=true` and the AMC is listed in `MF_DISCOVERY_BROWSER_AMCS`.
- LLM recovery is disabled unless `MF_DISCOVERY_LLM_RECOVERY_ENABLED=true` with an explicit model. It can choose only links already present on the approved AMC listing page and cannot fetch candidates, persist data, or change configuration.

## Discovery strategies

| AMC | Strategy |
|---|---|
| SBI | Official recent-factsheets endpoint; all-schemes files outrank passive-only files |
| Mirae | Official `GetDownloadsData` API for factsheets and monthly portfolios |
| PPFAS | Confirmation-aware official-page traversal |
| ICICI | Official categories and files APIs with download fallback |
| HDFC | Official page or configured direct URLs; escalates on network 403 |
| Nippon | Official page discovery and configured direct URLs |
| Kotak | Official page or configured direct URLs; escalates on Radware challenge pages |
| Aditya Birla | Official static download anchors |
| UTI | Official document APIs with the exact UTI CDN host allowlisted |
| DSP | Official `downloads.json` API for factsheets |

Mirae, Kotak, Aditya Birla, UTI, and DSP remain disabled in the production ingestion registry. Their discovery specialists can run explicitly without claiming that downstream parsers are ready.

## Run locally or as a hosted worker

From the repository root:

```powershell
.venv\Scripts\python.exe backend\app\mf_ingestion\jobs\run_discovery_agents.py `
  --document-type factsheet `
  --expected-month 2026-06 `
  --manifest-output backend\config\mf_document_sources.top10.agent.json `
  --strict
```

The default roster is all ten AMCs. Use `--amcs sbi,mirae,ppfas` to run a subset. Keep download probes enabled for reliability checks; `--skip-download-probes` is only a discovery dry run.

## GitHub Actions deployment

`discover-mf-documents.yml` is the first hosted deployment target. It runs at `03:15 UTC` on weekdays and supports manual overrides for the AMC roster, document scope, expected month, grace period, action budget, candidate count, probes, the browser fallback, and the minimum completion gate. Chromium is installed only for an explicitly enabled browser run.

The workflow:

- defaults to the ten-agent factsheet roster;
- uses the previous UTC month as the minimum report month when none is supplied;
- persists checksum-addressed reports and manifests to the R2 cold bucket;
- records persistence stages, evidence, and document observations in server-only discovery tables;
- compares meaningful document changes with the prior run and stages source-configuration evidence only after three promotable observations;
- retains the local JSON files as a GitHub artifact for 30 days;
- fails when fewer than the configured minimum agents complete;
- never invokes ingestion or promotes a disabled AMC.

Apply `20260721_add_mf_discovery_runs.sql` and `20260723_add_discovery_v2_history.sql` and configure the documented Supabase/R2 secrets before enabling the schedule. A successful discovery run proves discovery readiness only; it does not invoke ingestion or prove app coverage.

To test acquisition for a discovery-ready source that remains disabled in production, run `ingest_latest_amc_docs.py` with `--allow-disabled-source`. The source remains disabled in `mf_amc_sources`; only the explicitly requested raw document is acquired and inserted.

For a hosted setup, start with one scheduled worker. Route HDFC acquisition through the existing Edge/R2 path when the host blocks the worker IP. Kotak should consume a reviewed direct URL through `MF_KOTAK_FACTSHEET_DOCUMENT_URLS` until a hosted network can pass its challenge page.

## Latest local live check

The July 17, 2026 run tested June-or-newer factsheets with real download probes:

| AMC | Result | Evidence |
|---|---|---|
| SBI | Completed | June all-schemes PDF |
| Mirae | Completed | July active-funds PDF |
| PPFAS | Completed | June PDF |
| ICICI | Completed | June complete factsheet PDF |
| HDFC | Escalated | Official site returned 403 from this machine |
| Nippon | Completed | June PDF |
| Kotak | Escalated by default | Official listing returned a Radware challenge |
| Aditya Birla | Completed | July monthly factsheet PDF |
| UTI | Completed | July active-funds PDF from the verified UTI CDN |
| DSP | Completed | June PDF |

Eight specialists completed end to end in the default run. Kotak then completed with a separately reviewed `MF_KOTAK_FACTSHEET_DOCUMENT_URLS` fallback and a valid PDF probe. HDFC remained blocked at the network-access layer and correctly emitted no unverified manifest row.

## Output

The worker emits:

- supervisor and per-agent status;
- selected strategies;
- rejected candidates and reasons;
- readiness, content checksum, parser-smoke, and download-probe evidence;
- run-to-run source/content/readiness changes and staged configuration candidates;
- action counts and limits;
- a validated source manifest.

Discovery is provider-free by default. The optional bounded LLM recovery flag can use the configured OpenRouter/OpenAI key only after deterministic and browser recovery produce no candidates.
