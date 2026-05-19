'use client';

import { useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/admin/client';
import { EmptyState, ErrorState, LoadingState, Panel, statusBadgeClass } from '@/components/admin/AdminUi';

type UserRow = {
  email: string | null;
  user_id: string;
  role: string;
  tier: string;
  created_at: string | null;
  last_active_at: string | null;
  requests_today: number;
  monthly_tokens: number;
  subscription_status: string | null;
};

const FILTERS = ['all', 'free', 'pro', 'admin', 'tester'] as const;

function fmt(value: string | null) {
  if (!value) return '-';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return '-';
  return dt.toLocaleString('en-IN', { hour12: false });
}

export default function AdminUsersPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<UserRow[]>([]);

  const load = useCallback(async (nextFilter = filter) => {
    setLoading(true);
    setError(null);
    const res = await adminFetch(`/api/admin/users?filter=${encodeURIComponent(nextFilter)}`);
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(String((payload as { error?: string }).error || 'Failed to load users'));
      setRows([]);
      setLoading(false);
      return;
    }
    setRows(Array.isArray((payload as { users?: UserRow[] }).users) ? (payload as { users: UserRow[] }).users : []);
    setLoading(false);
  }, [filter]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load(filter);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [filter, load]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!rows.length) return <EmptyState message="No users found for this filter." />;

  return (
    <div className="space-y-4">
      <Panel>
        <div className="flex flex-wrap items-center gap-2">
          {FILTERS.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setFilter(option)}
              className={`rounded-full border px-3 py-1 text-xs ${filter === option ? 'border-[#68a7ff] bg-[#17325a] text-white' : 'border-white/15 text-[#b7c9e6]'}`}
            >
              {option}
            </button>
          ))}
          <button type="button" onClick={() => load(filter)} className="ml-auto rounded-lg border border-white/15 bg-[#142441] px-3 py-1.5 text-xs text-[#c7daf5]">
            Refresh
          </button>
        </div>
      </Panel>

      <Panel>
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="sticky top-0 bg-[#0d172a] text-[#95afd5]">
              <tr>
                <th className="px-2 py-2 text-left">Email</th>
                <th className="px-2 py-2 text-left">User ID</th>
                <th className="px-2 py-2 text-left">Role</th>
                <th className="px-2 py-2 text-left">Tier</th>
                <th className="px-2 py-2 text-left">Created</th>
                <th className="px-2 py-2 text-left">Last Active</th>
                <th className="px-2 py-2 text-right">Requests Today</th>
                <th className="px-2 py-2 text-right">Monthly Tokens</th>
                <th className="px-2 py-2 text-left">Subscription</th>
                <th className="px-2 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.user_id} className="border-t border-white/10">
                  <td className="px-2 py-2">{row.email || '-'}</td>
                  <td className="px-2 py-2 text-[#9db4d6]">{row.user_id}</td>
                  <td className="px-2 py-2"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass(row.role)}`}>{row.role}</span></td>
                  <td className="px-2 py-2"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass(row.tier === 'pro' ? 'active' : 'planned')}`}>{row.tier}</span></td>
                  <td className="px-2 py-2">{fmt(row.created_at)}</td>
                  <td className="px-2 py-2">{fmt(row.last_active_at)}</td>
                  <td className="px-2 py-2 text-right">{row.requests_today}</td>
                  <td className="px-2 py-2 text-right">{row.monthly_tokens}</td>
                  <td className="px-2 py-2">{row.subscription_status || '-'}</td>
                  <td className="px-2 py-2">
                    <div className="flex flex-wrap gap-1">
                      <button type="button" disabled className="rounded border border-white/10 px-2 py-0.5 text-[10px] text-[#8ea6cb]">View</button>
                      <button type="button" disabled className="rounded border border-white/10 px-2 py-0.5 text-[10px] text-[#8ea6cb]">Role</button>
                      <button type="button" disabled className="rounded border border-white/10 px-2 py-0.5 text-[10px] text-[#8ea6cb]">Tier</button>
                      <button type="button" disabled className="rounded border border-white/10 px-2 py-0.5 text-[10px] text-[#8ea6cb]">Reset</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[11px] text-[#8ea6cb]">Phase 1 is read-only. Role/tier/reset actions are TODO and intentionally disabled.</p>
      </Panel>
    </div>
  );
}
