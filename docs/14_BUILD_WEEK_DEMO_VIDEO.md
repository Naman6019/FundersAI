# Build Week Demo Video

**Target length:** 2 minutes 55 seconds

**Hard limit:** less than 3 minutes

**Format:** public YouTube video with audible narration

**Primary URL:** `https://www.fundersai.co.in`

## Demo Goal

Show one complete, credible vertical slice:

```text
official AMC source
  -> bounded discovery agent
  -> validated document evidence
  -> cited research or explicit abstention
  -> deterministic comparison with visible limitations
```

The demo must distinguish ten hosted discovery agents from the six-AMC production research boundary. Do not claim that all ten AMCs are fully ingested, parsed, or available in the app.

## Before Recording

1. Apply `backend/migrations/20260721_add_mf_discovery_runs.sql` in production Supabase.
2. Add the GitHub secrets required by `discover-mf-documents.yml`:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` using the server-side service role
   - `R2_ENDPOINT`
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
   - `R2_RAW_BUCKET`
   - `R2_COLD_BUCKET`
3. Push the workflow and run it manually with the default ten-AMC factsheet roster.
4. Confirm that:
   - the GitHub run summary lists all ten agents;
   - at least eight agents completed;
   - the JSON report and manifest artifact are downloadable;
   - R2 contains the matching report and manifest;
   - Supabase contains the `mf_discovery_runs` summary row.
5. Warm the Render backend and open the production app before recording.
6. Confirm `/dashboard/research-evidence` returns cited PPFAS excerpts covering the investment objective, benchmark, and riskometer for the exact demo query. The July 21 OpenAI backfill populated 186 vector chunks and the production-data probe passed in hybrid mode; deploy the updated backend and configure its OpenAI key before recording.
7. Start from an authenticated test session. Never record login credentials, `.env` files, secret dashboards, or browser password prompts.
8. Create a clean chat session containing only the demo prompts.
9. Close notifications, bookmarks, unrelated tabs, developer tools, and personal account menus.
10. Record at 1920×1080. Keep browser zoom between 90% and 100% so the canvas and source metadata remain visible.
11. Record the screen first and add the final voiceover afterward. Remove loading pauses rather than pretending that they did not occur.

## Shot-by-Shot Timeline and Voiceover

### 0:00–0:12 — Hook

**Screen**

- Show the FundersAI landing page and canonical `.co.in` URL.
- Move directly into the authenticated workspace.

**Speak**

> Mutual fund research is fragmented across factsheets, portfolio files, and market-data providers. FundersAI turns that evidence into transparent, research-only comparisons without hiding missing data.

### 0:12–0:28 — The Problem and Product Boundary

**Screen**

- Show the research workspace with chat, comparison canvas, sources, confidence, and freshness areas visible.

**Speak**

> Instead of producing a black-box recommendation, FundersAI separates deterministic calculations, official-source evidence, confidence, freshness, and limitations. It never presents personalized buy or sell advice.

### 0:28–0:47 — Architecture

**Screen**

- Show a single architecture slide:

```text
10 AMC discovery agents
  -> official-host and file validation
  -> R2 evidence storage
  -> parsing and review
  -> Supabase research data
  -> chat, evidence, and comparison UI
