'use client';

import { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, CheckCircle2, ExternalLink, FlaskConical, Search, ShieldCheck } from 'lucide-react';
import AuthGate from '@/components/auth/AuthGate';

type TraceStep = { node?: string; status?: string; [key: string]: unknown };
type Source = { document_id?: string; source_url?: string; excerpt?: string; score?: number; amc_code?: string; document_type?: string; report_month?: string };
type ResearchResponse = {
  answer?: string;
  grounded?: boolean;
  abstain?: boolean;
  trace_id?: string;
  workflow_version?: string;
  retrieval_version?: string;
  rewrite_count?: number;
  resolved_query?: string;
  sources?: Source[];
  trace_details?: TraceStep[];
  claim_validation?: { support_rate?: number; supported_claims?: number; claim_count?: number };
  retrieval?: { mode?: string; vector_status?: string; cross_encoder_status?: string; reranker_version?: string };
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

function pct(value: number | undefined) {
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : '—';
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
        body: JSON.stringify({ query, amc_code: amcCode || null, limit: 5 }),
      });
      if (!result.ok) throw new Error('Research workflow failed.');
      setResponse(await result.json());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Research workflow failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#060908] px-5 py-8 text-white sm:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link href="/dashboard" className="mb-3 inline-flex items-center gap-2 text-xs text-slate-400 hover:text-[#00FF9D]"><ArrowLeft className="h-3.5 w-3.5" /> Dashboard</Link>
            <h1 className="text-2xl font-semibold">Official Evidence Research</h1>
            <p className="mt-1 text-sm text-slate-400">Hybrid retrieval, bounded correction, claim validation and visible evaluation evidence.</p>
          </div>
          <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-xs text-amber-100">Dataset: {datasetStatus}</span>
        </div>

        <form onSubmit={submit} className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
          <div className="grid gap-3 md:grid-cols-[1fr_160px_auto]">
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm outline-none focus:border-[#00FF9D]/50" aria-label="Official-document question" />
            <input value={amcCode} onChange={(event) => setAmcCode(event.target.value)} className="rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm outline-none focus:border-[#00FF9D]/50" placeholder="AMC code" aria-label="AMC code" />
            <button disabled={loading || !query.trim()} className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#00FF9D] px-5 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50"><Search className="h-4 w-4" />{loading ? 'Running…' : 'Run evidence graph'}</button>
          </div>
          {error ? <p className="mt-3 text-sm text-rose-200">{error}</p> : null}
        </form>

        {response ? (
          <section className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
            <div className="space-y-5">
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
                <div className="flex flex-wrap gap-2 text-[11px]">
                  <span className={`rounded-full border px-2.5 py-1 ${response.grounded ? 'border-emerald-300/20 bg-emerald-300/10 text-emerald-100' : 'border-amber-300/20 bg-amber-300/10 text-amber-100'}`}>{response.grounded ? 'Grounded' : 'Abstained'}</span>
                  <span className="rounded-full border border-white/10 px-2.5 py-1 text-slate-300">{response.retrieval_version}</span>
                  <span className="rounded-full border border-white/10 px-2.5 py-1 text-slate-300">{response.workflow_version}</span>
                </div>
                <pre className="mt-4 whitespace-pre-wrap font-sans text-sm leading-7 text-slate-100">{response.answer}</pre>
                <div className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                  <div><div className="text-slate-500">Mode</div><div className="mt-1 text-slate-200">{response.retrieval?.mode || '—'}</div></div>
                  <div><div className="text-slate-500">Vector</div><div className="mt-1 text-slate-200">{response.retrieval?.vector_status || '—'}</div></div>
                  <div><div className="text-slate-500">Cross-encoder</div><div className="mt-1 text-slate-200">{response.retrieval?.cross_encoder_status || '—'}</div></div>
                  <div><div className="text-slate-500">Claim support</div><div className="mt-1 text-slate-200">{pct(response.claim_validation?.support_rate)}</div></div>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
                <h2 className="flex items-center gap-2 text-sm font-semibold"><ShieldCheck className="h-4 w-4 text-[#00FF9D]" /> Official sources</h2>
                <div className="mt-3 space-y-3">
                  {(response.sources || []).map((source, index) => (
                    <a key={`${source.document_id}-${index}`} href={source.source_url} target="_blank" rel="noreferrer" className="block rounded-xl border border-white/10 bg-black/20 p-4 transition hover:border-[#00FF9D]/30">
                      <div className="flex items-center justify-between gap-2 text-xs"><span className="font-semibold text-[#00FF9D]">Source {index + 1}</span><ExternalLink className="h-3.5 w-3.5 text-slate-500" /></div>
                      <p className="mt-2 text-sm leading-6 text-slate-300">{source.excerpt}</p>
                      <p className="mt-2 text-[11px] text-slate-500">{[source.amc_code, source.document_type, source.report_month].filter(Boolean).join(' · ')}</p>
                    </a>
                  ))}
                  {!response.sources?.length ? <p className="text-sm text-slate-400">No source passed the relevance and citation gates.</p> : null}
                </div>
              </div>
            </div>

            <div className="space-y-5">
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
                <h2 className="text-sm font-semibold">Judge-visible trace</h2>
                <p className="mt-1 break-all text-[10px] text-slate-500">{response.trace_id}</p>
                <div className="mt-4 space-y-3">
                  {(response.trace_details || []).map((step, index) => (
                    <div key={`${step.node}-${index}`} className="flex gap-3">
                      <CheckCircle2 className={`mt-0.5 h-4 w-4 shrink-0 ${step.status === 'failed' ? 'text-rose-300' : step.status === 'limited' ? 'text-amber-300' : 'text-[#00FF9D]'}`} />
                      <div><div className="text-xs font-semibold text-slate-100">{step.node}</div><div className="mt-0.5 text-[11px] text-slate-500">{Object.entries(step).filter(([key]) => !['node', 'status'].includes(key)).map(([key, value]) => `${key}: ${String(value)}`).join(' · ')}</div></div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>
        ) : null}

        <section className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold"><FlaskConical className="h-4 w-4 text-[#00FF9D]" /> Retrieval evaluation: v2 versus v3</h2>
          <p className="mt-1 text-xs text-slate-500">Development-seed evidence only. Live vector and cross-encoder status is recorded in each run.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {variants.map((variant) => (
              <div key={variant.retrieval_version} className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs font-semibold text-[#00FF9D]">{variant.configuration?.variant}</div>
                <div className="mt-1 text-[11px] text-slate-500">{variant.retrieval_version}</div>
                <div className="mt-4 grid grid-cols-4 gap-2 text-center"><div><div className="text-lg font-semibold">{variant.passed_cases}/{variant.cases}</div><div className="text-[10px] text-slate-500">Passed</div></div><div><div className="text-lg font-semibold">{pct(variant.recall_at_k)}</div><div className="text-[10px] text-slate-500">Recall</div></div><div><div className="text-lg font-semibold">{pct(variant.mean_reciprocal_rank)}</div><div className="text-[10px] text-slate-500">MRR</div></div><div><div className="text-lg font-semibold">{pct(variant.abstention_accuracy)}</div><div className="text-[10px] text-slate-500">Abstain</div></div></div>
                <p className="mt-3 text-[10px] text-slate-500">Live embeddings: {String(Boolean(variant.configuration?.live_embeddings))} · Cross-encoder: {String(Boolean(variant.configuration?.live_cross_encoder))}</p>
              </div>
            ))}
            {!variants.length ? <p className="text-sm text-slate-400">Generate the judge report to display the benchmark.</p> : null}
          </div>
        </section>
      </div>
    </main>
  );
}

export default function Page() {
  return <AuthGate><ResearchEvidencePage /></AuthGate>;
}
