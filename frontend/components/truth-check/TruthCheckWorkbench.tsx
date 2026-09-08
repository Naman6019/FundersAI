'use client';

import { FormEvent, type CSSProperties, useRef, useState } from 'react';
import { FlaskConical, LoaderCircle, Pencil, RotateCw, SearchCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { supabaseBrowser } from '@/lib/supabaseBrowser';
import { trackEvent } from '@/lib/analytics';
import ClaimResultCard from './ClaimResultCard';
import ClaimEquation from './ClaimEquation';
import ThesisMonitorPanel from './ThesisMonitorPanel';
import type { ClaimCheckResponse } from './types';

const EXAMPLES = [
  'HDFC Flexi Cap Fund has a lower expense ratio than Parag Parikh Flexi Cap Fund.',
  'Parag Parikh Flexi Cap Fund holds HDFC Bank.',
  'HDFC Flexi Cap Fund is safer than Parag Parikh Flexi Cap Fund.',
];

const CLARIFICATION_LABELS: Record<string, string> = {
  max_drawdown: 'lower maximum drawdown',
  volatility: 'lower volatility',
  riskometer: 'a lower riskometer label',
  rolling_return: 'higher 3-year rolling returns',
  holdings_concentration: 'lower top-holdings concentration',
  sector_exposure: 'sector exposure',
  portfolio_overlap: 'portfolio overlap',
};

function userFacingError(status: number, code?: string): string {
  if (status === 401) return 'Your session expired. Sign in again to continue.';
  if (status === 429) return 'Too many checks. Wait a moment and try again.';
  if (status === 404) return 'This private review build is not enabled.';
  if (code === 'input_must_be_between_3_and_2000_characters') return 'Enter between 3 and 2,000 characters.';
  return 'The check could not be completed. No verdict was generated.';
}

export default function TruthCheckWorkbench() {
  const [input, setInput] = useState('');
  const [result, setResult] = useState<ClaimCheckResponse | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const primaryClaim = result?.claims[0];

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const normalizedInput = input.trim();
    if (normalizedInput.length < 3 || normalizedInput.length > 2_000) {
      setError('Enter between 3 and 2,000 characters.');
      return;
    }

    setLoading(true);
    setError('');
    setNotice('');
    setResult(null);
    const startedAt = performance.now();
    trackEvent('fund_truth_check_started', { input_length: normalizedInput.length });

    try {
      const { data } = await supabaseBrowser.auth.getSession();
      const response = await fetch('/api/funds/claim-check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(data.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : {}),
        },
        body: JSON.stringify({ input: normalizedInput }),
        cache: 'no-store',
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(userFacingError(response.status, body?.error));
      const nextResult = body as ClaimCheckResponse;
      setResult(nextResult);
      setEditing(false);
      trackEvent('fund_truth_check_completed', {
        claim_count: nextResult.claims.length,
        definitive_count: nextResult.claims.filter((claim) => claim.verdict !== 'unverifiable').length,
        clarification_count: nextResult.claims.filter((claim) => claim.status === 'clarification_required').length,
        duration_ms: Math.round(performance.now() - startedAt),
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The check could not be completed.');
    } finally {
      setLoading(false);
    }
  };

  const chooseClarification = (choice: string) => {
    const label = CLARIFICATION_LABELS[choice] || choice.replaceAll('_', ' ');
    const subjectivePattern = /\b(less risky|lower risk|safer|safe|stable|consistent|diversified)\b/i;
    setInput((current) => (subjectivePattern.test(current)
      ? current.replace(subjectivePattern, label).replace(/\bis (lower|higher|a lower)\b/i, 'has $1')
      : `${current.trim()} Use ${label} as the definition.`).slice(0, 2_000));
    setNotice(`Updated the wording to use ${label}. Review it, then run the check again.`);
    textareaRef.current?.focus();
    textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  return (
    <div
      className="space-y-6"
      style={{ '--primary': '#00ff9d', '--primary-foreground': '#04120c', '--accent': '#00ff9d', '--ring': '#00ff9d' } as CSSProperties}
    >
      <div className="grid gap-5 border-b border-line pb-4 lg:grid-cols-[380px_minmax(0,1fr)] lg:items-end">
        <header>
          <div className="flex flex-wrap items-center gap-3">
            <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-primary">Fund Truth Check</p>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300/25 bg-amber-300/[0.06] px-2.5 py-1 text-[10px] font-semibold text-amber-200"><FlaskConical className="size-3" /> Private review</span>
          </div>
          <h1 className="mt-2 font-serif-display text-4xl font-extrabold tracking-tight text-white">Claim Autopsy</h1>
          <p className="mt-2 max-w-md text-xs leading-relaxed text-text-3 sm:text-sm">We dissect the claim and show the dated evidence, calculation, and uncertainty behind every part.</p>
        </header>

        <section className="rounded-xl border border-white/10 bg-[#08111d]/80 p-3">
          <form onSubmit={submit} className="space-y-3">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <label htmlFor="fund-claim" className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-primary">{primaryClaim ? 'Claim under review' : 'Enter a claim'}</label>
              <p id="fund-claim-help" className={`mt-1 text-xs leading-relaxed text-text-3 ${primaryClaim ? 'hidden' : ''}`}>Use factual claims about supported mutual funds. Advice, predictions, and undefined terms will be declined or clarified.</p>
            </div>
            {(!primaryClaim || editing) && <span id="fund-claim-count" className="text-xs text-text-3">{input.length.toLocaleString('en-IN')} / 2,000</span>}
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch">
            {primaryClaim && !editing ? (
              <div className="flex min-h-12 min-w-0 flex-1 items-center rounded-lg border border-white/15 bg-black/20 px-4 py-2.5">
                <ClaimEquation claim={primaryClaim} resolvedEntities={result.resolved_entities} />
              </div>
            ) : (
              <textarea
                ref={textareaRef}
                id="fund-claim"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                aria-describedby="fund-claim-help fund-claim-count"
                placeholder="Example: HDFC Flexi Cap has a higher 3-year CAGR than Parag Parikh Flexi Cap."
                rows={1}
                maxLength={2_000}
                className="min-h-12 w-full resize-none rounded-lg border border-white/15 bg-black/20 px-4 py-3 text-sm leading-relaxed text-white outline-none transition placeholder:text-text-3 focus:border-primary/60 focus:ring-2 focus:ring-primary/20"
              />
            )}
            {primaryClaim && !editing && (
              <Button type="button" variant="outline" size="lg" onClick={() => { setEditing(true); requestAnimationFrame(() => textareaRef.current?.focus()); }} className="shrink-0 border-white/15 bg-transparent text-text-2 hover:border-primary/40 hover:text-primary">
                <Pencil /> Edit
              </Button>
            )}
            <Button type="submit" size="lg" disabled={loading || input.trim().length < 3} className="shrink-0 bg-[#00ff9d] text-[#04120c] hover:bg-[#00e68d] sm:min-w-40">
              {loading ? <LoaderCircle className="animate-spin" /> : result ? <RotateCw /> : <SearchCheck />}
              {loading ? 'Checking evidence…' : result ? 'Re-check claim' : 'Check claim'}
            </Button>
          </div>
          </form>

          {!result && <div className="mt-4 border-t border-white/10 pt-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-text-3">Try an example</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {EXAMPLES.map((example) => (
                <button key={example} type="button" onClick={() => { setInput(example); setResult(null); setError(''); }} className="rounded-full border border-white/10 px-3 py-1.5 text-left text-[11px] text-text-2 transition hover:border-primary/30 hover:text-white">{example}</button>
              ))}
            </div>
          </div>}
        </section>
      </div>

      {error && <div role="alert" className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</div>}
      {notice && <div role="status" className="rounded-xl border border-blue-400/30 bg-blue-400/10 p-4 text-sm text-blue-100">{notice}</div>}

      {result && (
        <section aria-live="polite" className="space-y-5">
          {result.claims.map((claim, index) => (
            <ClaimResultCard key={`${claim.statement}-${index}`} claim={claim} index={index} resolvedEntities={result.resolved_entities} onClarification={chooseClarification} />
          ))}
        </section>
      )}

      {result && <ThesisMonitorPanel result={result} />}

      <p className="border-t border-white/10 pt-4 text-xs leading-relaxed text-text-3">Research only. Results may be incomplete and are not investment advice. Verify dates and linked official evidence before relying on any statement.</p>
    </div>
  );
}
