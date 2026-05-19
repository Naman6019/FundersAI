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
  freshness_status: string;
  coverage_percentage: number;
  status: string;
  missing_ter_count: number;
};

const FILTERS = ['all', 'fully-covered', 'partial', 'stale', 'missing-ter', 'missing-holdings', 'missing-ratios', 'parser-failing'] as const;

type Payload = {
  rows: CoverageRow[];
  pipeline_focus: { active_current: string[]; note: string };
  todo_notes: string[];
};

export default function AdminDataCoveragePage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Payload | null>(null);

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

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load(filter);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [filter, load]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data || !data.rows?.length) return <EmptyState message="No coverage rows available." />;

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
