'use client';

import { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, CheckCircle2, ExternalLink, FlaskConical, Search, ShieldCheck } from 'lucide-react';
import AuthGate from '@/components/auth/AuthGate';

type TraceStep = { node?: string; status?: string; [key: string]: unknown };
type Source = { document_id?: string; source_url?: string; excerpt?: string; score?: number; amc_code?: string; document_type?: string; report_month?: string };
type ModelUsage = { stage?: string; provider?: string; model?: string; purpose?: string; status?: string };
type ResearchResponse = {
  answer?: string;
  answer_format?: 'field_summary' | 'source_excerpts' | 'abstention';
  grounded?: boolean;
  abstain?: boolean;
  trace_id?: string;
  workflow_version?: string;
  retrieval_version?: string;
  sources?: Source[];
  trace_details?: TraceStep[];
  claim_validation?: { support_rate?: number; supported_claims?: number; claim_count?: number };
  retrieval?: { mode?: string; vector_status?: string; cross_encoder_status?: string; corpus_status?: string; reranker_version?: string };
  model_usage?: ModelUsage[];
};

type EvaluationVariant = {
  retrieval_version?: string;
  passed_cases?: number;
  cases?: number;
  recall_at_k?: number;
  mean_reciprocal_rank?: number;
  abstention_accuracy?: number;
  configuration?: { variant?: string; live_embeddings?: boolean; live_cross_encoder?: boolean };
};

const AMC_OPTIONS = [
  ['axis', 'Axis Mutual Fund'],
  ['hdfc', 'HDFC Mutual Fund'],
  ['icici', 'ICICI Prudential Mutual Fund'],
  ['nippon', 'Nippon India Mutual Fund'],
  ['ppfas', 'PPFAS Mutual Fund'],
  ['sbi', 'SBI Mutual Fund'],
];

const TRACE_LABELS: Record<string, string> = {
  normalize_request: 'Understand the question',
  retrieve_evidence: 'Search official documents',
  grade_retrieval: 'Check whether the evidence is relevant',
  rewrite_query: 'Try a clearer search',
  synthesize_from_evidence: 'Build the cited response',
  validate_citations: 'Verify the citations',
  citation_validation_failed: 'Stop because citation checks failed',
  abstain: 'Stop instead of guessing',
};

function pct(value: number | undefined) {
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : 'Not available';
}

function datasetLabel(value: string) {
  if (value === 'development_seed') return 'Demo benchmark';
  if (value === 'loading') return 'Loading';
  if (value === 'unavailable') return 'Unavailable';
  return value.replaceAll('_', ' ');
}

function searchMethod(mode?: string) {
  if (mode === 'hybrid') return 'Semantic and keyword search';
  if (mode === 'lexical') return 'Keyword search';
  if (mode === 'sparse') return 'Ranked keyword search';
  return 'Not reported';
}

function vectorStatus(value?: string) {
  if (value === 'active') return 'OpenAI semantic search was used';
  if (value === 'fallback_lexical') return 'Keyword fallback was used';
  if (value === 'disabled') return 'Semantic search was not used';
  return value ? value.replaceAll('_', ' ') : 'Not reported';
}

function crossEncoderStatus(value?: string) {
  if (value === 'active') return 'Advanced reranking was used';
  if (value === 'fallback_rrf') return 'Deterministic ranking fallback was used';
  if (value === 'disabled' || value === 'not_run') return 'Advanced reranking was not used';
  return value ? value.replaceAll('_', ' ') : 'Not reported';
}

