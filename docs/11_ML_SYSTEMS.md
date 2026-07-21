# ML Systems

**Last updated:** 2026-07-21

## Purpose

FundersAI is a research-first financial application. Its ML features must expose the evidence and limitations behind an output; they must not make return forecasts, portfolio allocations, or buy/sell recommendations.

The production ML and retrieval foundation has three independent parts:

1. numeric mutual-fund similarity and clustering for peer discovery;
2. deterministic parser-review prioritization for the admin workflow;
3. official-document chunking, indexing, retrieval, citation metadata, and abstention.

They are deliberately small, inspectable baselines. They create a reliable data and evaluation path before adding more complex models.

## 1. Mutual-fund similarity and clustering

Implementation: `backend/app/services/fund_similarity_service.py`.

### What it answers

“Which funds in the same category look most similar to this fund according to the currently stored metrics?”

It does **not** answer “Which fund will perform best?” Similarity is a research aid, not a forecast.

### Input data and scope

- Source table: `mutual_fund_core_snapshot`.
- Peer pool: funds with the same `category` as the requested scheme. If the target has no category, the pool is not category-filtered.
- A fund needs at least five usable numeric features. The service needs at least three eligible funds in its peer pool.
- The response records `feature_version: "mf_similarity_numeric_holdings_v2"` so a client or later evaluation can identify the exact feature definition.

### Feature vector

Each eligible fund becomes one numeric row with these stored snapshot fields:

- 1M, 3M, 6M, 1Y, 3Y, and 5Y return
- 1Y volatility and maximum drawdown
- expense ratio and AUM
- alpha, beta, and Sharpe ratio

`AUM` is transformed with `log(1 + AUM)`. This prevents a very large fund from dominating the distance calculation solely because its AUM is measured on a much larger scale.

### Vector preparation

1. Missing values are replaced with the median of that feature within the eligible peer pool.
2. Each non-constant feature is standardized: `(value - mean) / standard_deviation`.
3. Constant columns are dropped because they cannot distinguish funds.
4. Cosine similarity ranks peers. It compares the direction of two standardized feature vectors rather than their raw scale.

The API converts cosine similarity from `[-1, 1]` to the response's `similarity_score` range `[0, 1]` using `(cosine + 1) / 2`.

### Clustering

The same standardized vectors are grouped with a small deterministic k-means implementation:

- number of clusters: `sqrt(number_of_eligible_funds)`, bounded to 2–4;
- deterministic, evenly spaced initial centroids;
- up to 30 centroid updates;
- no additional ML dependency beyond NumPy.

`same_cluster` is an extra grouping signal; peer ranking still uses cosine similarity. The target response includes its cluster id and member count.

### Explainability and limitations

Every peer includes the three closest active features, including the target value, peer value, and standardized distance. The numeric similarity score remains independent from holdings. Each peer also includes `holdings_evidence`, which reports weighted holdings overlap when both funds have current holdings data. The response includes target missing features and these limitations:

- it uses only current stored snapshot metrics;
- holdings overlap is supporting evidence and does not change the numeric similarity score;
- document-text embeddings are a separate research-retrieval system;
- it is not a forecast or recommendation.

This is an important ML practice: a user can see why a result exists and when the data is too sparse to produce one.

## 2. Parser-review prioritization

Implementation: `backend/app/services/review_priority_service.py`.

The parser review queue contains documents that need a human decision. The new priority service only ranks pending work; it never resolves, reparses, skips, or writes to a document.

### Why a rule-based baseline first

There is not yet a verified historical label set large enough to train a dependable classifier. A deterministic baseline is the correct first production system because it is auditable, testable, and produces future training data from reviewer outcomes.

The result is tagged with `priority_version: "mf_review_rule_based_v1"`.

The offline supervised path now lives under `backend/ml/`. It exports only feature/label fields from reviewed queue rows, omitting reviewer notes and sample document contents. `mf_review_logistic_v1` predicts whether a reviewed item required reparse, uses a chronological 80/20 split, and compares its precision/recall at review capacity against the rule baseline.

Training refuses to run below the configured total-label, per-class, or time-split class-coverage thresholds. MLflow logging happens only after successful training. Registry promotion requires live reviewer outcomes or an explicitly verified reviewer export; unverified files cannot receive the `candidate` alias.

