'use client';

import { useEffect, useState } from 'react';
import { adminFetch } from '@/lib/admin/client';
import { EmptyState, ErrorState, LoadingState, Panel } from '@/components/admin/AdminUi';

type BucketRow = { [key: string]: string | number };
type Payload = {
  source_table: string;
  token_mode: 'actual' | 'proxy';
  todo_notes: string[];
  summary: {
    requests_today: number;
    requests_month: number;
    tokens_today: number;
    tokens_month: number;
    failed_calls_today: number;
  };
  requests_over_time: BucketRow[];
  usage_by_provider: BucketRow[];
  usage_by_model: BucketRow[];
  usage_by_feature: BucketRow[];
  top_users_by_tokens_month: BucketRow[];
};

function renderSimpleTable(rows: BucketRow[], keyName: string, title: string) {
  return (
    <Panel>
      <h3 className="text-sm font-semibold">{title}</h3>
      {!rows.length ? (
        <p className="mt-2 text-xs text-[#97afd2]">No data.</p>
      ) : (
        <div className="mt-2 overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="text-[#95afd5]">
              <tr>
                <th className="px-2 py-1.5 text-left">{keyName}</th>
                <th className="px-2 py-1.5 text-right">Requests</th>
                <th className="px-2 py-1.5 text-right">Tokens</th>
                <th className="px-2 py-1.5 text-right">Failed</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${title}-${index}`} className="border-t border-white/10">
                  <td className="px-2 py-1.5">{String(row[keyName] || '-')}</td>
                  <td className="px-2 py-1.5 text-right">{Number(row.requests || 0)}</td>
                  <td className="px-2 py-1.5 text-right">{Number(row.tokens || 0)}</td>
                  <td className="px-2 py-1.5 text-right">{Number(row.failed || 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

export default function AdminAiUsagePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Payload | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    const res = await adminFetch('/api/admin/ai-usage');
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(String((payload as { error?: string }).error || 'Failed to load AI usage'));
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
  if (!data) return <EmptyState message="No AI usage data available." />;

  return (
    <div className="space-y-4">
      <Panel>
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs text-[#97afd2]">Source: {data.source_table}</p>
            <p className="text-xs text-[#97afd2]">Token mode: {data.token_mode}</p>
          </div>
          <button type="button" onClick={load} className="rounded-lg border border-white/15 bg-[#142441] px-3 py-1.5 text-xs text-[#c7daf5]">
            Refresh
          </button>
        </div>
        {data.todo_notes?.length ? (
          <div className="mt-2 space-y-1">
            {data.todo_notes.map((note, index) => (
              <p key={index} className="text-[11px] text-[#8ea6cb]">{note}</p>
            ))}
          </div>
        ) : null}
      </Panel>

      <div className="grid gap-3 md:grid-cols-5">
        <Panel><p className="text-xs text-[#97afd2]">Requests today</p><p className="mt-1 text-xl font-semibold">{data.summary.requests_today}</p></Panel>
        <Panel><p className="text-xs text-[#97afd2]">Requests month</p><p className="mt-1 text-xl font-semibold">{data.summary.requests_month}</p></Panel>
        <Panel><p className="text-xs text-[#97afd2]">Tokens today</p><p className="mt-1 text-xl font-semibold">{data.summary.tokens_today}</p></Panel>
        <Panel><p className="text-xs text-[#97afd2]">Tokens month</p><p className="mt-1 text-xl font-semibold">{data.summary.tokens_month}</p></Panel>
        <Panel><p className="text-xs text-[#97afd2]">Failed today</p><p className="mt-1 text-xl font-semibold">{data.summary.failed_calls_today}</p></Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        {renderSimpleTable(data.requests_over_time || [], 'day', 'Requests Over Time')}
        {renderSimpleTable(data.usage_by_provider || [], 'provider', 'Provider Breakdown')}
        {renderSimpleTable(data.usage_by_model || [], 'model', 'Model Breakdown')}
        {renderSimpleTable(data.usage_by_feature || [], 'feature', 'Feature Breakdown')}
      </div>

      {renderSimpleTable(data.top_users_by_tokens_month || [], 'user_id', 'Top 20 Users by Tokens (Month)')}
    </div>
  );
}
