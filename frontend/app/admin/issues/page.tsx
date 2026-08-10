'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/admin/client';
import { EmptyState, ErrorState, LoadingState, Panel, statusBadgeClass } from '@/components/admin/AdminUi';

type DataQualityIssue = {
  id: string;
  symbol: string | null;
  table_name: string | null;
  field_name: string | null;
  issue_type: string | null;
  issue_message: string | null;
  source: string | null;
  detected_at: string | null;
};

type WorkflowRun = {
  provider: string | null;
  job_name: string | null;
  status: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_summary: string | null;
};

type OpsOverview = {
  status: string;
  checked_at: string;
  workflow_summary: { recent_run_count: number; status_counts: Record<string, number>; successes_24h: number; failures_24h: number };
  workflow_runs: WorkflowRun[];
  data_quality: {
    recent_issues: DataQualityIssue[];
    issue_count_24h: number;
    issue_count_7d: number;
    mf_failed_documents: number;
    mf_pending_review: number;
  };
};

type PendingPromotionCount = {
  status: string;
  total_pending: number;
  actionable_pending: number;
  pending_by_amc: { amc_code: string; use_staged: number; use_live: number; exclude: number }[];
};

function fmt(value: string | null) {
  if (!value) return '-';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return '-';
  return dt.toLocaleString('en-IN', { hour12: false });
}