### Score inputs

The priority score is capped at `1.0` and is built from explicit evidence:

| Signal | Score added |
| --- | ---: |
| `parse_exception` | 0.45 |
| `raw_file_missing` or `raw_file_unavailable` | 0.40 |
| `holdings_not_found` | 0.25 |
| `percent_aum_out_of_band` | 0.20 |
| `factsheet_fields_not_extracted` | 0.18 |
| `llm_partial_review_required` | 0.15 |
| low extractor confidence | up to 0.25 |
| review waiting 14+ days | 0.05–0.15 |

Priority labels are `high` at 0.65+, `medium` at 0.35–0.649, and `low` below 0.35. Each returned row contains `priority_reasons`, so an operator can challenge or understand the ordering.

## API contracts

### Public fund similarity

`GET /api/funds/{scheme_code}/similar?limit=5`

- `scheme_code` is an integer mutual-fund scheme code.
- `limit` is clamped to 1–20.
- It shares the existing `mf-detail` rate-limit group.

Example response shape:

```json
{
  "status": "available",
  "feature_version": "mf_similarity_numeric_holdings_v2",
  "method": "median_imputation + standardization + cosine_similarity + deterministic_kmeans",
  "peer_scope": { "category": "Flexi Cap", "eligible_funds": 42 },
  "target": {
    "scheme_code": "101",
    "scheme_name": "Example Fund",
    "features_available": 13,
    "missing_features": [],
    "cluster": { "id": 1, "member_count": 12 }
  },
  "peers": [
    {
      "scheme_code": "102",
      "similarity_score": 0.94,
      "same_cluster": true,
      "matching_factors": [
        { "feature": "volatility_1y", "standardized_distance": 0.08, "target_value": 12.0, "peer_value": 12.1 }
      ]
    }
  ],
  "limitations": ["..."]
}
```

Possible non-success data states are `not_found` and `insufficient_data`; both return an empty `peers` list and an explicit limitation.

### Internal parser-review priority endpoint

`GET /api/admin/mf-review-priorities?limit=100`

- Requires the internal `X-Admin-Key` header. It is for the server-side admin proxy, not direct browser use.
- `limit` is 1–500.
- Reads only `pending_review` rows from `mf_parse_review_queue`.

The response contains `items`, `summary` counts for high/medium/low priority, `priority_version`, and the method string `deterministic review triage baseline; no automated resolution`.

## 3. Official-document retrieval

Implementations:

- `backend/app/mf_ingestion/jobs/index_parsed_documents.py`
- `backend/app/services/document_indexing_service.py`
- `backend/app/services/document_retrieval_service.py`
- `backend/migrations/20260715_add_pgvector_and_amc_document_chunks.sql`
- `backend/migrations/20260721_harden_amc_document_chunks.sql`

The indexing path is explicitly offline. It filters to `parsed` or `parsed_partial` official PDFs before applying its document limit, creates deterministic paragraph-aware chunks, and stores normalized source, parser, and report-month metadata. Direct OpenAI `text-embedding-3-small` vectors use the existing 1,536-dimension schema and version `amc_document_embedding_openai_v2`. `--require-embeddings` re-indexes lexical-only documents and fails on provider errors; non-strict execution retains lexical fallback.

`POST /api/funds/research/search` returns citations-ready sources with `document_id`, `chunk_id`, official source URL, AMC, document type, report month, score, and excerpt. No matching source produces `abstain: true`; the service does not invent evidence.

The default retrieval version is `amc_lexical_rerank_v2`. It evaluates up to 200 filtered lexical candidates, combines lexical overlap with RapidFuzz token-set reranking, removes duplicate chunk text, selects sources that cover distinct meaningful query terms, focuses each excerpt around the strongest matched window, and rejects questions whose meaningful terms have insufficient corpus coverage. It exposes corpus status, retrieval mode, vector status, reranker version, and query coverage. When `MF_RESEARCH_VECTOR_SEARCH_ENABLED=true`, the service creates a direct OpenAI query embedding, calls `match_document_chunks`, and falls back to lexical retrieval if OpenAI or the RPC fails. Render enables this flag after the matching document-vector backfill.

