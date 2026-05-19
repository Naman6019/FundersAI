'use client';

import { useEffect, useState } from 'react';
import { adminFetch } from '@/lib/admin/client';
import { EmptyState, ErrorState, LoadingState, Panel, statusBadgeClass } from '@/components/admin/AdminUi';

type OverviewPayload = {
  cards: {
    users: Record<string, number>;
    ai_usage: Record<string, number | string>;
    data: Record<string, number>;
    sync_health: Record<string, number | string | null>;
  };
  critical_alerts: Array<{ id: string; label: string; status: string; detail: string }>;
};

export default function AdminOverviewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<OverviewPayload | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    const res = await adminFetch('/api/admin/overview');
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(String((payload as { error?: string }).error || 'Failed to load overview'));
      setData(null);
      setLoading(false);
      return;
    }
    setData(payload as OverviewPayload);
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
  if (!data) return <EmptyState message="No overview data available." />;

  const users = data.cards.users || {};
  const ai = data.cards.ai_usage || {};
  const fund = data.cards.data || {};
  const sync = data.cards.sync_health || {};

  return (
    <div className="space-y-4">
      <Panel>
        <div className="flex items-center justify-end">
          <button type="button" onClick={load} className="rounded-lg border border-white/15 bg-[#142441] px-3 py-1.5 text-xs text-[#c7daf5]">
            Refresh
          </button>
        </div>
      </Panel>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Panel><p className="text-xs text-[#97afd2]">Total users</p><p className="mt-1 text-2xl font-semibold">{users.total_users || 0}</p></Panel>
        <Panel><p className="text-xs text-[#97afd2]">AI requests today</p><p className="mt-1 text-2xl font-semibold">{ai.ai_requests_today || 0}</p></Panel>
        <Panel><p className="text-xs text-[#97afd2]">Funds covered</p><p className="mt-1 text-2xl font-semibold">{fund.total_funds || 0}</p></Panel>
        <Panel><p className="text-xs text-[#97afd2]">Latest NAV sync</p><p className={`mt-1 inline-flex rounded-full border px-2 py-0.5 text-xs ${statusBadgeClass(String(sync.latest_nav_sync_status || 'unknown'))}`}>{String(sync.latest_nav_sync_status || 'unknown')}</p></Panel>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <Panel>
          <h3 className="text-sm font-semibold">Users</h3>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
            <p>Active today: <span className="font-semibold">{users.active_users_today || 0}</span></p>
            <p>Free: <span className="font-semibold">{users.free_users || 0}</span></p>
            <p>Pro: <span className="font-semibold">{users.pro_users || 0}</span></p>
            <p>Admin/Tester: <span className="font-semibold">{users.admin_tester_users || 0}</span></p>
          </div>
        </Panel>
        <Panel>
          <h3 className="text-sm font-semibold">AI Usage</h3>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
            <p>Requests month: <span className="font-semibold">{ai.ai_requests_month || 0}</span></p>
            <p>Tokens today: <span className="font-semibold">{ai.tokens_today || 0}</span></p>
            <p>Tokens month: <span className="font-semibold">{ai.tokens_month || 0}</span></p>
            <p>Failed today: <span className="font-semibold">{ai.failed_ai_calls_today || 0}</span></p>
          </div>
          {ai.token_note ? <p className="mt-2 text-[11px] text-[#8ea6cb]">{String(ai.token_note)}</p> : null}
        </Panel>
      </div>

      <Panel>
        <h3 className="text-sm font-semibold">Critical Alerts</h3>
        {!data.critical_alerts?.length ? (
          <p className="mt-2 text-xs text-[#9db4d6]">No critical alerts.</p>
        ) : (
          <div className="mt-2 space-y-2">
            {data.critical_alerts.map((alert) => (
              <div key={alert.id} className="rounded-xl border border-white/10 bg-[#101d34] px-3 py-2 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium">{alert.label}</p>
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] ${statusBadgeClass(alert.status)}`}>{alert.status}</span>
                </div>
                <p className="mt-1 text-[#9db4d6]">{alert.detail}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
