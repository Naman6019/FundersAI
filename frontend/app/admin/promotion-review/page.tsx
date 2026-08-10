'use client';

import { useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/admin/client';
import { EmptyState, ErrorState, LoadingState, Panel } from '@/components/admin/AdminUi';

type Decision = {
  id: string;
  resolution: 'use_staged' | 'use_live' | 'exclude';
  reviewed_by: string;
  note: string | null;
  created_at: string;
  promoted_at: string | null;
  promotion_result: Record<string, unknown> | null;
};

type RiskRow = {
  family_id: string;
  staged_scheme_code: string;
  raw_scheme_name: string;
  staged_risk_level: string;
  mismatched_live_schemes: { scheme_code: string; scheme_name: string | null; live_risk_level: string }[];
  source_document_id: string;
  source_url: string | null;
  decision: Decision | null;
};

type HoldingsRow = {
  scheme_key: string;
  mapped_family_id: string | null;
  raw_scheme_name: string | null;
  total_percent_aum: number | null;
  expected_band: [number, number];
  validation_statuses: string[];
  holding_row_ids: string[];
  holding_row_count: number;
  holding_rows_missing_isin: number;
  also_staged_in_n_other_documents: number;
  source_document_id: string;
  source_url: string | null;
  decision: Decision | null;
};

type Scope = 'risk' | 'holdings';

const AMC_OPTIONS = ['icici', 'kotak', 'hdfc', 'axis', 'nippon', 'motilal', 'mirae', 'dsp', 'aditya_birla', 'ppfas', 'sbi', 'uti'];

function DecisionBadge({ decision }: { decision: Decision | null }) {
  if (!decision) return <span className="text-[#8ea6cb]">Not reviewed</span>;
  const color =
    decision.resolution === 'use_staged'
      ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200'
      : decision.resolution === 'exclude'
      ? 'border-slate-400/35 bg-slate-500/10 text-slate-200'
      : 'border-amber-400/40 bg-amber-400/10 text-amber-200';
  return (
    <div className="space-y-1">
      <span className={`rounded-full border px-2 py-0.5 text-[11px] ${color}`}>{decision.resolution}</span>
      <div className="text-[10px] text-[#8ea6cb]">by {decision.reviewed_by}</div>
      {decision.promoted_at ? (
        <div className="text-[10px] text-emerald-300">promoted {new Date(decision.promoted_at).toLocaleString()}</div>
      ) : decision.resolution === 'use_staged' ? (
        <div className="text-[10px] text-amber-300">not yet promoted</div>
      ) : null}
    </div>
  );
}

export default function PromotionReviewPage() {
  const [amc, setAmc] = useState('icici');
  const [scope, setScope] = useState<Scope>('risk');
  const [reportMonth, setReportMonth] = useState('2026-06-01');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [riskRows, setRiskRows] = useState<RiskRow[]>([]);
  const [holdingsRows, setHoldingsRows] = useState<HoldingsRow[]>([]);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [noteDraft, setNoteDraft] = useState<Record<string, string>>({});
  const [confirmDraft, setConfirmDraft] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await adminFetch(
      `/api/admin/promotion-review/flags?amc=${encodeURIComponent(amc)}&scope=${scope}&report_month=${encodeURIComponent(reportMonth)}`
    );
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(String((payload as { error?: string }).error || 'Failed to load flagged rows'));
      setLoading(false);
      return;
    }
    if (scope === 'risk') setRiskRows((payload.rows as RiskRow[]) || []);
    else setHoldingsRows((payload.rows as HoldingsRow[]) || []);
    setLoading(false);
  }, [amc, scope, reportMonth]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const decideRisk = useCallback(
    async (row: RiskRow, resolution: 'use_staged' | 'use_live' | 'exclude') => {
      const key = `risk:${row.family_id}`;
      setBusyKey(key);
      setMessage(null);
      const res = await adminFetch('/api/admin/promotion-review/decisions', {
        method: 'POST',
        body: JSON.stringify({
          amc,
          report_month: reportMonth,
          scope: 'risk',
          subject_key: row.family_id,
          subject_label: row.raw_scheme_name,
          resolution,
          decided_value: { risk_level: row.staged_risk_level, mismatched_live_schemes: row.mismatched_live_schemes },
          source_document_id: row.source_document_id,
          note: noteDraft[key] || null,
        }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        setMessage(String((payload as { error?: string }).error || 'Failed to record decision'));
        setBusyKey(null);
        return;
      }
      setMessage(`Recorded: ${row.raw_scheme_name} -> ${resolution}`);
      await load();
      setBusyKey(null);
    },
    [amc, reportMonth, noteDraft, load]
  );

  const decideHoldings = useCallback(
    async (row: HoldingsRow, resolution: 'use_staged' | 'use_live' | 'exclude') => {
      const key = `holdings:${row.scheme_key}`;
      setBusyKey(key);
      setMessage(null);
      const res = await adminFetch('/api/admin/promotion-review/decisions', {
        method: 'POST',
        body: JSON.stringify({
          amc,
          report_month: reportMonth,
          scope: 'holdings',
          subject_key: row.scheme_key,
          subject_label: row.raw_scheme_name || row.scheme_key,
          resolution,
          decided_value: { holding_row_ids: row.holding_row_ids, total_percent_aum: row.total_percent_aum },
          source_document_id: row.source_document_id,
          note: noteDraft[key] || null,
        }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        setMessage(String((payload as { error?: string }).error || 'Failed to record decision'));
        setBusyKey(null);
        return;
      }
      setMessage(`Recorded: ${row.raw_scheme_name || row.scheme_key} -> ${resolution}`);
      await load();
      setBusyKey(null);
    },
    [amc, reportMonth, noteDraft, load]
  );

  const promote = useCallback(
    async (decisionId: string, key: string) => {
      if (confirmDraft[key] !== 'PROMOTE') {
        setMessage('Type PROMOTE in the confirm box first.');
        return;
      }
      setBusyKey(key);
      setMessage(null);
      const res = await adminFetch('/api/admin/promotion-review/promote', {
        method: 'POST',
        body: JSON.stringify({ decision_id: decisionId, confirm_phrase: confirmDraft[key] }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        setMessage(String((payload as { error?: string; detail?: string }).error || (payload as { detail?: string }).detail || 'Promotion failed'));
        setBusyKey(null);
        return;
      }
      setMessage('Promoted to production.');
      await load();
      setBusyKey(null);
    },
    [confirmDraft, load]
  );

  return (
    <div className="space-y-4">
      <Panel>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs text-[#9fb7dc]">
            AMC
            <select
              value={amc}
              onChange={(e) => setAmc(e.target.value)}
              className="mt-1 block rounded-lg border border-white/15 bg-[#101d34] px-2 py-1.5 text-xs text-[#d6e6ff]"
            >
              {AMC_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-[#9fb7dc]">
            Scope
            <div className="mt-1 flex gap-1">
              {(['risk', 'holdings'] as Scope[]).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setScope(option)}
                  className={`rounded-full border px-3 py-1 text-xs ${scope === option ? 'border-[#68a7ff] bg-[#17325a] text-white' : 'border-white/15 text-[#b7c9e6]'}`}
                >
                  {option}
                </button>
              ))}
            </div>
          </label>
          <label className="text-xs text-[#9fb7dc]">
            Report month
            <input
              value={reportMonth}
              onChange={(e) => setReportMonth(e.target.value)}
              placeholder="2026-06-01"
              className="mt-1 block w-32 rounded-lg border border-white/15 bg-[#101d34] px-2 py-1.5 text-xs text-[#d6e6ff]"
            />
          </label>
          <button
            type="button"
            onClick={() => load()}
            className="ml-auto rounded-lg border border-white/15 bg-[#142441] px-3 py-1.5 text-xs text-[#c7daf5]"
          >
            Refresh
          </button>
        </div>
        <p className="mt-2 text-xs text-[#8ea6cb]">
          Flags staged-vs-live conflicts blocking promotion, reusing the exact conflict logic from{' '}
          <code>promote_mf_disclosures.py</code>. Resolving records a decision only. Promoting is a second, separately
          confirmed step and writes to production runtime tables (
          <code>mutual_fund_core_snapshot</code> for risk, <code>mf_scheme_holdings</code> +{' '}
          <code>promote_mf_holdings_document_v2</code> for holdings).
        </p>
        {message ? <p className="mt-2 text-xs text-[#9fb7dc]">{message}</p> : null}
      </Panel>

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} />
      ) : scope === 'risk' ? (
        riskRows.length === 0 ? (
          <EmptyState message="No risk conflicts flagged for this AMC/month." />
        ) : (
          <Panel>
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs">
                <thead className="sticky top-0 bg-[#0d172a] text-[#95afd5]">
                  <tr>
                    <th className="px-2 py-2 text-left">Family / Scheme</th>
                    <th className="px-2 py-2 text-left">Staged risk</th>
                    <th className="px-2 py-2 text-left">Live mismatches</th>
                    <th className="px-2 py-2 text-left">Source</th>
                    <th className="px-2 py-2 text-left">Decision</th>
                    <th className="px-2 py-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {riskRows.map((row) => {
                    const key = `risk:${row.family_id}`;
                    const canPromote = row.decision?.resolution === 'use_staged' && !row.decision.promoted_at;
                    return (
                      <tr key={row.family_id} className="border-t border-white/10 align-top">
                        <td className="px-2 py-2">
                          <div className="font-medium text-[#d6e6ff]">{row.raw_scheme_name}</div>
                          <div className="text-[10px] text-[#8ea6cb]">{row.family_id}</div>
                        </td>
                        <td className="px-2 py-2 text-[#d6e6ff]">{row.staged_risk_level}</td>
                        <td className="px-2 py-2">
                          {row.mismatched_live_schemes.map((m) => (
                            <div key={m.scheme_code} className="text-[#b7c9e6]">
                              {m.scheme_code}: <span className="text-amber-300">{m.live_risk_level}</span>
                            </div>
                          ))}
                        </td>
                        <td className="px-2 py-2">
                          {row.source_url ? (
                            <a href={row.source_url} target="_blank" rel="noreferrer" className="text-[#68a7ff] hover:underline">
                              PDF
                            </a>
                          ) : (
                            '-'
                          )}
                        </td>
                        <td className="px-2 py-2">
                          <DecisionBadge decision={row.decision} />
                        </td>
                        <td className="px-2 py-2">
                          <div className="flex flex-col items-end gap-1">
                            <div className="flex justify-end gap-1">
                              <button
                                type="button"
                                disabled={Boolean(busyKey)}
                                onClick={() => decideRisk(row, 'use_staged')}
                                className="rounded-lg border border-emerald-400/40 bg-emerald-500/10 px-2 py-1 text-[11px] text-emerald-200 disabled:opacity-50"
                              >
                                Use staged
                              </button>
                              <button
                                type="button"
                                disabled={Boolean(busyKey)}
                                onClick={() => decideRisk(row, 'use_live')}
                                className="rounded-lg border border-amber-400/40 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-200 disabled:opacity-50"
                              >
                                Keep live
                              </button>
                              <button
                                type="button"
                                disabled={Boolean(busyKey)}
                                onClick={() => decideRisk(row, 'exclude')}
                                className="rounded-lg border border-slate-400/35 bg-slate-500/10 px-2 py-1 text-[11px] text-slate-200 disabled:opacity-50"
                              >
                                Exclude
                              </button>
                            </div>
                            <input
                              value={noteDraft[key] || ''}
                              onChange={(e) => setNoteDraft((prev) => ({ ...prev, [key]: e.target.value }))}
                              placeholder="reviewer note (optional)"
                              className="w-40 rounded-lg border border-white/15 bg-[#101d34] px-2 py-1 text-[10px] text-[#d6e6ff]"
                            />
                            {canPromote ? (
                              <div className="mt-1 flex items-center gap-1">
                                <input
                                  value={confirmDraft[key] || ''}
                                  onChange={(e) => setConfirmDraft((prev) => ({ ...prev, [key]: e.target.value }))}
                                  placeholder="type PROMOTE"
                                  className="w-28 rounded-lg border border-red-400/30 bg-[#1a0f10] px-2 py-1 text-[10px] text-red-200"
                                />
                                <button
                                  type="button"
                                  disabled={Boolean(busyKey)}
                                  onClick={() => row.decision && promote(row.decision.id, key)}
                                  className="rounded-lg border border-red-400/50 bg-red-500/10 px-2 py-1 text-[11px] text-red-200 disabled:opacity-50"
                                >
                                  {busyKey === key ? 'Promoting...' : 'Promote'}
                                </button>
                              </div>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        )
      ) : holdingsRows.length === 0 ? (
        <EmptyState message="No out-of-band holdings flagged for this AMC/month." />
      ) : (
        <Panel>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="sticky top-0 bg-[#0d172a] text-[#95afd5]">
                <tr>
                  <th className="px-2 py-2 text-left">Scheme</th>
                  <th className="px-2 py-2 text-right">Total %AUM</th>
                  <th className="px-2 py-2 text-left">Band</th>
                  <th className="px-2 py-2 text-left">Status</th>
                  <th className="px-2 py-2 text-right">No ISIN</th>
                  <th className="px-2 py-2 text-left">Source</th>
                  <th className="px-2 py-2 text-left">Decision</th>
                  <th className="px-2 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {holdingsRows.map((row) => {
                  const key = `holdings:${row.scheme_key}`;
                  const canPromote = row.decision?.resolution === 'use_staged' && !row.decision.promoted_at;
                  return (
                    <tr key={row.scheme_key} className="border-t border-white/10 align-top">
                      <td className="px-2 py-2">
                        <div className="font-medium text-[#d6e6ff]">{row.raw_scheme_name || row.scheme_key}</div>
                        {row.also_staged_in_n_other_documents ? (
                          <div className="text-[10px] text-[#8ea6cb]">also in {row.also_staged_in_n_other_documents} other doc(s)</div>
                        ) : null}
                      </td>
                      <td className="px-2 py-2 text-right text-[#d6e6ff]">{row.total_percent_aum ?? '-'}</td>
                      <td className="px-2 py-2 text-[#b7c9e6]">
                        {row.expected_band[0]}-{row.expected_band[1]}
                      </td>
                      <td className="px-2 py-2 text-amber-300">{row.validation_statuses.join(', ') || '-'}</td>
                      <td className="px-2 py-2 text-right text-[#d6e6ff]">
                        {row.holding_rows_missing_isin}/{row.holding_row_count}
                      </td>
                      <td className="px-2 py-2">
                        {row.source_url ? (
                          <a href={row.source_url} target="_blank" rel="noreferrer" className="text-[#68a7ff] hover:underline">
                            PDF
                          </a>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="px-2 py-2">
                        <DecisionBadge decision={row.decision} />
                      </td>
                      <td className="px-2 py-2">
                        <div className="flex flex-col items-end gap-1">
                          <div className="flex justify-end gap-1">
                            <button
                              type="button"
                              disabled={Boolean(busyKey)}
                              onClick={() => decideHoldings(row, 'use_staged')}
                              className="rounded-lg border border-emerald-400/40 bg-emerald-500/10 px-2 py-1 text-[11px] text-emerald-200 disabled:opacity-50"
                            >
                              Accept staged
                            </button>
                            <button
                              type="button"
                              disabled={Boolean(busyKey)}
                              onClick={() => decideHoldings(row, 'exclude')}
                              className="rounded-lg border border-slate-400/35 bg-slate-500/10 px-2 py-1 text-[11px] text-slate-200 disabled:opacity-50"
                            >
                              Exclude
                            </button>
                          </div>
                          <input
                            value={noteDraft[key] || ''}
                            onChange={(e) => setNoteDraft((prev) => ({ ...prev, [key]: e.target.value }))}
                            placeholder="reviewer note (optional)"
                            className="w-40 rounded-lg border border-white/15 bg-[#101d34] px-2 py-1 text-[10px] text-[#d6e6ff]"
                          />
                          {canPromote ? (
                            <div className="mt-1 flex items-center gap-1">
                              <input
                                value={confirmDraft[key] || ''}
                                onChange={(e) => setConfirmDraft((prev) => ({ ...prev, [key]: e.target.value }))}
                                placeholder="type PROMOTE"
                                className="w-28 rounded-lg border border-red-400/30 bg-[#1a0f10] px-2 py-1 text-[10px] text-red-200"
                              />
                              <button
                                type="button"
                                disabled={Boolean(busyKey)}
                                onClick={() => row.decision && promote(row.decision.id, key)}
                                className="rounded-lg border border-red-400/50 bg-red-500/10 px-2 py-1 text-[11px] text-red-200 disabled:opacity-50"
                              >
                                {busyKey === key ? 'Promoting...' : 'Promote'}
                              </button>
                            </div>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[11px] text-[#8ea6cb]">
            Promoting a holdings decision promotes the entire source document&apos;s <code>holdings</code> scope (all
            currently-valid schemes in it), not just this one row -- matching how the existing manual promotion
            workflow already scopes holdings promotion.
          </p>
        </Panel>
      )}
    </div>
  );
}
