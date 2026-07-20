# AMC Link Discovery Agents

FundersAI has ten bounded specialists for official AMC document discovery:

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

## Safety contract

- Only approved official AMC hosts and explicitly verified first-party CDN hosts are accepted.
- Every run has a fixed action budget.
- Expected-month runs reject stale or undated candidates.
- Candidate URLs must pass metadata validation and an optional live download probe.
- HTML block pages and invalid PDF, Excel, and ZIP bodies are rejected.
- A specialist escalates instead of guessing a URL.
- Agents emit a validated manifest; ingestion, R2 storage, parsing, and review remain separate stages.

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
- download-probe evidence;
- action counts and limits;
- a validated source manifest.

OpenAI is intentionally absent from this stage, so these discovery runs consume no OpenAI API credits.