`evaluate_retrieval` is provider-free and measures recall at k, hit rate, all-relevant rate, mean reciprocal rank, grounded-answer rate, and abstention accuracy. `backend/evals/fund_research_v1` contains the first versioned dataset, corpus, manifest, and recorded lexical baseline. The dataset is deliberately marked `development_seed`: it proves the evaluation contract, but fixture claims must be replaced with reviewer-verified official-document cases before it can gate production.

The recorded v1 seed baseline retrieves all expected documents but has only `0.3333` abstention accuracy. V2 fixes both known false-grounding cases on the same seed: retrieval recall remains `1.0`, abstention accuracy becomes `1.0`, and 14/14 cases pass. This is a development-fixture result and cannot gate production until the dataset is replaced with reviewer-verified official-document cases.

`POST /api/funds/research/answer` uses `fund_research_graph_v3` to normalize the request, retrieve evidence, branch to synthesis or abstention, and validate HTTPS sources plus numbered citations. Its deterministic synthesis extracts readable objective, benchmark, riskometer, and expense-ratio claims when present; unsupported questions retain cited-excerpt fallback or abstention. It does not use free-form LLM generation. Fund details and comparisons remain outside the graph.

The offline review-priority path also includes a feature-drift report. Numeric features use standardized mean shift; categorical features use total-variation distance. Drift alerts signal distribution change only—they do not prove model performance degradation, which still requires fresh reviewer outcomes.

## Learning path and next steps

### What this teaches now

- feature engineering, including scale-aware transforms;
- missing-data handling and the difference between imputation and source completeness;
- vector normalization, cosine similarity, and k-means clustering;
- explainability through nearest features rather than black-box scores;
- a supervised-learning prerequisite: start with an auditable rule baseline and collect reliable labels.

### How to evaluate before expanding

1. Ask reviewers to judge a sample of returned peer lists; track precision@k and explanation usefulness.
2. Store data/feature versions with each offline evaluation so results remain reproducible.
3. Use time-aware splits for any future market model. Never train on data that would not have existed at the prediction date.
4. For review prioritization, record final reviewer outcome and measure precision at the actual daily review capacity.
5. Keep human review and research-only language for all financial outputs.

### Ordered next work

- **Golden retrieval evaluation:** expand the development seed to at least 50 reviewer-verified official-document cases before using it as a production gate.
- **Prefect deployment:** exercise the implemented flow with live credentials and keep GitHub Actions authoritative until equivalent run evidence exists.
- **Supervised review classifier:** run the guarded trainer on live reviewer outcomes, inspect the chronological holdout metrics, and register a candidate only when it improves the operational review-capacity metric.
- **Vector retrieval:** compare the implemented opt-in pgvector path against v1 and v2 on reviewer-verified cases, including latency and provider cost.
- **LangGraph extension:** `fund_research_graph_v2` now adds one bounded official-corpus rewrite and claim-level support validation; add entity/structured-fact nodes only after reviewer-verified production evaluation coverage.
- **Retrieval v3:** reciprocal-rank fusion and the Cohere cross-encoder adapter are independently feature-flagged. The cross-encoder must fall back to deterministic fusion and cannot be promoted until the same reviewer-verified set establishes quality, latency, and cost improvement.
- **Deployment and observability:** run the container/GCP proof, capture smoke-test and alert evidence, then add persisted freshness, index-lag, retrieval-quality, latency, and cost dashboards.
- **Fine-tuning:** consider it only for narrowly scoped, reviewer-verified document extraction/classification. Do not fine-tune general chat or use it for financial return prediction.

## Tests

- `backend/tests/test_fund_similarity_service.py` verifies explainable peer ranking and sparse-data handling.
- `backend/tests/test_review_priority_service.py` verifies deterministic ranking, non-mutating output, and the admin-service authentication path.
- `backend/tests/test_document_indexing_service.py` verifies the direct OpenAI embedding boundary, local key alias, strict failure, and lexical-only re-index selection.
- `backend/tests/test_document_retrieval_service.py` verifies deterministic chunking, citable sources, abstention, and retrieval evaluation.
