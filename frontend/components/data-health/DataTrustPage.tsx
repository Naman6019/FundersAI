'use client';

import Link from 'next/link';
import {
  ArrowLeft,
  BookOpenCheck,
  CheckCircle2,
  Clock3,
  Database,
  FileSearch,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import StatusLabel from '@/components/data-health/StatusLabel';
import { useDataHealthContext } from '@/components/data-health/DataHealthProvider';
import {
  DataHealthMetric,
  STATUS_GLOSSARY,
  dataHealthSummary,
  statusColorClass,
  statusExplanation,
} from '@/lib/dataHealth';

function formatDate(value?: string | null): string {
  if (!value) return 'Not available';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short', hour12: false });
}

function formatCoverage(value?: number): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return `${Math.round(value * 100)}%`;
}

function MetricCard({ metric }: { metric: DataHealthMetric }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
      <StatusLabel
        label={metric.label}
        status={metric.status}
        description={statusExplanation(metric.status)}
        details={(
          <>
            <span className="block">{metric.note || 'No additional status note was returned.'}</span>
            <span className="mt-1 block">Data last updated: {formatDate(metric.last_updated)}</span>
          </>
        )}
      />
      <p className={`mt-5 text-3xl font-semibold tracking-tight ${statusColorClass(metric.status)}`}>{metric.status}</p>
      <p className="mt-3 text-sm leading-6 text-slate-300">{metric.note || 'No additional status note was returned.'}</p>
      <p className="mt-4 text-[11px] uppercase tracking-[0.13em] text-slate-500">
        Data updated {formatDate(metric.last_updated)}
      </p>
    </article>
  );
}

const PIPELINE_STAGES = [
  {
    title: 'Discover and validate',
    body: 'Official AMC pages are checked for the correct host, document type, reporting month, file signature, and parser readiness.',
    icon: FileSearch,
  },
  {
    title: 'Acquire and retain',
    body: 'Accepted raw documents are downloaded and retained in R2. Acquisition does not automatically change app data.',
    icon: Database,
  },
  {
    title: 'Parse and review',
    body: 'Documents are parsed into structured fields. Partial, failed, or questionable results remain visible for review.',
    icon: BookOpenCheck,
  },
  {
    title: 'Serve validated snapshots',
    body: 'Only validated normalized records and last-known-good snapshots are used by the research workspace.',
    icon: ShieldCheck,
  },
];

const ANSWER_LABELS = [
  ['As of', 'The source and data date used for an answer. It is answer-specific, not a global pipeline status.'],
  ['Confidence', 'A qualified resolver or evidence-support signal, never a prediction of investment performance.'],
  ['Coverage', 'How much of the requested structured data or official evidence was available.'],
  ['Missing fields', 'Expected fields that were absent and therefore excluded from deterministic conclusions.'],
  ['Reasoning summary', 'A concise description of the checked data and limits, without exposing private model reasoning.'],
  ['Claim sources', 'Official-document links attached to the claims they support.'],
];

