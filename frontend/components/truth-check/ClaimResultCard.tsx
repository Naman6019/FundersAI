import { AlertTriangle, CheckCircle2, CircleHelp, ExternalLink, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import ShareClaimButton from './ShareClaimButton';
import type { AtomicClaim } from './types';

type Props = {
  claim: AtomicClaim;
  index: number;
  onClarification: (choice: string) => void;
};

const VERDICT_STYLES = {
  supported: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300',
  contradicted: 'border-rose-400/30 bg-rose-400/10 text-rose-300',
  mixed: 'border-amber-400/30 bg-amber-400/10 text-amber-300',
  unverifiable: 'border-slate-400/30 bg-slate-400/10 text-slate-300',
};

const FRESHNESS_STYLES = {
  current: 'text-emerald-300',
  stale: 'text-amber-300',
  unknown: 'text-slate-400',
};

function titleCase(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const PERCENT_METRICS = new Set([
  'expense_ratio',
  'cagr',
  'rolling_return',
  'max_drawdown',
  'volatility',
  'stock_exposure',
  'sector_exposure',
  'holdings_concentration',
  'portfolio_overlap',
]);

function formatScalar(key: string, value: unknown, metric: AtomicClaim['metric']): string {
  if (value === null || value === undefined) return 'Unavailable';
  if (typeof value !== 'number') return String(value);
  if (metric === 'aum' || key.includes('aum')) return `₹${value.toLocaleString('en-IN')} crore`;
  if (PERCENT_METRICS.has(metric || '') || /return|volatility|drawdown|weight|overlap|exposure|cagr/.test(key)) {
    return `${value.toLocaleString('en-IN', { maximumFractionDigits: 3 })}%`;
  }
  return value.toLocaleString('en-IN', { maximumFractionDigits: 4 });
}

function flattenValues(values: Record<string, unknown>, metric: AtomicClaim['metric']): Array<{ label: string; value: string }> {
  const rows: Array<{ label: string; value: string }> = [];
  Object.entries(values).forEach(([entity, raw]) => {
    if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
      const fields = Object.entries(raw as Record<string, unknown>)
        .filter(([key]) => !['as_of_date', 'source_fingerprint'].includes(key));
      fields.forEach(([key, value]) => rows.push({
        label: fields.length === 1 ? entity : `${entity} · ${titleCase(key)}`,
        value: formatScalar(key, value, metric),
      }));
      const date = (raw as Record<string, unknown>).as_of_date;
      if (date) rows.push({ label: `${entity} · As of`, value: String(date) });
    } else {
      rows.push({ label: titleCase(entity), value: formatScalar(entity, raw, metric) });
    }
  });
  return rows;
}

function VerdictIcon({ verdict }: { verdict: AtomicClaim['verdict'] }) {
  if (verdict === 'supported') return <CheckCircle2 className="size-5" />;
  if (verdict === 'contradicted') return <XCircle className="size-5" />;
  if (verdict === 'mixed') return <AlertTriangle className="size-5" />;
  return <CircleHelp className="size-5" />;
}

export default function ClaimResultCard({ claim, index, onClarification }: Props) {
  const values = flattenValues(claim.values, claim.metric);

  return (
    <Card className="border-white/10 bg-white/[0.025] shadow-none">
      <CardHeader className="gap-4 border-b border-white/10 p-5 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-mono uppercase tracking-[0.18em] text-text-3">Claim {index + 1}</p>
            <h2 className="text-lg font-semibold leading-snug text-white">{claim.statement}</h2>
          </div>
          <div className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold uppercase tracking-wide ${VERDICT_STYLES[claim.verdict]}`}>
            <VerdictIcon verdict={claim.verdict} />
            {titleCase(claim.verdict)}
          </div>
        </div>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs">
          <span className="text-text-3">Status: <strong className="text-text-1">{titleCase(claim.status)}</strong></span>
          <span className="text-text-3">Evidence freshness: <strong className={FRESHNESS_STYLES[claim.freshness]}>{titleCase(claim.freshness)}</strong></span>
          {claim.metric && <span className="text-text-3">Metric: <strong className="text-text-1">{titleCase(claim.metric)}</strong></span>}
        </div>
      </CardHeader>

      <CardContent className="space-y-5 p-5 sm:p-6">
        {claim.freshness === 'stale' && claim.verdict !== 'unverifiable' && (
          <p className="rounded-lg border border-amber-400/20 bg-amber-400/10 p-3 text-sm text-amber-200">
            This verdict describes the cited historical period. It is not a statement about the latest fund data.
          </p>
        )}

        {values.length > 0 && (
          <dl className="grid gap-3 sm:grid-cols-2">
            {values.map((row, rowIndex) => (
              <div key={`${row.label}-${rowIndex}`} className="rounded-lg border border-white/10 bg-black/10 p-3">
                <dt className="text-xs text-text-3">{row.label}</dt>
                <dd className="mt-1 break-words text-sm font-semibold text-white">{row.value}</dd>
              </div>
            ))}
          </dl>
        )}

        {claim.clarification && (
          <div className="rounded-xl border border-blue-400/20 bg-blue-400/5 p-4">
            <p className="text-sm font-medium text-blue-100">{claim.clarification.prompt}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {claim.clarification.choices.map((choice) => (
                <button
                  key={choice}
                  type="button"
                  onClick={() => onClarification(choice)}
                  className="rounded-full border border-blue-300/30 px-3 py-1.5 text-xs text-blue-200 transition hover:bg-blue-300/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300"
                >
                  Use {titleCase(choice)}
                </button>
              ))}
            </div>
          </div>
        )}

        {claim.limitations.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-text-2">Limits</h3>
            <ul className="mt-2 space-y-1.5 text-sm text-text-3">
              {claim.limitations.map((limitation) => <li key={limitation}>• {limitation}</li>)}
            </ul>
          </div>
        )}

        {claim.evidence.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-text-2">Official evidence</h3>
            <ul className="mt-2 space-y-2">
              {claim.evidence.map((item, evidenceIndex) => (
                <li key={`${item.source_fingerprint || item.document_id || item.source_name}-${evidenceIndex}`} className="rounded-lg border border-white/10 p-3 text-xs text-text-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium text-text-1">{item.source_name}</span>
                    {item.source_url && (
                      <a href={item.source_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-primary hover:underline">
                        Open source <ExternalLink className="size-3" />
                      </a>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono">
                    {item.as_of_date && <span>As of {item.as_of_date}</span>}
                    {item.document_id && <span>Document {item.document_id}</span>}
                    {item.source_fingerprint && <span>Fingerprint {item.source_fingerprint.slice(0, 12)}…</span>}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex items-center justify-between gap-3 border-t border-white/10 pt-4">
          <p className="text-xs text-text-3">Verdict and freshness are separate checks.</p>
          <ShareClaimButton claim={claim} />
        </div>
      </CardContent>
    </Card>
  );
}
