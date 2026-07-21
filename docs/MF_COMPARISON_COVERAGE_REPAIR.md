# Mutual-Fund Comparison Coverage Repair

Use this when a comparison resolves the right funds but reports partial coverage, incorrect categories, missing metrics, or malformed holdings.

## 1. Run the read-only diagnostic

From the repository root:

```powershell
.\.venv\Scripts\python.exe backend\scripts\diagnose_mf_comparison_coverage.py 118955 122639
```

The report separates:

- identity: scheme code and resolved name;
- metadata: category, benchmark, and official risk label;
- NAV coverage: point count, supported periods, freshness, and calculated returns/risk;
- cost: expense ratio and AUM;
- holdings: usable row count and parser noise;
- `missing_fields`: fields that make coverage incomplete;
- `limitations`: disclosed fallbacks that do not make core coverage incomplete.

## 2. Classify the failure

| Symptom | Cause | Fix |
|---|---|---|
| Scheme code missing | Resolver/snapshot identity gap | Run the metadata sync, confirm the AMFI code, and add a resolver regression test. |
| NAV history is short or stale | `nav_api_cache` was not populated/refreshed | Run the NAV sync workflow, then confirm the history point count and 1Y/3Y/5Y support. |
| Category, benchmark, or risk label is missing/wrong | Structured metadata gap | Verify the value on the official AMC page/factsheet, add an idempotent migration, and add a narrow runtime fallback if an immediate deploy-safe repair is needed. |
| Holdings are empty | Official disclosure was not parsed/mapped | Check the raw document, family mapping, parse status, and latest holdings date; then reparse the document. |
| Holdings contain totals or joined headers | Parser extraction noise | Add the exact bad row to the AMC parser regression test, reject it in the parser, reparse, and keep read-time filtering for old rows. |
| Benchmark fallback is shown | Benchmark metadata is unavailable | Treat it as a disclosed limitation. Do not mark otherwise complete return/risk/cost data as missing solely because fallback context is used. |

Only use official AMC or AMFI sources for a metadata repair. Do not copy fund metadata from an aggregator.

## 3. Apply this repair

Run this migration in the Supabase SQL editor:

```text
backend/migrations/20260722_repair_flexi_cap_comparison_metadata.sql
```

It corrects the category, subcategory, benchmark, and risk label for scheme codes `118955` and `122639`, and records the official source URL in `provider_payload`.

Deploy in this order:

1. Apply the database migration.
2. Deploy the backend.
3. Deploy the frontend only if frontend comparison code changed.
4. Run the diagnostic again.
5. Run the exact chat comparison and confirm that the canvas opens.

## 4. Verify production

Expected checks:

```powershell
Invoke-RestMethod https://www.fundersai.co.in/api/mf/118955
Invoke-RestMethod https://www.fundersai.co.in/api/mf/122639

$body = @{ fund_names = @(
  'HDFC Flexi Cap Fund',
  'Parag Parikh Flexi Cap Fund'
) } | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri https://www.fundersai.co.in/api/funds/compare/verdict `
  -ContentType 'application/json' `
  -Body $body
```

Pass conditions:

- both scheme codes resolve;
- both categories read `Equity Scheme - Flexi Cap Fund`;
- both benchmarks read `NIFTY 500 TRI`;
- NAV history supports 1Y, 3Y, and 5Y;
- returns, volatility, drawdown, Sharpe, expense ratio, and AUM are populated;
- `missing_fields` is empty for the requested comparison fields;
- malformed subtotal rows do not appear in holdings;
- the chat response includes a usable comparison action and the canvas opens.

If the API passes but chat does not open the canvas, the remaining fault is in chat action delivery or frontend state, not data coverage.