export default function DataTrustPage() {
  const {
    data,
    error,
    isRefreshing,
    lastAttemptedCheck,
    lastSuccessfulCheck,
    refresh,
  } = useDataHealthContext();
  const pipeline = data.pipeline || {};
  const quality = data.amc_parser_quality || [];
  const summary = dataHealthSummary(data.metrics);
  const pipelineStats = [
    ['Documents', pipeline.total_documents],
    ['Parsed', pipeline.parsed_count],
    ['Pending', pipeline.pending_count],
    ['Needs review', pipeline.needs_review_count],
    ['Failed', pipeline.failed_count],
    ['Skipped', pipeline.skipped_count],
  ];

  return (
    <main className="min-h-screen bg-[#030711] text-white">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-[#030711]/92 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
          <div>
            <Link href="/dashboard" className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 transition hover:text-white">
              <ArrowLeft className="h-3.5 w-3.5" /> Research workspace
            </Link>
            <h1 className="mt-1 text-xl font-semibold">Data &amp; Trust</h1>
          </div>
          <div className="flex items-center gap-3">
            <StatusLabel
              label="Live status"
              status={summary.status}
              description={summary.label}
              details={`Last successful check: ${formatDate(lastSuccessfulCheck)}`}
            />
            <button
              type="button"
              onClick={() => void refresh()}
              disabled={isRefreshing}
              className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-[#66a3ff]/30 bg-[#66a3ff]/10 px-3 text-xs font-semibold text-[#cce0ff] transition hover:border-[#66a3ff]/60 disabled:opacity-60"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              {isRefreshing ? 'Checking…' : 'Refresh status'}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-16 px-5 py-10 sm:px-8 sm:py-14">
        <section aria-labelledby="live-data-title">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#00FF9D]">Read-only production view</p>
              <h2 id="live-data-title" className="mt-3 text-3xl font-semibold tracking-tight sm:text-5xl">What the workspace can use now</h2>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300">
                These labels are refreshed from stored production data every minute while this page is visible.
                A refresh checks status only—it never starts discovery, ingestion, parsing, sync, or promotion.
              </p>
            </div>
            <div className="text-right text-[11px] leading-5 text-slate-500">
              <p>Last successful check: {formatDate(lastSuccessfulCheck)}</p>
              <p>Last attempted check: {formatDate(lastAttemptedCheck)}</p>
            </div>
          </div>
          {error ? (
            <p className="mt-5 rounded-xl border border-rose-300/20 bg-rose-300/[0.07] px-4 py-3 text-sm text-rose-100" aria-live="polite">
              {error} Last successful values remain visible.
            </p>
          ) : null}
          <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {data.metrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}
          </div>
        </section>

        <section aria-labelledby="pipeline-title">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#66a3ff]">Pipeline boundaries</p>
          <h2 id="pipeline-title" className="mt-3 text-3xl font-semibold tracking-tight">Acquisition and promotion stay separate</h2>
          <p className="mt-4 max-w-4xl text-sm leading-7 text-slate-300">
            Finding or downloading an official document is evidence of acquisition, not proof that its contents are ready for answers.
            Parser checks, review states, normalized storage, and runtime freshness remain separate gates.
          </p>
          <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {PIPELINE_STAGES.map(({ title, body, icon: Icon }, index) => (
              <article key={title} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                <div className="flex items-center justify-between">
                  <Icon className="h-5 w-5 text-[#00FF9D]" />
                  <span className="text-xs text-slate-500">0{index + 1}</span>
                </div>
                <h3 className="mt-5 text-lg font-semibold">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-400">{body}</p>
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="documents-title" className="rounded-3xl border border-white/10 bg-white/[0.025] p-5 sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#00FF9D]">Official AMC documents</p>
              <h2 id="documents-title" className="mt-3 text-2xl font-semibold">Acquisition and parser status</h2>
            </div>
            <div className="text-[11px] leading-5 text-slate-500">
              <p>Last downloaded: {formatDate(pipeline.last_downloaded_at)}</p>
              <p>Last parse attempt: {formatDate(pipeline.last_parse_attempt_at)}</p>
              <p>Last successful parse: {formatDate(pipeline.last_success_at)}</p>
            </div>
          </div>
          <div className="mt-7 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            {pipelineStats.map(([label, value]) => (
              <div key={String(label)} className="rounded-xl border border-white/10 bg-black/20 p-4">
                <p className="text-2xl font-semibold">{typeof value === 'number' ? value : '—'}</p>
                <p className="mt-1 text-xs text-slate-400">{label}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <thead className="border-b border-white/10 text-slate-500">
                <tr>
                  <th className="px-3 py-3 font-semibold">AMC</th>
                  <th className="px-3 py-3 font-semibold">Factsheet</th>
                  <th className="px-3 py-3 font-semibold">Holdings</th>
                  <th className="px-3 py-3 font-semibold">TER</th>
                  <th className="px-3 py-3 font-semibold">Benchmark</th>
                  <th className="px-3 py-3 font-semibold">Risk label</th>
                  <th className="px-3 py-3 font-semibold">Review</th>
                </tr>
              </thead>
              <tbody>
                {quality.map((row) => (
                  <tr key={row.amc} className="border-b border-white/5 text-slate-300">
                    <td className="px-3 py-4 font-semibold text-white">{row.amc}</td>
                    <td className="px-3 py-4">{row.latest_factsheet_month || '—'}</td>
                    <td className="px-3 py-4" title={row.holdings_source_note || undefined}>{row.latest_holdings_month || '—'}</td>
                    <td className="px-3 py-4">{formatCoverage(row.ter_coverage)}</td>
                    <td className="px-3 py-4">{formatCoverage(row.benchmark_coverage)}</td>
                    <td className="px-3 py-4">{formatCoverage(row.risk_label_coverage)}</td>
                    <td className="px-3 py-4">{row.parse_review_count ?? '—'}</td>
                  </tr>
                ))}
                {!quality.length ? (
                  <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500">No AMC quality rows were returned.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="labels-title">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#66a3ff]">Label guide</p>
          <h2 id="labels-title" className="mt-3 text-3xl font-semibold tracking-tight">What every status means</h2>
          <div className="mt-7 flex flex-wrap gap-3">
            {Object.entries(STATUS_GLOSSARY).map(([status, description]) => (
              <StatusLabel key={status} label="Status" status={status} description={description} />
            ))}
          </div>

          <h3 className="mt-12 text-xl font-semibold">Labels attached to an answer</h3>
          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {ANSWER_LABELS.map(([label, body]) => (
              <article key={label} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                <p className="font-semibold text-white">{label}</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{body}</p>
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="why-title" className="overflow-hidden rounded-3xl border border-[#00FF9D]/20 bg-[linear-gradient(135deg,rgba(0,255,157,0.09),rgba(102,163,255,0.06))] p-7 sm:p-10">
          <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#00FF9D]">Product motivation</p>
              <h2 id="why-title" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">Why FundersAI was built</h2>
              <p className="mt-5 text-sm leading-7 text-slate-200">
                Mutual-fund research is fragmented across factsheets, portfolio disclosures, changing web pages, and market-data providers.
                Many tools present a clean answer without making data age, missing fields, or source support equally clear.
              </p>
              <p className="mt-4 text-sm leading-7 text-slate-300">
                FundersAI brings structured comparisons and official-document evidence into one research workspace while keeping uncertainty visible.
                The goal is better inspection and comparison—not personalized advice or buy, sell, and hold calls.
              </p>
            </div>
            <div className="grid gap-3">
              {[
                'Official-source evidence stays inspectable.',
                'Stale, partial, and missing data remain visible.',
                'Deterministic metrics stay separate from AI explanation.',
                'Unsupported claims are qualified or refused.',
              ].map((item) => (
                <div key={item} className="flex items-start gap-3 rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-slate-200">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#00FF9D]" />
                  {item}
                </div>
              ))}
            </div>
          </div>
        </section>

        <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-white/10 py-6 text-xs text-slate-500">
          <span className="inline-flex items-center gap-2"><Clock3 className="h-3.5 w-3.5" /> One-minute foreground refresh</span>
          <span>Research only · verify independently</span>
        </footer>
      </div>
    </main>
  );
}

