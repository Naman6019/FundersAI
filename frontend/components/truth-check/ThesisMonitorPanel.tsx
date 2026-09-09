'use client';

import { useCallback, useEffect, useState } from 'react';
import { BookmarkPlus, History, LoaderCircle, PauseCircle, PlayCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { trackEvent } from '@/lib/analytics';
import { supabaseBrowser } from '@/lib/supabaseBrowser';
import type { ClaimCheckResponse, ClaimFreshness, ClaimVerdict } from './types';

type SavedEvaluation = {
  id: string;
  verdict: ClaimVerdict;
  freshness: ClaimFreshness;
  source_fingerprint: string;
  evaluated_at: string;
};

type SavedClaim = {
  id: string;
  original_text: string;
  active: boolean;
  created_at: string;
  latest_evaluation: SavedEvaluation | null;
  evaluations: SavedEvaluation[];
};

function monitorError(status: number, code?: string): string {
  if (status === 401) return 'Your session expired. Sign in again to continue.';
  if (status === 422 || code === 'claim_not_trackable') return 'Only claims with deterministic values and fingerprinted evidence can be monitored.';
  if (status === 429) return 'Too many monitor changes. Wait a moment and try again.';
  if (code === 'claim_monitor_storage_unavailable') return 'Phase 3 storage is not enabled in this environment.';
  return 'The private thesis monitor is temporarily unavailable.';
}

async function authorizationHeaders(): Promise<Record<string, string>> {
  const { data } = await supabaseBrowser.auth.getSession();
  return data.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : {};
}

function verdictStyle(verdict?: ClaimVerdict): string {
  if (verdict === 'supported') return 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200';
  if (verdict === 'contradicted') return 'border-rose-400/30 bg-rose-400/10 text-rose-200';
  if (verdict === 'mixed') return 'border-amber-400/30 bg-amber-400/10 text-amber-100';
  return 'border-white/10 bg-white/5 text-text-2';
}

export default function ThesisMonitorPanel({ result }: { result: ClaimCheckResponse | null }) {
  const [claims, setClaims] = useState<SavedClaim[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyClaimId, setBusyClaimId] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadClaims = useCallback(async () => {
    try {
      const response = await fetch('/api/funds/claim-monitor', {
        headers: await authorizationHeaders(),
        cache: 'no-store',
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(monitorError(response.status, body?.error));
      setClaims(Array.isArray(body?.claims) ? body.claims : []);
      setError('');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The private thesis monitor is temporarily unavailable.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void loadClaims(), 0);
    return () => window.clearTimeout(initialLoad);
  }, [loadClaims]);

  const saveCurrent = async () => {
    if (!result) return;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const response = await fetch('/api/funds/claim-monitor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...await authorizationHeaders() },
        body: JSON.stringify({ input: result.input }),
        cache: 'no-store',
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(monitorError(response.status, body?.error));
      setNotice('Saved. A new history row will be added only after relevant source evidence changes.');
      trackEvent('fund_truth_monitor_saved', {
        claim_count: result.claims.filter((claim) => claim.trackable).length,
        verdict: body?.evaluation?.verdict || 'unknown',
      });
      await loadClaims();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The private thesis monitor is temporarily unavailable.');
    } finally {
      setSaving(false);
    }
  };

  const setActive = async (claim: SavedClaim, active: boolean) => {
    setBusyClaimId(claim.id);
    setError('');
    setNotice('');
    try {
      const response = await fetch(`/api/funds/claim-monitor/${claim.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...await authorizationHeaders() },
        body: JSON.stringify({ active }),
        cache: 'no-store',
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(monitorError(response.status, body?.error));
      setClaims((current) => current.map((item) => (item.id === claim.id ? { ...item, active } : item)));
      setNotice(active ? 'Monitoring resumed.' : 'Monitoring paused. Existing history was preserved.');
      trackEvent(active ? 'fund_truth_monitor_resumed' : 'fund_truth_monitor_paused', {});
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The private thesis monitor is temporarily unavailable.');
    } finally {
      setBusyClaimId('');
    }
  };

  const canSave = Boolean(result?.claims.some((claim) => claim.trackable));

  return (
    <section className="space-y-4 rounded-xl border border-white/10 bg-[#08111d]/75 p-4 sm:p-5" aria-labelledby="thesis-monitor-heading">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary">Private truth ledger</p>
          <h2 id="thesis-monitor-heading" className="mt-2 text-lg font-bold text-white">Save this claim</h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-3">
            Keep an append-only record of how the evidence-backed verdict changes. No alerts are sent in this phase.
          </p>
        </div>
        {result && (
          <Button type="button" size="lg" onClick={saveCurrent} disabled={!canSave || saving}>
            {saving ? <LoaderCircle className="animate-spin" /> : <BookmarkPlus />}
            {saving ? 'Saving…' : 'Save this claim'}
          </Button>
        )}
      </div>

      {result && !canSave && (
        <p className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-100">
          This result cannot be monitored until it has deterministic values and fingerprinted official evidence.
        </p>
      )}
      {error && <p role="alert" className="rounded-lg border border-rose-400/25 bg-rose-400/10 p-3 text-sm text-rose-100">{error}</p>}
      {notice && <p role="status" className="rounded-lg border border-blue-400/25 bg-blue-400/10 p-3 text-sm text-blue-100">{notice}</p>}

      <div className="border-t border-white/10 pt-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <History className="size-4 text-primary" />
          Saved claims
        </div>
        {loading ? (
          <p className="mt-4 flex items-center gap-2 text-sm text-text-3"><LoaderCircle className="size-4 animate-spin" /> Loading private history…</p>
        ) : claims.length === 0 ? (
          <p className="mt-4 text-sm text-text-3">No saved claims yet.</p>
        ) : (
          <div className="mt-4 space-y-3">
            {claims.map((claim) => (
              <article key={claim.id} className="rounded-xl border border-white/10 bg-black/15 p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase ${verdictStyle(claim.latest_evaluation?.verdict)}`}>
                        {claim.latest_evaluation?.verdict || 'pending'}
                      </span>
                      <span className="text-xs text-text-3">Freshness: {claim.latest_evaluation?.freshness || 'unknown'}</span>
                      <span className="text-xs text-text-3">{claim.active ? 'Active' : 'Paused'}</span>
                    </div>
                    <p className="mt-3 break-words text-sm leading-relaxed text-white">{claim.original_text}</p>
                    {claim.latest_evaluation && (
                      <p className="mt-2 text-xs text-text-3">
                        Last evaluated {new Date(claim.latest_evaluation.evaluated_at).toLocaleString('en-IN')} · Fingerprint {claim.latest_evaluation.source_fingerprint.slice(0, 12)}…
                      </p>
                    )}
                  </div>
                  <Button type="button" variant="outline" size="sm" disabled={busyClaimId === claim.id} onClick={() => setActive(claim, !claim.active)}>
                    {busyClaimId === claim.id ? <LoaderCircle className="animate-spin" /> : claim.active ? <PauseCircle /> : <PlayCircle />}
                    {claim.active ? 'Pause' : 'Resume'}
                  </Button>
                </div>
                <details className="mt-4 border-t border-white/10 pt-3">
                  <summary className="cursor-pointer text-xs font-semibold text-text-2">Evaluation history ({claim.evaluations.length})</summary>
                  <ol className="mt-3 space-y-2">
                    {claim.evaluations.map((evaluation) => (
                      <li key={evaluation.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-3">
                        <span className="font-semibold text-text-2">{evaluation.verdict}</span>
                        <span>{evaluation.freshness}</span>
                        <time dateTime={evaluation.evaluated_at}>{new Date(evaluation.evaluated_at).toLocaleString('en-IN')}</time>
                        <span className="font-mono">{evaluation.source_fingerprint.slice(0, 12)}…</span>
                      </li>
                    ))}
                  </ol>
                </details>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
