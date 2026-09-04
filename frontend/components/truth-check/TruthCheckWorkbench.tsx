'use client';

import { FormEvent, useRef, useState } from 'react';
import { LoaderCircle, SearchCheck, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { supabaseBrowser } from '@/lib/supabaseBrowser';
import { trackEvent } from '@/lib/analytics';
import ClaimResultCard from './ClaimResultCard';
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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
    setInput((current) => subjectivePattern.test(current)
      ? current.replace(subjectivePattern, label)
      : `${current.trim()} Use ${label} as the definition.`);
    setNotice(`Updated the wording to use ${label}. Review it, then run the check again.`);
    textareaRef.current?.focus();
    textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5 sm:p-7">
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label htmlFor="fund-claim" className="text-sm font-semibold text-white">What claim should be checked?</label>
            <p id="fund-claim-help" className="mt-1 text-xs leading-relaxed text-text-3">
              Use factual claims about supported mutual funds. Advice, predictions, and undefined terms will be declined or clarified.
            </p>
          </div>
          <textarea
            ref={textareaRef}
            id="fund-claim"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            aria-describedby="fund-claim-help fund-claim-count"
            placeholder="Example: Fund A has a lower expense ratio than Fund B."
            rows={5}
            maxLength={2_000}
            className="w-full resize-y rounded-xl border border-white/15 bg-black/20 px-4 py-3 text-sm text-white outline-none transition placeholder:text-text-3 focus:border-primary/60 focus:ring-2 focus:ring-primary/20"
          />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span id="fund-claim-count" className="text-xs text-text-3">{input.length.toLocaleString('en-IN')} / 2,000</span>
            <Button type="submit" size="lg" disabled={loading || input.trim().length < 3}>
              {loading ? <LoaderCircle className="animate-spin" /> : <SearchCheck />}
              {loading ? 'Checking evidence…' : 'Check claim'}
            </Button>
          </div>
        </form>

        <div className="mt-6 border-t border-white/10 pt-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-text-3">Try an example</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {EXAMPLES.map((example) => (
              <button key={example} type="button" onClick={() => { setInput(example); setResult(null); setError(''); }} className="rounded-full border border-white/10 px-3 py-2 text-left text-xs text-text-2 transition hover:border-primary/30 hover:text-white">
                {example}
              </button>
            ))}
          </div>
        </div>
      </section>

      {error && <div role="alert" className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</div>}
      {notice && <div role="status" className="rounded-xl border border-blue-400/30 bg-blue-400/10 p-4 text-sm text-blue-100">{notice}</div>}

      {result && (
        <section aria-live="polite" className="space-y-5">
          <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-black/10 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-white">{result.claims.length} atomic {result.claims.length === 1 ? 'claim' : 'claims'} checked</p>
              <p className="mt-1 text-xs text-text-3">Generated {new Date(result.generated_at).toLocaleString('en-IN')}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {result.resolved_entities.map((entity, index) => (
                <span key={`${entity.scheme_code || entity.input}-${index}`} className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-text-2">
                  {entity.scheme_name || entity.input}{entity.scheme_code ? ` · ${entity.scheme_code}` : ''}
                </span>
              ))}
            </div>
          </div>
          {result.claims.map((claim, index) => (
            <ClaimResultCard key={`${claim.statement}-${index}`} claim={claim} index={index} onClarification={chooseClarification} />
          ))}
        </section>
      )}

      <aside className="grid gap-3 rounded-xl border border-primary/20 bg-primary/5 p-5 text-sm text-text-2 sm:grid-cols-[auto_1fr]">
        <ShieldCheck className="mt-0.5 size-5 text-primary" />
        <div>
          <p className="font-semibold text-white">Private review build</p>
          <p className="mt-1 leading-relaxed">Checks are not saved by this interface. Results are research-only, may be incomplete, and are not investment advice. Verify dates and linked official evidence before relying on any statement.</p>
        </div>
      </aside>
    </div>
  );
}
