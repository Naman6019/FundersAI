import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  Database,
  ExternalLink,
  LineChart,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import ShareClaimButton from './ShareClaimButton';
import ClaimEquation from './ClaimEquation';
import {
  buildExplanation,
  comparisonRule,
  extractAutopsyRows,
  formatDate,
  freshnessMessage,
  metricLabel,
  titleCase,
  verdictTitle,
} from './claimAutopsy';
import type { AtomicClaim, ResolvedEntity } from './types';

type Props = {
  claim: AtomicClaim;
  index: number;
  resolvedEntities: ResolvedEntity[];
  onClarification: (choice: string) => void;
};

const STEPS = [
  ['Original claim', 'Your exact statement, parsed into parts.', 'min-h-[150px]'],
  ['Resolved entities', 'Names mapped to unique AMFI scheme codes.', 'min-h-[106px]'],
  ['Metric and time window', 'The exact measure and period evaluated.', 'min-h-[94px]'],
  ['Official evidence', 'Dated data from the authoritative source.', 'min-h-[220px]'],
  ['Deterministic rule and verdict', 'A visible rule. No generated rationale.', 'min-h-0'],
];

function verdictTone(claim: AtomicClaim): string {
  if (claim.verdict === 'supported') return 'text-primary';
  if (claim.verdict === 'contradicted') return 'text-rose-300';
  if (claim.verdict === 'mixed') return 'text-amber-300';
  return 'text-text-2';
}

function VerdictIcon({ claim }: { claim: AtomicClaim }) {
  if (claim.verdict === 'supported') return <CheckCircle2 className="size-7" />;
  if (claim.verdict === 'contradicted') return <XCircle className="size-7" />;
  if (claim.verdict === 'mixed') return <AlertTriangle className="size-7" />;
  return <CircleHelp className="size-7" />;
}