function readableDate(value?: string) {
  if (!value) return '';
  const date = new Date(`${value.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('en-IN', { month: 'long', year: 'numeric', timeZone: 'UTC' });
}

function readableValue(value: unknown) {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) return value.join(', ');
  return String(value ?? 'Not available').replaceAll('_', ' ');
}

function traceLabel(node?: string) {
  return TRACE_LABELS[node || ''] || String(node || 'Processing step').replaceAll('_', ' ');
}

function variantLabel(variant?: string) {
  if (variant === 'lexical_rerank_v2') return 'Current retrieval';
  if (variant === 'hybrid_cross_encoder_v3') return 'Experimental retrieval';
  return String(variant || 'Retrieval variant').replaceAll('_', ' ');
}

function ResearchEvidencePage() {
  const [query, setQuery] = useState('Which official factsheet section lists the total expense ratio?');
  const [amcCode, setAmcCode] = useState('hdfc');
  const [response, setResponse] = useState<ResearchResponse | null>(null);
  const [variants, setVariants] = useState<EvaluationVariant[]>([]);
  const [datasetStatus, setDatasetStatus] = useState('loading');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('/api/funds/research/evaluation', { cache: 'no-store' })
      .then((result) => result.json())
      .then((value) => {
        setVariants(Array.isArray(value.variants) ? value.variants : []);
        setDatasetStatus(String(value.dataset_status || value.status || 'unknown'));
      })
      .catch(() => setDatasetStatus('unavailable'));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const result = await fetch('/api/funds/research/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, amc_code: amcCode, limit: 5 }),
      });
      if (!result.ok) throw new Error('The official-document search could not be completed.');
      setResponse(await result.json());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The official-document search could not be completed.');
    } finally {
      setLoading(false);
    }
  }

  const answerLines = (response?.answer || '')
    .split('\n')
    .filter((line) => line.trim() && !line.trim().endsWith(':'));
  const isAbstention = Boolean(response?.abstain || !response?.grounded);
  const isLegacyExcerptDump = Boolean(
    response?.grounded
    && !response?.answer_format
    && answerLines.length
    && answerLines.every((line) => /^[-•]?\s*\[\d+]\s+/.test(line.trim())),
  );
  const isExtractiveFallback = response?.answer_format === 'source_excerpts' || isLegacyExcerptDump;

  return (
    <main className="min-h-screen bg-[#060908] px-5 py-8 text-white sm:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link href="/dashboard" className="mb-3 inline-flex items-center gap-2 text-xs text-slate-400 hover:text-[#00FF9D]"><ArrowLeft className="h-3.5 w-3.5" /> Dashboard</Link>
            <h1 className="text-2xl font-semibold">Research official fund documents</h1>
            <p className="mt-1 text-sm text-slate-400">Ask a question and see the exact AMC factsheet evidence used to answer it.</p>
          </div>
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-300">Evaluation data: {datasetLabel(datasetStatus)}</span>
        </div>

        <form onSubmit={submit} className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
          <div className="grid gap-4 md:grid-cols-[1fr_230px_auto] md:items-end">
            <label className="grid gap-2 text-xs font-medium text-slate-300">
              Question for official documents
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm font-normal text-white outline-none focus:border-[#00FF9D]/50"
                placeholder="Example: What is the scheme benchmark?"
              />
            </label>
            <label className="grid gap-2 text-xs font-medium text-slate-300">
              Fund house
              <select value={amcCode} onChange={(event) => setAmcCode(event.target.value)} className="rounded-xl border border-white/10 bg-[#0a0e0c] px-4 py-3 text-sm font-normal text-white outline-none focus:border-[#00FF9D]/50">
                {AMC_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <button disabled={loading || !query.trim()} className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#00FF9D] px-5 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50"><Search className="h-4 w-4" />{loading ? 'Searching official documents…' : 'Find evidence'}</button>
          </div>
          <p className="mt-3 text-xs text-slate-500">Search is limited to indexed official AMC documents. FundersAI stops when the evidence is insufficient.</p>
          {error ? <p className="mt-3 text-sm text-rose-200">{error}</p> : null}
        </form>

        {response ? (
          <section className="grid gap-5 lg:grid-cols-[1.45fr_0.85fr]">
            <div className="space-y-5">
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
                <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] ${response.grounded ? 'border-emerald-300/20 bg-emerald-300/10 text-emerald-100' : 'border-amber-300/20 bg-amber-300/10 text-amber-100'}`}>{response.grounded ? 'Evidence found' : 'Not enough evidence'}</span>
                <h2 className="mt-4 text-lg font-semibold">{isExtractiveFallback ? 'Matching official evidence' : 'Answer from official documents'}</h2>
                <p className="mt-1 text-xs text-slate-400">{isExtractiveFallback ? 'Relevant text was found, but a concise field-level answer could not be extracted reliably.' : 'Each statement includes a link to the supporting official document.'}</p>
                {isAbstention ? (
                  <p className="mt-4 text-sm leading-7 text-slate-200">{response.answer}</p>
                ) : isExtractiveFallback ? (
                  <p className="mt-4 rounded-xl border border-amber-300/15 bg-amber-300/[0.05] p-4 text-sm leading-6 text-amber-100">Review the matching passages under Official evidence excerpts. FundersAI has not converted them into an answer because the wording could not be verified safely.</p>
                ) : answerLines.length ? (
                  <ol className="mt-4 space-y-3">
                    {answerLines.map((line, index) => {
                      const citationMatch = line.match(/\[(\d+)]\s*$/);
                      const sourceNumber = citationMatch?.[1] || String(index + 1);
                      const source = response.sources?.[Number(sourceNumber) - 1];
                      const clean = line.replace(/^[-•]\s*/, '').replace(/\s*\[\d+]\s*$/, '');
                      return (
                        <li key={`${index}-${clean.slice(0, 20)}`} className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm leading-6 text-slate-200">
                          <span>{clean}</span>{' '}
                          {source?.source_url ? <a href={source.source_url} target="_blank" rel="noreferrer" className="whitespace-nowrap font-semibold text-[#00FF9D] hover:underline">View evidence {sourceNumber}</a> : <span className="font-semibold text-[#00FF9D]">[{sourceNumber}]</span>}
                        </li>
                      );
                    })}
                  </ol>
                ) : <p className="mt-4 text-sm leading-7 text-slate-200">{response.answer}</p>}
                {!isAbstention && !isExtractiveFallback ? (
                  <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-3 text-sm"><span>Evidence coverage</span><span className="font-semibold text-[#00FF9D]">{pct(response.claim_validation?.support_rate)}</span></div>
                    <p className="mt-1 text-xs text-slate-500">Share of displayed statements matched to the official excerpts below.</p>
                  </div>
                ) : null}
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
                <h2 className="flex items-center gap-2 text-sm font-semibold"><ShieldCheck className="h-4 w-4 text-[#00FF9D]" /> Official evidence excerpts</h2>
                <p className="mt-1 text-xs text-slate-500">Each item is a matching passage from an indexed official AMC document.</p>
                <div className="mt-3 space-y-3">
                  {(response.sources || []).map((source, index) => (
                    <article key={`${source.document_id}-${index}`} className="rounded-xl border border-white/10 bg-black/20 p-4">
                      <div className="flex items-center justify-between gap-2 text-xs">
                        <span className="font-semibold text-[#00FF9D]">Evidence excerpt {index + 1}</span>
                        <a href={source.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-slate-400 hover:text-white">Open document <ExternalLink className="h-3.5 w-3.5" /></a>
                      </div>
                      <p className="mt-2 text-[11px] text-slate-500">{[source.amc_code?.toUpperCase(), source.document_type ? source.document_type.charAt(0).toUpperCase() + source.document_type.slice(1) : '', readableDate(source.report_month)].filter(Boolean).join(' · ')}</p>
                      <details className="mt-3 border-t border-white/10 pt-3">
                        <summary className="cursor-pointer text-xs font-medium text-slate-300">View matching excerpt</summary>
                        <p className="mt-3 text-sm leading-6 text-slate-400">{source.excerpt}</p>
                      </details>
                    </article>
                  ))}
                  {!response.sources?.length ? <p className="text-sm text-slate-400">{response.retrieval?.corpus_status === 'empty' ? 'No official documents have been indexed for this fund house yet.' : 'The indexed official documents did not contain enough relevant evidence.'}</p> : null}
                </div>
              </div>
            </div>

            <div className="space-y-5">
              <div className="rounded-2xl border border-emerald-300/10 bg-emerald-300/[0.04] p-5">
                <h2 className="text-sm font-semibold">Why you can trust this result</h2>
                <ul className="mt-4 space-y-3 text-sm text-slate-300">
                  <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#00FF9D]" /> Searches only indexed official AMC documents.</li>
                  <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#00FF9D]" /> Shows the source excerpt beside every result.</li>
                  <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#00FF9D]" /> Refuses to answer when evidence is insufficient.</li>
                </ul>
              </div>

              <details className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
                <summary className="cursor-pointer text-sm font-semibold">Technical audit trail</summary>
                <p className="mt-2 text-xs text-slate-500">For reviewers and developers. This information is not needed to read the answer.</p>
                <dl className="mt-4 grid gap-3 text-xs">
                  <div><dt className="text-slate-500">Search method</dt><dd className="mt-1 text-slate-200">{searchMethod(response.retrieval?.mode)}</dd></div>
                  <div><dt className="text-slate-500">Semantic search</dt><dd className="mt-1 text-slate-200">{vectorStatus(response.retrieval?.vector_status)}</dd></div>
                  <div><dt className="text-slate-500">Additional reranking</dt><dd className="mt-1 text-slate-200">{crossEncoderStatus(response.retrieval?.cross_encoder_status)}</dd></div>
                  <div><dt className="text-slate-500">Internal versions</dt><dd className="mt-1 break-words text-slate-200">{response.retrieval_version || '—'} · {response.workflow_version || '—'}</dd></div>
                </dl>
                <div className="mt-5 border-t border-white/10 pt-4">
                  <div className="text-xs font-semibold">Models and components used</div>
                  <p className="mt-1 text-[11px] text-slate-500">Only components used for this answer are listed.</p>
                  <div className="mt-3 space-y-3">
                    {(response.model_usage || []).map((usage, index) => (
                      <div key={`${usage.stage}-${usage.model}-${index}`} className="rounded-xl border border-white/10 bg-black/20 p-3">
                        <div className="text-xs font-semibold text-slate-100">{usage.stage || 'Processing component'}</div>
                        <div className="mt-1 break-words text-[11px] text-[#00FF9D]">{[usage.provider, usage.model].filter(Boolean).join(' · ')}</div>
                        <p className="mt-1 text-[11px] leading-5 text-slate-500">{usage.purpose || 'Purpose not reported.'}</p>
                      </div>
                    ))}
                    {!response.model_usage?.length ? <p className="text-[11px] text-slate-500">Model usage was not reported by this backend revision.</p> : null}
                  </div>
                </div>
                <div className="mt-5 border-t border-white/10 pt-4">
                  <div className="text-xs font-semibold">Processing steps</div>
                  <div className="mt-3 space-y-3">
                    {(response.trace_details || []).map((step, index) => (
                      <div key={`${step.node}-${index}`} className="flex gap-3">
                        <CheckCircle2 className={`mt-0.5 h-4 w-4 shrink-0 ${step.status === 'failed' ? 'text-rose-300' : step.status === 'limited' ? 'text-amber-300' : 'text-[#00FF9D]'}`} />
                        <div><div className="text-xs font-semibold text-slate-100">{traceLabel(step.node)}</div><div className="mt-0.5 text-[11px] leading-5 text-slate-500">{Object.entries(step).filter(([key]) => !['node', 'status'].includes(key)).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${readableValue(value)}`).join(' · ')}</div></div>
                      </div>
                    ))}
                  </div>
                  <p className="mt-4 break-all text-[10px] text-slate-600">Trace ID: {response.trace_id}</p>
                </div>
              </details>
            </div>
          </section>
        ) : null}

        <details className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
          <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold"><FlaskConical className="h-4 w-4 text-[#00FF9D]" /> Developer evaluation (not part of the answer)</summary>
          <p className="mt-2 text-xs text-slate-500">A small demo benchmark comparing the current and experimental retrieval methods. It is not a production-quality claim.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {variants.map((variant) => (
              <div key={variant.retrieval_version} className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs font-semibold text-[#00FF9D]">{variantLabel(variant.configuration?.variant)}</div>
                <div className="mt-1 text-[11px] text-slate-500">{variant.retrieval_version}</div>
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div><div className="text-lg font-semibold">{variant.passed_cases}/{variant.cases}</div><div className="text-[10px] text-slate-500">Test questions passed</div></div>
                  <div><div className="text-lg font-semibold">{pct(variant.recall_at_k)}</div><div className="text-[10px] text-slate-500">Expected sources found</div></div>
                  <div><div className="text-lg font-semibold">{pct(variant.mean_reciprocal_rank)}</div><div className="text-[10px] text-slate-500">First useful source rank</div></div>
                  <div><div className="text-lg font-semibold">{pct(variant.abstention_accuracy)}</div><div className="text-[10px] text-slate-500">Correct refusals</div></div>
                </div>
                <p className="mt-3 text-[10px] text-slate-500">Live semantic search: {variant.configuration?.live_embeddings ? 'Yes' : 'No'} · Advanced reranking: {variant.configuration?.live_cross_encoder ? 'Yes' : 'No'}</p>
              </div>
            ))}
            {!variants.length ? <p className="text-sm text-slate-400">No developer evaluation report is available.</p> : null}
          </div>
        </details>
      </div>
    </main>
  );
}

export default function Page() {
  return <AuthGate><ResearchEvidencePage /></AuthGate>;
}
