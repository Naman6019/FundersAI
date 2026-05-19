'use client';

import { FormEvent, useState } from 'react';
import { adminFetch } from '@/lib/admin/client';
import { EmptyState, ErrorState, Panel, statusBadgeClass } from '@/components/admin/AdminUi';

type Candidate = {
  rank: number;
  selected: boolean;
  scheme_code: string;
  scheme_name: string;
  amc_name: string;
  match_score: number;
  nav_history_points: number;
  first_nav_date: string | null;
  last_nav_date: string | null;
  supports: { '1Y': boolean; '3Y': boolean; '5Y': boolean };
  penalty_notes: string[];
};

type Payload = {
  input_query: string;
  normalized_query: string;
  selected_candidate: (Candidate & { resolver_confidence?: { label: string; score_gap_vs_next: number } }) | null;
  top_candidates: Candidate[];
  scoring_breakdown: { horizon: string; min_history_points: number; candidate_count: number };
};

const QUICK_CASES = [
  'ICICI Multi Asset',
  'ICICI Prudential Multi Asset Fund',
  'Parag Flexi Cap',
  'Parag Parikh Flexi Cap',
];

export default function AdminResolverDebugPage() {
  const [query, setQuery] = useState('ICICI Multi Asset');
  const [horizon, setHorizon] = useState<'1Y' | '3Y' | '5Y'>('3Y');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Payload | null>(null);

  const load = async (nextQuery = query, nextHorizon = horizon) => {
    if (!nextQuery.trim()) return;
    setLoading(true);
    setError(null);
    const res = await adminFetch(`/api/admin/resolver-debug?query=${encodeURIComponent(nextQuery)}&horizon=${encodeURIComponent(nextHorizon)}`);
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(String((payload as { error?: string }).error || 'Resolver debug failed'));
      setData(null);
      setLoading(false);
      return;
    }
    setData(payload as Payload);
    setLoading(false);
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await load(query, horizon);
  };

  return (
    <div className="space-y-4">
      <Panel>
        <form onSubmit={onSubmit} className="flex flex-col gap-3 md:flex-row md:items-end">
          <div className="flex-1">
            <label className="mb-1 block text-xs text-[#97afd2]">Search query</label>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="ICICI Multi Asset"
              className="w-full rounded-xl border border-white/15 bg-[#0f1b31] px-3 py-2 text-sm text-white outline-none focus:border-[#69a7ff]"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[#97afd2]">Range</label>
            <select
              value={horizon}
              onChange={(event) => setHorizon(event.target.value as '1Y' | '3Y' | '5Y')}
              className="rounded-xl border border-white/15 bg-[#0f1b31] px-3 py-2 text-sm text-white outline-none"
            >
              <option value="1Y">1Y</option>
              <option value="3Y">3Y</option>
              <option value="5Y">5Y</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl border border-white/15 bg-[#17325a] px-4 py-2 text-sm text-white disabled:opacity-60"
          >
            {loading ? 'Testing...' : 'Test Resolver'}
          </button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {QUICK_CASES.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => {
                setQuery(item);
                load(item, horizon);
              }}
              className="rounded-full border border-white/15 bg-[#0f1b31] px-3 py-1 text-xs text-[#c6d8f4]"
            >
              {item}
            </button>
          ))}
        </div>
      </Panel>

      {error ? <ErrorState message={error} /> : null}
      {!data && !error ? <EmptyState message="Run a resolver test to view candidate selection and scoring." /> : null}

      {data ? (
        <>
          <Panel>
            <h3 className="text-sm font-semibold">Selected Result</h3>
            {data.selected_candidate ? (
              <div className="mt-2 grid gap-2 text-xs md:grid-cols-2">
                <p>scheme_code: <span className="font-semibold">{data.selected_candidate.scheme_code}</span></p>
                <p>scheme_name: <span className="font-semibold">{data.selected_candidate.scheme_name}</span></p>
                <p>confidence: <span className="font-semibold">{data.selected_candidate.resolver_confidence?.label || 'n/a'}</span></p>
                <p>score: <span className="font-semibold">{data.selected_candidate.match_score}</span></p>
                <p>nav_history_points: <span className="font-semibold">{data.selected_candidate.nav_history_points}</span></p>
                <p>first_nav_date: <span className="font-semibold">{data.selected_candidate.first_nav_date || '-'}</span></p>
                <p>last_nav_date: <span className="font-semibold">{data.selected_candidate.last_nav_date || '-'}</span></p>
                <p>supports_1y: <span className="font-semibold">{String(data.selected_candidate.supports?.['1Y'] || false)}</span></p>
                <p>supports_3y: <span className="font-semibold">{String(data.selected_candidate.supports?.['3Y'] || false)}</span></p>
                <p>supports_5y: <span className="font-semibold">{String(data.selected_candidate.supports?.['5Y'] || false)}</span></p>
              </div>
            ) : (
              <p className="mt-2 text-xs text-[#97afd2]">No candidate selected.</p>
            )}
          </Panel>

          <Panel>
            <h3 className="text-sm font-semibold">Top Candidates</h3>
            <p className="mt-1 text-[11px] text-[#8ea6cb]">
              Query: {data.input_query} | normalized: {data.normalized_query} | min history points: {data.scoring_breakdown?.min_history_points}
            </p>
            {!data.top_candidates?.length ? (
              <p className="mt-2 text-xs text-[#97afd2]">No candidates found.</p>
            ) : (
              <div className="mt-2 overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead className="sticky top-0 bg-[#0d172a] text-[#95afd5]">
                    <tr>
                      <th className="px-2 py-2 text-right">Rank</th>
                      <th className="px-2 py-2 text-left">Selected</th>
                      <th className="px-2 py-2 text-left">Scheme Code</th>
                      <th className="px-2 py-2 text-left">Scheme Name</th>
                      <th className="px-2 py-2 text-left">AMC</th>
                      <th className="px-2 py-2 text-right">Score</th>
                      <th className="px-2 py-2 text-right">NAV Rows</th>
                      <th className="px-2 py-2 text-left">First NAV</th>
                      <th className="px-2 py-2 text-left">Last NAV</th>
                      <th className="px-2 py-2 text-left">Penalty Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.top_candidates.map((candidate) => (
                      <tr key={`${candidate.rank}-${candidate.scheme_code}`} className="border-t border-white/10">
                        <td className="px-2 py-2 text-right">{candidate.rank}</td>
                        <td className="px-2 py-2">
                          <span className={`rounded-full border px-2 py-0.5 ${statusBadgeClass(candidate.selected ? 'active' : 'planned')}`}>
                            {candidate.selected ? 'yes' : 'no'}
                          </span>
                        </td>
                        <td className="px-2 py-2">{candidate.scheme_code}</td>
                        <td className="px-2 py-2">{candidate.scheme_name}</td>
                        <td className="px-2 py-2">{candidate.amc_name}</td>
                        <td className="px-2 py-2 text-right">{candidate.match_score}</td>
                        <td className="px-2 py-2 text-right">{candidate.nav_history_points}</td>
                        <td className="px-2 py-2">{candidate.first_nav_date || '-'}</td>
                        <td className="px-2 py-2">{candidate.last_nav_date || '-'}</td>
                        <td className="px-2 py-2">{candidate.penalty_notes?.join(', ') || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </>
      ) : null}
    </div>
  );
}