function Card({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-[#101d34] px-4 py-3">
      <p className="text-[11px] text-[#8ea6cb]">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${tone || 'text-[#d6e6ff]'}`}>{value}</p>
    </div>
  );
}

export default function AdminIssuesPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ops, setOps] = useState<OpsOverview | null>(null);
  const [pending, setPending] = useState<PendingPromotionCount | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [opsRes, pendingRes] = await Promise.all([
      adminFetch('/api/admin/ops-overview'),
      adminFetch('/api/admin/promotion-review/pending-count'),
    ]);
    const opsPayload = await opsRes.json().catch(() => ({}));
    const pendingPayload = await pendingRes.json().catch(() => ({}));
    if (!opsRes.ok) {
      setError(String((opsPayload as { error?: string }).error || 'Failed to load ops overview'));
      setLoading(false);
      return;
    }
    setOps(opsPayload as OpsOverview);
    setPending(pendingRes.ok ? (pendingPayload as PendingPromotionCount) : null);
    setLoading(false);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!ops) return <EmptyState message="No operational data available." />;

  const failedRuns = ops.workflow_runs.filter((run) =>
    ['failed', 'error', 'partial_failed', 'timeout', 'timed_out'].includes(String(run.status || '').toLowerCase())
  );

  return (
    <div className="space-y-4">
      <Panel>
        <div className="flex items-center justify-between">
          <p className="text-xs text-[#8ea6cb]">
            Cross-cutting triage view. Checked {fmt(ops.checked_at)}. Each section links to its own detail page for
            the actual actions (reparse/resolve/skip, promote review decisions).
          </p>
          <button type="button" onClick={() => load()} className="rounded-lg border border-white/15 bg-[#142441] px-3 py-1.5 text-xs text-[#c7daf5]">
            Refresh
          </button>
        </div>
      </Panel>

      <Panel>
        <h3 className="mb-3 text-sm font-semibold text-[#d6e6ff]">Data quality</h3>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Card label="Issues (24h)" value={ops.data_quality.issue_count_24h} tone={ops.data_quality.issue_count_24h > 0 ? 'text-amber-300' : undefined} />
          <Card label="Issues (7d)" value={ops.data_quality.issue_count_7d} />
          <Card label="MF failed documents" value={ops.data_quality.mf_failed_documents} tone={ops.data_quality.mf_failed_documents > 0 ? 'text-red-300' : undefined} />
          <Card label="MF pending review" value={ops.data_quality.mf_pending_review} />
        </div>
        {ops.data_quality.recent_issues.length ? (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="text-[#95afd5]">
                <tr>
                  <th className="px-2 py-1 text-left">Symbol</th>
                  <th className="px-2 py-1 text-left">Table.Field</th>
                  <th className="px-2 py-1 text-left">Type</th>
                  <th className="px-2 py-1 text-left">Message</th>
                  <th className="px-2 py-1 text-left">Detected</th>
                </tr>
              </thead>
              <tbody>
                {ops.data_quality.recent_issues.slice(0, 20).map((issue) => (
                  <tr key={issue.id} className="border-t border-white/10">
                    <td className="px-2 py-1">{issue.symbol || '-'}</td>
                    <td className="px-2 py-1 text-[#9db4d6]">{issue.table_name}.{issue.field_name}</td>
                    <td className="px-2 py-1"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass('warning')}`}>{issue.issue_type}</span></td>
                    <td className="px-2 py-1 text-[#b7c9e6]">{issue.issue_message}</td>
                    <td className="px-2 py-1">{fmt(issue.detected_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-3 text-[11px] text-[#8ea6cb]">No data quality issues recorded.</p>
        )}
        <p className="mt-3 text-[11px] text-[#8ea6cb]">
          Parser backlog and document-level actions live on <Link href="/admin/data-coverage" className="text-[#68a7ff] hover:underline">Data Coverage</Link>.
        </p>
      </Panel>

      <Panel>
        <h3 className="mb-3 text-sm font-semibold text-[#d6e6ff]">Provider run health</h3>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Card label="Runs (recent)" value={ops.workflow_summary.recent_run_count} />
          <Card label="Successes (24h)" value={ops.workflow_summary.successes_24h} tone="text-emerald-300" />
          <Card label="Failures (24h)" value={ops.workflow_summary.failures_24h} tone={ops.workflow_summary.failures_24h > 0 ? 'text-red-300' : undefined} />
          <Card label="Failed runs shown" value={failedRuns.length} />
        </div>
        {failedRuns.length ? (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="text-[#95afd5]">
                <tr>
                  <th className="px-2 py-1 text-left">Provider</th>
                  <th className="px-2 py-1 text-left">Job</th>
                  <th className="px-2 py-1 text-left">Status</th>
                  <th className="px-2 py-1 text-left">Started</th>
                  <th className="px-2 py-1 text-left">Error</th>
                </tr>
              </thead>
              <tbody>
                {failedRuns.slice(0, 20).map((run, idx) => (
                  <tr key={idx} className="border-t border-white/10">
                    <td className="px-2 py-1">{run.provider || '-'}</td>
                    <td className="px-2 py-1">{run.job_name || '-'}</td>
                    <td className="px-2 py-1"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass('failing')}`}>{run.status}</span></td>
                    <td className="px-2 py-1">{fmt(run.started_at)}</td>
                    <td className="px-2 py-1 text-[#b7c9e6]">{run.error_summary || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-3 text-[11px] text-[#8ea6cb]">No failed provider runs recently.</p>
        )}
      </Panel>

      <Panel>
        <h3 className="mb-3 text-sm font-semibold text-[#d6e6ff]">Pending promotion reviews</h3>
        {!pending || pending.total_pending === 0 ? (
          <p className="text-[11px] text-[#8ea6cb]">No reviewed decisions currently awaiting promotion.</p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Card label="Total pending" value={pending.total_pending} />
              <Card label="Ready to promote" value={pending.actionable_pending} tone="text-emerald-300" />
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-xs">
                <thead className="text-[#95afd5]">
                  <tr>
                    <th className="px-2 py-1 text-left">AMC</th>
                    <th className="px-2 py-1 text-right">Ready (use staged)</th>
                    <th className="px-2 py-1 text-right">Kept live</th>
                    <th className="px-2 py-1 text-right">Excluded</th>
                  </tr>
                </thead>
                <tbody>
                  {pending.pending_by_amc.map((row) => (
                    <tr key={row.amc_code} className="border-t border-white/10">
                      <td className="px-2 py-1">{row.amc_code}</td>
                      <td className="px-2 py-1 text-right text-emerald-300">{row.use_staged}</td>
                      <td className="px-2 py-1 text-right">{row.use_live}</td>
                      <td className="px-2 py-1 text-right">{row.exclude}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        <p className="mt-3 text-[11px] text-[#8ea6cb]">
          Review and promote from <Link href="/admin/promotion-review" className="text-[#68a7ff] hover:underline">Promotion Review</Link>.
        </p>
      </Panel>
    </div>
  );
}
