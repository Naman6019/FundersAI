'use client';

import { useEffect, useState } from 'react';
import { adminFetch } from '@/lib/admin/client';
import { EmptyState, ErrorState, LoadingState, Panel, statusBadgeClass } from '@/components/admin/AdminUi';

type RunRow = {
  id: string;
  provider: string;
  source: string;
  job_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  rows_processed: number;
  rows_inserted: number;
  rows_updated: number;
  rows_skipped: number;
  failed_schemes: number;
  error_summary: string | null;
};

type Payload = {
  latest_nav_sync: RunRow | null;
  latest_nav_date: string | null;
  recent_runs: RunRow[];
  alerts: Array<{ id: string; severity: 'warning' | 'error'; message: string }>;
  actions: { run_sync_now: { enabled: boolean; reason: string } };
};

function fmt(value: string | null) {
  if (!value) return '-';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return '-';
  return dt.toLocaleString('en-IN', { hour12: false });
}

export default function AdminNavSyncPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Payload | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    const res = await adminFetch('/api/admin/nav-sync');
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(String((payload as { error?: string }).error || 'Failed to load NAV sync monitor'));
      setData(null);
      setLoading(false);
      return;
    }
    setData(payload as Payload);
    setLoading(false);
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message="No NAV sync data available." />;

  return (
    <div className="space-y-4">
      <Panel>
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs text-[#97afd2]">Latest NAV date: {data.latest_nav_date || '-'}</p>
            <p className="text-xs text-[#97afd2]">Run sync now: {data.actions.run_sync_now.enabled ? 'enabled' : 'disabled'} ({data.actions.run_sync_now.reason})</p>
          </div>
          <button type="button" onClick={load} className="rounded-lg border border-white/15 bg-[#142441] px-3 py-1.5 text-xs text-[#c7daf5]">
            Refresh
          </button>
        </div>
      </Panel>

      <div className="grid gap-3 md:grid-cols-4">
        <Panel><p className="text-xs text-[#97afd2]">Latest Status</p><p className={`mt-1 inline-flex rounded-full border px-2 py-0.5 text-xs ${statusBadgeClass(data.latest_nav_sync?.status || 'unknown')}`}>{data.latest_nav_sync?.status || 'unknown'}</p></Panel>
        <Panel><p className="text-xs text-[#97afd2]">Rows Inserted</p><p className="mt-1 text-xl font-semibold">{data.latest_nav_sync?.rows_inserted || 0}</p></Panel>
        <Panel><p className="text-xs text-[#97afd2]">Rows Updated</p><p className="mt-1 text-xl font-semibold">{data.latest_nav_sync?.rows_updated || 0}</p></Panel>
        <Panel><p className="text-xs text-[#97afd2]">Failed Schemes</p><p className="mt-1 text-xl font-semibold">{data.latest_nav_sync?.failed_schemes || 0}</p></Panel>
      </div>

      <Panel>
        <h3 className="text-sm font-semibold">Alerts</h3>
        {!data.alerts.length ? (
          <p className="mt-2 text-xs text-[#97afd2]">No active alerts.</p>
        ) : (
          <div className="mt-2 space-y-2">
            {data.alerts.map((alert) => (
              <div key={alert.id} className="rounded-xl border border-white/10 bg-[#101d34] px-3 py-2 text-xs">
                <span className={`rounded-full border px-2 py-0.5 text-[10px] ${statusBadgeClass(alert.severity === 'error' ? 'error' : 'stale')}`}>{alert.severity}</span>
                <p className="mt-1 text-[#cfe1ff]">{alert.message}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel>
        <h3 className="text-sm font-semibold">Recent Provider Runs</h3>
        {!data.recent_runs.length ? (
          <p className="mt-2 text-xs text-[#97afd2]">No MF/nav provider runs found.</p>
        ) : (
          <div className="mt-2 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="sticky top-0 bg-[#0d172a] text-[#95afd5]">
                <tr>
                  <th className="px-2 py-2 text-left">Source</th>
                  <th className="px-2 py-2 text-left">Status</th>
                  <th className="px-2 py-2 text-left">Started</th>
                  <th className="px-2 py-2 text-left">Completed</th>
                  <th className="px-2 py-2 text-right">Duration</th>
                  <th className="px-2 py-2 text-right">Processed</th>
                  <th className="px-2 py-2 text-right">Failed</th>
                  <th className="px-2 py-2 text-left">Error</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_runs.map((run) => (
                  <tr key={run.id} className="border-t border-white/10">
                    <td className="px-2 py-2">{run.source}</td>
                    <td className="px-2 py-2"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass(run.status)}`}>{run.status}</span></td>
                    <td className="px-2 py-2">{fmt(run.started_at)}</td>
                    <td className="px-2 py-2">{fmt(run.completed_at)}</td>
                    <td className="px-2 py-2 text-right">{run.duration_seconds ?? '-'}</td>
                    <td className="px-2 py-2 text-right">{run.rows_processed}</td>
                    <td className="px-2 py-2 text-right">{run.failed_schemes}</td>
                    <td className="px-2 py-2">{run.error_summary || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