```

**Speak**

> Ten bounded discovery agents inspect approved official AMC hosts. Each agent has an action budget, validates dates and file bodies, and escalates instead of guessing. The supervisor isolates individual failures and stores the complete run evidence in R2 and Supabase.

### 0:47–1:05 — Hosted Agent Run

**Screen**

- Open the latest `Discover Official AMC Documents` GitHub Actions run.
- Show the summary table, completion count, and validated-document count.
- Briefly show the report and manifest artifact names; do not expose secrets.

**Speak**

> This is the hosted supervisor running all ten specialists on GitHub Actions. Discovery is independent from ingestion, so a newly discovered AMC cannot enter production automatically. Today the user-facing research boundary remains six supported AMCs.

Do not say “ten out of ten completed” unless the visible run actually shows that result. State the displayed result accurately.

### 1:05–1:32 — Official Evidence and Citation

**Screen**

- Open `/dashboard/research-evidence`.
- Use this query:

```text
Find the investment objective, benchmark, and riskometer in the PPFAS factsheet.
```

- Show AMC, document type, report month, excerpt, source URL, and trace/retrieval status.

**Speak**

> Here OpenAI embeddings retrieve semantically relevant passages from the official PPFAS factsheet. FundersAI then shows the supporting excerpt and source metadata, validates citation support, and retains a deterministic lexical fallback instead of inventing evidence.

### 1:32–1:46 — Abstention

**Screen**

- Use this unsupported query:

```text
What is the exit-load waiver for lunar mining companies?
```

- Show the abstention or no-supported-evidence result.

**Speak**

> When the official corpus does not support a claim, FundersAI abstains. This is intentional: no citation means no answer.

### 1:46–2:00 — Deterministic Calculation

**Screen**

- Return to chat and enter:

```text
Calculate SIP returns for ₹1,000 monthly for 10 years at 12%.
```

- Show the streamed status and completed result.

**Speak**

> Deterministic questions take the fast path. This SIP calculation completes without a model call, which reduces latency, cost, and unnecessary provider dependency.

### 2:00–2:30 — Live Fund Comparison

**Screen**

- Enter:

```text
Compare HDFC Flexi Cap Fund and Parag Parikh Flexi Cap Fund for returns, risk, cost, and data freshness.
```

- Show the intermediate SSE statuses.
- Cut the loading interval if needed.
- Show the final comparison and canvas, including confidence, coverage, freshness, and missing fields.

**Speak**

> The comparison resolves both funds, streams progress, and builds a deterministic side-by-side view. It exposes returns, volatility, drawdown, cost, freshness, and confidence. Missing benchmarks or holdings remain visible instead of being filled with invented values.

### 2:30–2:40 — Session Persistence

**Screen**

- Reload the workspace.
- Select the latest session and show the restored messages.

**Speak**

> Authenticated sessions are user-owned, protected by row-level security, and restored across reloads.

### 2:40–2:55 — Codex, GPT-5.6, and Closing

**Screen**

- Show a closing slide with:
  - live app;
  - ten discovery agents;
  - six-AMC production boundary;
  - official citations and abstention;
  - `14/14 development-seed evaluation`;
  - research-only disclaimer.

**Speak**

> During Build Week, I used GPT-5.6 through Codex to inspect the repository, implement the bounded agent workflow, harden authentication and streaming, generate focused tests, and verify the deployed experience. The production research pipeline uses OpenAI embeddings for semantic retrieval, with deterministic lexical fallback and official-source citations. FundersAI makes mutual-fund research more inspectable, reproducible, and honest about what the data can prove.

Use the GPT-5.6 sentence only if it accurately describes the development account and model used. Development use is different from claiming GPT-5.6 or the OpenAI API as a production runtime provider.

## Recording and Editing Rules

- Keep the exported video between 2:45 and 2:58.
- Use captions throughout.
- Use simple cuts rather than accelerated cursor movement.
- Keep source names, confidence, and limitations readable for at least two seconds.
- Do not show the browser console; the current Recharts warning is non-fatal but adds no judge value.
- Do not wait through the provider-backed general-explanation query; the latest production run took about 50 seconds.
- Do not use investment-performance marketing language such as “best fund,” “guaranteed,” or “no stale data.”
- Do not hide partial coverage. Explain it as a trust boundary.
- Do not show GitHub, Supabase, R2, Render, or Vercel secret values.
- Use only official AMC source pages or FundersAI-owned screens.

## Claims You Can Make

- Ten bounded official-AMC discovery agents are implemented.
- The supervisor runs specialists concurrently and isolates per-AMC failures.
- Hosted discovery evidence is retained in GitHub artifacts, R2, and Supabase after the first successful workflow run.
- The production research boundary supports Axis, HDFC, SBI, ICICI, PPFAS, and Nippon.
- Deterministic SIP and comparison paths do not require a model call.
- The app exposes coverage, confidence, freshness, missing data, citations, and abstention.
- The current retrieval evaluation passes 14/14 development-seed cases.

## Claims You Must Not Make

- All ten AMCs are fully usable in the app.
- A green discovery run proves ingestion or parser coverage.
- `parse_only=true` proves live document acquisition.
- The 14/14 development seed establishes production accuracy.
- Prefect, Cloud Run, GCP, vector retrieval, cross-encoder reranking, or an LLM relevance grader is active in production.
- FundersAI provides financial advice or personalized investment recommendations.
- The production runtime uses OpenAI or GPT-5.6 unless matching runtime evidence exists.

## Final Submission Checklist

- Video is shorter than three minutes.
- Video is public or unlisted according to the submission requirements and works in an incognito window.
- Audio clearly explains what was built and how Codex and GPT-5.6 were used.
- Repository access matches the submission rules.
- The primary Codex `/feedback` Session ID is ready.
- The project description uses the same six-AMC production and ten-agent discovery distinction.
- The video description contains the live app and repository links.
- No credentials, private user data, provider keys, or admin-only secrets are visible.