function StepRail() {
  return (
    <ol className="hidden h-full lg:flex lg:flex-col">
      {STEPS.map(([title, description, heightClass], stepIndex) => (
        <li key={title} className={`relative flex gap-4 ${heightClass}`}>
          {stepIndex < STEPS.length - 1 && <span className="absolute left-[17px] top-9 h-[calc(100%-12px)] w-px bg-white/20" />}
          <span className="relative z-10 flex size-9 shrink-0 items-center justify-center rounded-full border border-primary bg-background font-mono text-sm font-bold text-primary">
            {stepIndex + 1}
          </span>
          <div className="pt-1">
            <h3 className="font-mono text-xs font-bold uppercase tracking-[0.12em] text-primary">{title}</h3>
            <p className="mt-2 max-w-[175px] text-xs leading-relaxed text-text-3">{description}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function MobileStep({ number, title }: { number: number; title: string }) {
  return (
    <div className="mb-3 flex items-center gap-2 lg:hidden">
      <span className="flex size-7 items-center justify-center rounded-full border border-primary font-mono text-xs font-bold text-primary">{number}</span>
      <h3 className="font-mono text-[11px] font-bold uppercase tracking-[0.12em] text-primary">{title}</h3>
    </div>
  );
}

function resolveName(entity: ResolvedEntity): string {
  return entity.scheme_name || entity.input || 'Unresolved fund';
}

function metricWindow(claim: AtomicClaim, endDate: string | null): string {
  if (!endDate) return 'A dated evaluation window could not be established.';
  const years = Number(claim.statement.match(/\b(\d+)[-\s]?year\b/i)?.[1] || 0);
  if (!years || !['cagr', 'rolling_return'].includes(claim.metric || '')) return `Evaluated using evidence through ${formatDate(endDate)}.`;
  const start = new Date(`${endDate}T00:00:00Z`);
  start.setUTCFullYear(start.getUTCFullYear() - years);
  start.setUTCDate(start.getUTCDate() + 1);
  return `From ${formatDate(start.toISOString().slice(0, 10))} to ${formatDate(endDate)} (inclusive)`;
}

function evidenceTitle(claim: AtomicClaim): string {
  const source = claim.evidence[0];
  if (source?.source_type === 'amfi_nav' || source?.source_name === 'AMFI NAV') return 'AMFI NAV History (Direct Plan Growth)';
  return source?.source_name || 'Official evidence';
}

export default function ClaimResultCard({ claim, index, resolvedEntities, onClarification }: Props) {
  const rows = extractAutopsyRows(claim);
  const rule = comparisonRule(claim, rows);
  const explanation = buildExplanation(claim, rows);
  const evidenceDates = Array.from(new Set(claim.evidence.map((item) => item.as_of_date).filter((date): date is string => Boolean(date))));
  const newestDate = evidenceDates.sort().at(-1) || null;
  const verified = claim.status === 'evaluated' && claim.verdict !== 'unverifiable';

  return (
    <article className="rounded-2xl border border-white/10 bg-[#08111d]/75 p-4 shadow-[0_28px_90px_rgba(0,0,0,0.2)]" aria-labelledby={`claim-${index}-heading`}>
      <div className="grid gap-6 lg:grid-cols-[230px_minmax(0,1fr)]">
        <StepRail />

        <div className="min-w-0 space-y-2">
          <section className="rounded-xl border border-white/10 bg-black/10 p-4">
            <MobileStep number={1} title="Original claim" />
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-text-3">Claim {index + 1} · parsed statement</p>
            <h2 id={`claim-${index}-heading`} className="sr-only">{claim.statement}</h2>
            <div className="mt-4">
              <ClaimEquation claim={claim} resolvedEntities={resolvedEntities} labelled />
            </div>
          </section>

          <section className="rounded-xl border border-white/10 bg-black/10 p-4">
            <MobileStep number={2} title="Resolved entities" />
            {resolvedEntities.length ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {resolvedEntities.map((entity, entityIndex) => (
                  <div key={`${entity.scheme_code || entity.input}-${entityIndex}`} className="min-w-0 border-white/10 sm:not-last:border-r sm:not-last:pr-4">
                    <p className="truncate text-sm font-medium text-white">{resolveName(entity)}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-text-3">
                      <span>AMFI scheme code</span>
                      <span className="rounded border border-white/20 px-2 py-1 font-mono text-text-1">{entity.scheme_code || 'Unresolved'}</span>
                      <span>{Math.round(entity.confidence * 100)}% match</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-text-3">No unique fund identity was resolved.</p>}
          </section>

          <section className="rounded-xl border border-white/10 bg-black/10 p-4">
            <MobileStep number={3} title="Metric and time window" />
            <div className="flex items-start gap-4">
              <LineChart className="mt-0.5 size-5 shrink-0 text-primary" />
              <div>
                <p className="text-sm font-semibold text-white">{metricLabel(claim)}</p>
                <p className="mt-1 text-xs leading-relaxed text-text-3">{metricWindow(claim, newestDate)}</p>
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-white/10 bg-black/10 p-4">
            <MobileStep number={4} title="Official evidence" />
            {claim.evidence.length ? (
              <>
                <div className="flex flex-col gap-4 border-b border-white/10 pb-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-white/15 bg-white/[0.03]"><Database className="size-5 text-primary" /></span>
                    <div className="min-w-0"><p className="text-sm font-semibold text-white">{evidenceTitle(claim)}</p><p className="mt-1 text-xs text-text-3">{claim.evidence[0].source_type === 'amfi_nav' ? 'Association of Mutual Funds in India (AMFI)' : `As of ${formatDate(claim.evidence[0].as_of_date)}`}</p></div>
                  </div>
                  {claim.evidence[0].source_url && (
                    <a href={claim.evidence[0].source_url} target="_blank" rel="noreferrer noopener" className="inline-flex w-fit items-center gap-2 rounded-md border border-white/15 px-3 py-2 text-xs font-medium text-text-1 transition hover:border-primary/50 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">Inspect proof <ExternalLink className="size-3.5" /></a>
                  )}
                </div>
                {rows.length > 0 && (
                  <div className="mt-4 overflow-x-auto rounded-lg border border-white/10">
                    <table className="w-full min-w-[680px] border-collapse text-left text-xs">
                      <thead className="bg-white/[0.025] font-mono uppercase tracking-[0.12em] text-text-3"><tr><th className="px-4 py-2 font-medium">Scheme</th><th className="px-4 py-2 font-medium">AMFI scheme code</th><th className="px-4 py-2 font-medium">As of</th><th className="px-4 py-2 font-medium">{metricLabel(claim)}</th></tr></thead>
                      <tbody>{rows.map((row, rowIndex) => (
                        <tr key={`${row.entity}-${rowIndex}`} className="border-t border-white/10"><td className="px-4 py-2.5 text-text-1"><span className="mr-2 text-primary">•</span>{row.entity}</td><td className="px-4 py-2.5 font-mono text-text-2">{resolvedEntities.find((entity) => entity.scheme_name === row.entity)?.scheme_code || '—'}</td><td className="px-4 py-2.5 text-text-3">{formatDate(row.date)}</td><td className={`px-4 py-2.5 font-mono font-semibold ${rowIndex === 0 ? 'text-primary' : 'text-text-1'}`}>{row.primary?.value || 'Unavailable'}</td></tr>
                      ))}</tbody>
                    </table>
                  </div>
                )}
              </>
            ) : <p className="text-sm text-text-3">No official evidence could be attached to this claim.</p>}
          </section>

          <section className="rounded-xl border border-white/10 bg-black/10 p-4">
            <MobileStep number={5} title="Deterministic rule and verdict" />
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(300px,0.7fr)] xl:items-center">
              <div className={`flex items-start gap-3 ${verdictTone(claim)}`}><VerdictIcon claim={claim} /><div><h3 className="font-serif-display text-xl font-bold sm:text-2xl">{verdictTitle(claim)}</h3><p className="mt-2 max-w-3xl text-sm leading-relaxed text-text-2">{explanation}</p></div></div>
              <div className="border-white/10 xl:border-l xl:pl-6"><p className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-3">Deterministic rule</p><p className="mt-2 break-words font-mono text-xl text-white"><span className={verdictTone(claim)}>{rule.rule}</span>{rule.difference ? <span className="text-text-3"> = <span className={verdictTone(claim)}>+{rule.difference}</span></span> : null}</p></div>
            </div>
            {claim.clarification && (
              <div className="mt-5 border-t border-white/10 pt-4"><p className="text-sm font-medium text-white">Choose the measurable meaning you intend:</p><div className="mt-3 flex flex-wrap gap-2">{claim.clarification.choices.map((choice) => <button key={choice} type="button" onClick={() => onClarification(choice)} className="rounded-full border border-primary/30 px-3 py-1.5 text-xs text-primary transition hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">Use {titleCase(choice)}</button>)}</div></div>
            )}
          </section>

          <div className={`flex gap-3 rounded-xl border p-4 ${claim.freshness === 'stale' ? 'border-amber-400/35 bg-amber-400/[0.07] text-amber-200' : 'border-white/10 bg-white/[0.02] text-text-2'}`}>
            {claim.freshness === 'stale' ? <AlertTriangle className="mt-0.5 size-5 shrink-0" /> : <ShieldCheck className="mt-0.5 size-5 shrink-0 text-primary" />}
            <div><p className="text-sm font-semibold">{freshnessMessage(claim)}</p><p className="mt-1 text-xs leading-relaxed opacity-80">Verdict and freshness are separate checks.</p></div>
          </div>

          <section className="rounded-xl border border-white/10 bg-black/10 p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-sky-300">Where uncertainty enters</p>
            <p className="mt-1 text-xs text-text-3">{claim.freshness === 'current' ? 'Every displayed check is verified.' : 'The unresolved checks below define the boundary of this result.'}</p>
            <div className="mt-3 grid gap-3 text-xs sm:grid-cols-3 xl:grid-cols-5">
              {[
                ['Entity identity', resolvedEntities.length > 0 && resolvedEntities.every((entity) => Boolean(entity.scheme_code))],
                ['Metric definition', Boolean(claim.metric)],
                ['Official source', claim.evidence.length > 0],
                ['Calculation', verified],
                ['Freshness', claim.freshness === 'current'],
              ].map(([label, okay]) => (
                <div key={String(label)} className="flex items-center gap-2 border-white/10 sm:not-last:border-r sm:not-last:pr-3">
                  {okay ? <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/20 text-primary"><Check className="size-3" /></span> : <AlertTriangle className="size-4 shrink-0 text-amber-300" />}
                  <div><p className="text-text-2">{label}</p><p className={okay ? 'text-primary' : 'text-amber-300'}>{okay ? 'Verified' : 'Unresolved'}</p></div>
                </div>
              ))}
            </div>
          </section>

          {claim.evidence[0] && (
            <section className="grid gap-3 rounded-xl border border-white/10 bg-black/10 p-4 text-xs sm:grid-cols-[1.5fr_0.7fr_1fr_auto] sm:items-center">
              <div><p className="text-text-3">Data source</p><p className="mt-1 font-medium text-text-1">{evidenceTitle(claim)}</p></div>
              <div><p className="text-text-3">As of</p><p className="mt-1 text-text-1">{formatDate(claim.evidence[0].as_of_date)}</p></div>
              <div><p className="text-text-3">Coverage</p><p className="mt-1 text-text-1">{metricWindow(claim, claim.evidence[0].as_of_date).replace(/^From /, '')}</p></div>
              {claim.evidence[0].source_url && <a href={claim.evidence[0].source_url} target="_blank" rel="noreferrer noopener" className="inline-flex w-fit items-center gap-2 rounded-md border border-white/15 px-3 py-2 font-medium text-text-1 hover:border-primary/50 hover:text-primary">Inspect proof <ExternalLink className="size-3.5" /></a>}
            </section>
          )}

          {claim.limitations.length > 0 && <section className="rounded-xl border border-white/10 bg-black/10 p-4"><h3 className="text-xs font-semibold uppercase tracking-wide text-text-2">Limits</h3><ul className="mt-2 space-y-1.5 text-sm text-text-3">{claim.limitations.map((limitation) => <li key={limitation}>• {limitation}</li>)}</ul></section>}

          <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:items-center sm:justify-between">
            <details className="group text-xs text-text-3">
              <summary className="flex cursor-pointer list-none items-center gap-2 font-medium text-text-2"><ChevronDown className="size-4 transition group-open:rotate-180" /> Technical details &amp; internal status</summary>
              <div className="mt-3 space-y-2 rounded-lg border border-white/10 bg-black/20 p-3 font-mono"><p>Status: {claim.status} · Verdict: {claim.verdict} · Freshness: {claim.freshness}</p><p>Metric: {claim.metric || 'none'} · Operator: {claim.operator || 'none'} · Trackable: {String(claim.trackable)}</p>{claim.evidence.map((item, evidenceIndex) => <p key={`${item.source_fingerprint || item.document_id || evidenceIndex}`} className="break-all">Evidence {evidenceIndex + 1}: {item.document_id || 'no document id'} · {item.source_fingerprint || 'no fingerprint'}</p>)}</div>
            </details>
            <ShareClaimButton claim={claim} />
          </div>
        </div>
      </div>
    </article>
  );
}
