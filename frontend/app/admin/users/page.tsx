'use client';

import { Fragment, useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/admin/client';
import { EmptyState, ErrorState, LoadingState, Panel, statusBadgeClass } from '@/components/admin/AdminUi';

type UserRow = {
  email: string | null;
  user_id: string;
  role: string;
  tier: string;
  created_at: string | null;
  last_active_at: string | null;
  last_sign_in_at: string | null;
  requests_today: number;
  monthly_tokens: number;
  subscription_status: string | null;
  provider_subscription_id: string | null;
  provider_plan_id: string | null;
  subscription_current_end: string | null;
};

type UsageDay = { day: string; requests: number; tokens: number; failed: number };

type FeedbackRow = {
  id: string;
  feedback_type: string;
  rating: number;
  comment: string | null;
  page_path: string | null;
  response_excerpt: string | null;
  created_at: string;
};

type UserDetail = {
  usage_summary: { total_requests: number; total_tokens: number; total_failed: number };
  usage_by_day: UsageDay[];
  feedback: FeedbackRow[];
  feedback_count: number;
};

const FILTERS = ['all', 'free', 'pro', 'ultra', 'admin', 'tester'] as const;

function fmt(value: string | null) {
  if (!value) return '-';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return '-';
  return dt.toLocaleString('en-IN', { hour12: false });
}

function DetailPanel({ detail, loading, error }: { detail: UserDetail | null; loading: boolean; error: string | null }) {
  if (loading) return <p className="p-3 text-xs text-[#9eb4d6]">Loading 90-day usage and feedback...</p>;
  if (error) return <p className="p-3 text-xs text-red-200">{error}</p>;
  if (!detail) return null;

  const maxRequests = Math.max(1, ...detail.usage_by_day.map((d) => d.requests));

  return (
    <div className="grid gap-4 p-3 md:grid-cols-2">
      <div>
        <h4 className="mb-2 text-xs font-semibold text-[#d6e6ff]">
          Usage, last 90 days ({detail.usage_summary.total_requests} requests, {detail.usage_summary.total_tokens.toLocaleString()} tokens,{' '}
          {detail.usage_summary.total_failed} failed)
        </h4>
        {detail.usage_by_day.length === 0 ? (
          <p className="text-[11px] text-[#8ea6cb]">No AI usage recorded in this window.</p>
        ) : (
          <div className="flex h-20 items-end gap-0.5">
            {detail.usage_by_day.map((d) => (
              <div
                key={d.day}
                title={`${d.day}: ${d.requests} requests, ${d.tokens} tokens, ${d.failed} failed`}
                className="flex-1 rounded-t bg-[#68a7ff]/50 hover:bg-[#68a7ff]"
                style={{ height: `${Math.max(4, (d.requests / maxRequests) * 100)}%` }}
              />
            ))}
          </div>
        )}
      </div>
      <div>
        <h4 className="mb-2 text-xs font-semibold text-[#d6e6ff]">Feedback submitted ({detail.feedback_count})</h4>
        {detail.feedback.length === 0 ? (
          <p className="text-[11px] text-[#8ea6cb]">No feedback submitted.</p>
        ) : (
          <div className="max-h-40 space-y-2 overflow-y-auto">
            {detail.feedback.map((f) => (
              <div key={f.id} className="rounded-lg border border-white/10 bg-[#101d34] p-2 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] ${statusBadgeClass(f.rating >= 4 ? 'success' : f.rating <= 2 ? 'error' : 'warning')}`}>
                    {f.feedback_type} · {f.rating}/5
                  </span>
                  <span className="text-[#8ea6cb]">{fmt(f.created_at)}</span>
                </div>
                {f.comment ? <p className="mt-1 text-[#b7c9e6]">{f.comment}</p> : null}
                {f.page_path ? <p className="mt-1 text-[10px] text-[#8ea6cb]">{f.page_path}</p> : null}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminUsersPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<UserRow[]>([]);
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null);
  const [detailCache, setDetailCache] = useState<Record<string, UserDetail>>({});
  const [detailLoading, setDetailLoading] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

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

  const toggleExpand = useCallback(async (userId: string) => {
    if (expandedUserId === userId) {
      setExpandedUserId(null);
      return;
    }
    setExpandedUserId(userId);
    if (detailCache[userId]) return;
    setDetailLoading(userId);
    setDetailError(null);
    const res = await adminFetch(`/api/admin/users/${encodeURIComponent(userId)}/detail`);
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      setDetailError(String((payload as { error?: string }).error || 'Failed to load user detail'));
      setDetailLoading(null);
      return;
    }
    setDetailCache((prev) => ({ ...prev, [userId]: payload as UserDetail }));
    setDetailLoading(null);
  }, [expandedUserId, detailCache]);

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
        <p className="mt-2 text-xs text-[#8ea6cb]">Click a row (or &quot;View&quot;) to expand 90-day usage history and submitted feedback for that user.</p>
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
                <th className="px-2 py-2 text-left">Last Login</th>
                <th className="px-2 py-2 text-right">Requests Today</th>
                <th className="px-2 py-2 text-right">Monthly Tokens</th>
                <th className="px-2 py-2 text-left">Subscription</th>
                <th className="px-2 py-2 text-left">Razorpay</th>
                <th className="px-2 py-2 text-left">Period End</th>
                <th className="px-2 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <Fragment key={row.user_id}>
                  <tr
                    onClick={() => toggleExpand(row.user_id)}
                    className={`cursor-pointer border-t border-white/10 hover:bg-white/5 ${expandedUserId === row.user_id ? 'bg-white/5' : ''}`}
                  >
                    <td className="px-2 py-2">{row.email || '-'}</td>
                    <td className="px-2 py-2 text-[#9db4d6]">{row.user_id}</td>
                    <td className="px-2 py-2"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass(row.role)}`}>{row.role}</span></td>
                    <td className="px-2 py-2"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass(row.tier === 'pro' || row.tier === 'ultra' ? 'active' : 'planned')}`}>{row.tier}</span></td>
                    <td className="px-2 py-2">{fmt(row.created_at)}</td>
                    <td className="px-2 py-2">{row.last_sign_in_at ? fmt(row.last_sign_in_at) : <span className="text-[#8ea6cb]">Never</span>}</td>
                    <td className="px-2 py-2 text-right">{row.requests_today}</td>
                    <td className="px-2 py-2 text-right">{row.monthly_tokens}</td>
                    <td className="px-2 py-2">{row.subscription_status || '-'}</td>
                    <td className="px-2 py-2 text-[#9db4d6]">{row.provider_subscription_id || '-'}</td>
                    <td className="px-2 py-2">{fmt(row.subscription_current_end)}</td>
                    <td className="px-2 py-2">
                      <div className="flex flex-wrap gap-1">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleExpand(row.user_id);
                          }}
                          className="rounded border border-[#68a7ff]/40 bg-[#17325a] px-2 py-0.5 text-[10px] text-[#d6e6ff]"
                        >
                          {expandedUserId === row.user_id ? 'Hide' : 'View'}
                        </button>
                        <button type="button" disabled className="rounded border border-white/10 px-2 py-0.5 text-[10px] text-[#8ea6cb]">Role</button>
                        <button type="button" disabled className="rounded border border-white/10 px-2 py-0.5 text-[10px] text-[#8ea6cb]">Tier</button>
                        <button type="button" disabled className="rounded border border-white/10 px-2 py-0.5 text-[10px] text-[#8ea6cb]">Reset</button>
                      </div>
                    </td>
                  </tr>
                  {expandedUserId === row.user_id ? (
                    <tr className="border-t border-white/5 bg-[#0b1626]">
                      <td colSpan={12}>
                        <DetailPanel
                          detail={detailCache[row.user_id] || null}
                          loading={detailLoading === row.user_id}
                          error={detailError}
                        />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[11px] text-[#8ea6cb]">Phase 1 is read-only. Role/tier/reset actions are TODO and intentionally disabled.</p>
      </Panel>
    </div>
  );
}
