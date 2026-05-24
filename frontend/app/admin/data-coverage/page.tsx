'use client';

import { useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/admin/client';
import { EmptyState, ErrorState, LoadingState, Panel, statusBadgeClass } from '@/components/admin/AdminUi';

type CoverageRow = {
  amc: string;
  total_funds: number;
  funds_with_nav: number;
  funds_with_aum: number;
  funds_with_ter: number;
  funds_with_holdings: number;
  funds_with_sector_allocation: number;
  funds_with_asset_allocation: number;
  funds_with_ratios: number;
  parser_status: string;
  skipped_docs: number;
  freshness_status: string;
  coverage_percentage: number;
  status: string;
  missing_ter_count: number;
};

type NeedsReviewEntry = {
  id: string;
  amc: string;
  source_document_type: string;
  parse_status: string;
  source_url: string;
  validation_issues: string[];
  parsed_at: string | null;
  downloaded_at: string | null;
  latest_at: string | null;
};

const FILTERS = ['all', 'fully-covered', 'partial', 'stale', 'missing-ter', 'missing-holdings', 'missing-ratios', 'parser-failing'] as const;

type Payload = {
  rows: CoverageRow[];
  needs_review_entries: NeedsReviewEntry[];
  pipeline_focus: { active_current: string[]; note: string };
  todo_notes: string[];
};

export default function AdminDataCoveragePage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Payload | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const load = useCallback(async (nextFilter = filter) => {
    setLoading(true);
    setError(null);
    const res = await adminFetch(`/api/admin/data-coverage?filter=${encodeURIComponent(nextFilter)}`);
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(String((payload as { error?: string }).error || 'Failed to load data coverage'));
      setData(null);
      setLoading(false);
      return;
    }
    setData(payload as Payload);
    setLoading(false);
  }, [filter]);

  const handleDocumentAction = useCallback(async (documentId: string, action: 'reparse' | 'skip') => {
    setActionId(`${action}:${documentId}`);
    setActionMessage(null);
    const res = await adminFetch(`/api/admin/data-coverage/documents/${encodeURIComponent(documentId)}/${action}`, {
      method: 'POST',
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      setActionMessage(String((payload as { error?: string; detail?: string }).error || (payload as { detail?: string }).detail || 'Action failed'));
      setActionId(null);
      return;
    }
    setActionMessage(action === 'reparse' ? 'Reparse queued.' : 'Document skipped.');
    await load(filter);
    setActionId(null);
  }, [filter, load]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load(filter);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [filter, load]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data || (!data.rows?.length && !data.needs_review_entries?.length)) return <EmptyState message="No coverage rows available." />;

  return (
    <div className="space-y-4">
      <Panel>
        <div className="flex flex-wrap gap-2">
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
        <p className="mt-2 text-xs text-[#8ea6cb]">{data.pipeline_focus?.note}</p>
      </Panel>

      <Panel>
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="sticky top-0 bg-[#0d172a] text-[#95afd5]">
              <tr>
                <th className="px-2 py-2 text-left">AMC</th>
                <th className="px-2 py-2 text-right">Total</th>
                <th className="px-2 py-2 text-right">NAV</th>
                <th className="px-2 py-2 text-right">AUM</th>
                <th className="px-2 py-2 text-right">TER</th>
                <th className="px-2 py-2 text-right">Holdings</th>
                <th className="px-2 py-2 text-right">Sector</th>
                <th className="px-2 py-2 text-right">Ratios</th>
                <th className="px-2 py-2 text-right">Coverage %</th>
                <th className="px-2 py-2 text-left">Freshness</th>
                <th className="px-2 py-2 text-left">Parser</th>
                <th className="px-2 py-2 text-left">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row) => (
                <tr key={row.amc} className="border-t border-white/10">
                  <td className="px-2 py-2 font-medium">{row.amc}</td>
                  <td className="px-2 py-2 text-right">{row.total_funds}</td>
                  <td className="px-2 py-2 text-right">{row.funds_with_nav}</td>
                  <td className="px-2 py-2 text-right">{row.funds_with_aum}</td>
                  <td className="px-2 py-2 text-right">{row.funds_with_ter}</td>
                  <td className="px-2 py-2 text-right">{row.funds_with_holdings}</td>
                  <td className="px-2 py-2 text-right">{row.funds_with_sector_allocation}</td>
                  <td className="px-2 py-2 text-right">{row.funds_with_ratios}</td>
                  <td className="px-2 py-2 text-right">{row.coverage_percentage}%</td>
                  <td className="px-2 py-2"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass(row.freshness_status)}`}>{row.freshness_status}</span></td>
                  <td className="px-2 py-2"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass(row.parser_status)}`}>{row.parser_status}</span></td>
                  <td className="px-2 py-2"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass(row.status)}`}>{row.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[#d6e6ff]">Parser Action Entries</h3>
          <span className="rounded-full border border-amber-400/40 bg-amber-500/10 px-2 py-0.5 text-[11px] text-amber-300">
            {data.needs_review_entries?.length || 0}
          </span>
        </div>
        {actionMessage ? <p className="mb-2 text-xs text-[#9fb7dc]">{actionMessage}</p> : null}
        {!data.needs_review_entries?.length ? (
          <p className="text-xs text-[#8ea6cb]">No documents currently marked as needs_review or failed.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="sticky top-0 bg-[#0d172a] text-[#95afd5]">
                <tr>
                  <th className="px-2 py-2 text-left">AMC</th>
                  <th className="px-2 py-2 text-left">Document Type</th>
                  <th className="px-2 py-2 text-left">Status</th>
                  <th className="px-2 py-2 text-left">Issues</th>
                  <th className="px-2 py-2 text-left">Latest</th>
                  <th className="px-2 py-2 text-left">Document</th>
                  <th className="px-2 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.needs_review_entries.map((entry) => (
                  <tr key={entry.id} className="border-t border-white/10">
                    <td className="px-2 py-2 font-medium">{entry.amc}</td>
                    <td className="px-2 py-2">{entry.source_document_type || '-'}</td>
                    <td className="px-2 py-2"><span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass(entry.parse_status)}`}>{entry.parse_status || '-'}</span></td>
                    <td className="px-2 py-2">
                      <div className="flex flex-wrap gap-1">
                        {(entry.validation_issues || []).length ? (
                          entry.validation_issues.map((issue, idx) => (
                            <span key={`${entry.id}-${idx}`} className="rounded-full border border-amber-400/35 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-300">
                              {issue}
                            </span>
                          ))
                        ) : (
                          <span className="text-[#8ea6cb]">-</span>
                        )}
                      </div>
                    </td>
                    <td className="px-2 py-2 text-[#b7c9e6]">{entry.latest_at ? new Date(entry.latest_at).toLocaleString() : '-'}</td>
                    <td className="px-2 py-2">
                      {entry.source_url ? (
                        <a href={entry.source_url} target="_blank" rel="noreferrer" className="text-[#68a7ff] hover:underline">
                          Open
                        </a>
                      ) : (
                        <span className="text-[#8ea6cb]">-</span>
                      )}
                    </td>
                    <td className="px-2 py-2">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          disabled={Boolean(actionId)}
                          onClick={() => handleDocumentAction(entry.id, 'reparse')}
                          className="rounded-lg border border-[#68a7ff]/40 bg-[#17325a] px-2 py-1 text-[11px] text-[#d6e6ff] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {actionId === `reparse:${entry.id}` ? 'Queuing...' : 'Reparse'}
                        </button>
                        <button
                          type="button"
                          disabled={Boolean(actionId)}
                          onClick={() => handleDocumentAction(entry.id, 'skip')}
                          className="rounded-lg border border-emerald-400/40 bg-emerald-500/10 px-2 py-1 text-[11px] text-emerald-200 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {actionId === `skip:${entry.id}` ? 'Skipping...' : 'Skip'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {data.todo_notes?.length ? (
        <Panel>
          {data.todo_notes.map((note, index) => (
            <p key={index} className="text-[11px] text-[#8ea6cb]">{note}</p>
          ))}
        </Panel>
      ) : null}
    </div>
  );
}
