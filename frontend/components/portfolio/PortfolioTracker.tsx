'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Database,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Trash2,
  WalletCards,
  X,
} from 'lucide-react';
import { supabaseBrowser } from '@/lib/supabaseBrowser';

type FreshnessStatus = 'fresh' | 'lagging' | 'stale' | 'partial' | 'missing';

type Position = {
  id: string;
  portfolio_id: string;
  scheme_code: number;
  units: number;
  current_value: number;
  position_source?: string | null;
  fund: {
    scheme_name: string | null;
    amc_name: string | null;
    category: string | null;
  };
  holdings_count: number;
  freshness: {
    status: FreshnessStatus;
    nav_status: string;
    holdings_status: string;
    nav_date: string | null;
    holdings_as_of_date: string | null;
    snapshot_last_updated: string | null;
    note: string;
  };
};

type Portfolio = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  positions: Position[];
  total_current_value: number;
  aggregate_overlap: {
    coverage_status: 'unavailable' | 'partial' | 'available';
    positions_with_holdings: number;
    positions_without_holdings: number;
    total_current_value: number;
    covered_current_value: number;
    uncovered_current_value: number;
    total_overlap_exposure: number;
    total_overlap_percent: number | null;
    covered_overlap_percent: number | null;
    common_holding_count: number;
    top_common_holdings: Array<{
      isin: string | null;
      name: string;
      sector: string | null;
      fund_count: number;
      portfolio_exposure: number | null;
      overlap_exposure: number | null;
    }>;
  };
  freshness: {
    status: FreshnessStatus;
    positions_with_nav: number;
    positions_with_holdings: number;
    positions_missing_data: number;
    latest_nav_date: string | null;
    latest_holdings_as_of_date: string | null;
  };
  research_boundary: string;
};

type ApiBody = Record<string, unknown>;

function formatInr(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Not available';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 4 }).format(value);
}

function formatDate(value: string | null | undefined): string {
  if (!value) return 'Not available';
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00+05:30`);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function statusClass(status: string): string {
  switch (status) {
    case 'fresh':
      return 'border-emerald-400/25 bg-emerald-400/10 text-emerald-200';
    case 'lagging':
    case 'partial':
      return 'border-amber-400/25 bg-amber-400/10 text-amber-100';
    case 'stale':
    case 'missing':
      return 'border-rose-400/25 bg-rose-400/10 text-rose-100';
    default:
      return 'border-white/10 bg-white/[0.04] text-slate-300';
  }
}

async function accessToken(): Promise<string | null> {
  const { data } = await supabaseBrowser.auth.getSession();
  return data.session?.access_token || null;
}

async function portfolioRequest(path: string, init: RequestInit = {}): Promise<{ response: Response; body: ApiBody }> {
  const token = await accessToken();
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers || {}),
    },
    cache: 'no-store',
  });
  const body = await response.json().catch(() => ({}));
  return { response, body };
}

function apiError(body: ApiBody, fallback: string): string {
  return typeof body.error === 'string' ? body.error : fallback;
}

export default function PortfolioTracker() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [portfolioName, setPortfolioName] = useState('My research portfolio');
  const [schemeCode, setSchemeCode] = useState('');
  const [units, setUnits] = useState('');
  const [currentValue, setCurrentValue] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editUnits, setEditUnits] = useState('');
  const [editCurrentValue, setEditCurrentValue] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPortfolio = useMemo(
    () => portfolios.find((portfolio) => portfolio.id === selectedId) || portfolios[0] || null,
    [portfolios, selectedId],
  );

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { response, body } = await portfolioRequest('/api/portfolio');
      if (!response.ok) throw new Error(apiError(body, 'Could not load portfolio data.'));
      const next = Array.isArray(body.portfolios) ? body.portfolios as Portfolio[] : [];
      setPortfolios(next);
      setSelectedId((current) => next.some((portfolio) => portfolio.id === current) ? current : next[0]?.id || '');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load portfolio data.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void refresh();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [refresh]);

  const createPortfolio = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      const { response, body } = await portfolioRequest('/api/portfolio', {
        method: 'POST',
        body: JSON.stringify({ name: portfolioName }),
      });
      if (!response.ok) throw new Error(apiError(body, 'Could not create portfolio.'));
      setPortfolioName('My research portfolio');
      await refresh();
      const createdPortfolio = body.portfolio as { id?: unknown } | undefined;
      if (typeof createdPortfolio?.id === 'string') setSelectedId(createdPortfolio.id);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not create portfolio.');
    } finally {
      setIsSaving(false);
    }
  };

  const addPosition = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedPortfolio) return;
    setIsSaving(true);
    setError(null);
    try {
      const { response, body } = await portfolioRequest(`/api/portfolio/${selectedPortfolio.id}/positions`, {
        method: 'POST',
        body: JSON.stringify({ scheme_code: schemeCode, units, current_value: currentValue }),
      });
      if (!response.ok) throw new Error(apiError(body, 'Could not add position.'));
      setSchemeCode('');
      setUnits('');
      setCurrentValue('');
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not add position.');
    } finally {
      setIsSaving(false);
    }
  };

  const startEditing = (position: Position) => {
    setEditingId(position.id);
    setEditUnits(String(position.units));
    setEditCurrentValue(String(position.current_value));
  };

  const savePosition = async (position: Position) => {
    if (!selectedPortfolio) return;
    setIsSaving(true);
    setError(null);
    try {
      const { response, body } = await portfolioRequest(`/api/portfolio/${selectedPortfolio.id}/positions/${position.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ units: editUnits, current_value: editCurrentValue }),
      });
      if (!response.ok) throw new Error(apiError(body, 'Could not update position.'));
      setEditingId(null);
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not update position.');
    } finally {
      setIsSaving(false);
    }
  };

  const removePosition = async (position: Position) => {
    if (!selectedPortfolio || !window.confirm(`Remove scheme ${position.scheme_code} from this manual portfolio?`)) return;
    setIsSaving(true);
    setError(null);
    try {
      const { response, body } = await portfolioRequest(`/api/portfolio/${selectedPortfolio.id}/positions/${position.id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error(apiError(body, 'Could not remove position.'));
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not remove position.');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading && !portfolios.length) {
    return <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 text-sm text-slate-300">Loading manual portfolio data…</div>;
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-300">Research workspace</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Manual portfolio tracking</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
            Store your own mutual-fund position snapshot and inspect overlap against the latest stored official holdings.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={isLoading}
          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/[0.04] px-4 text-xs font-semibold text-slate-200 transition hover:border-emerald-400/50 disabled:opacity-60"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh stored data
        </button>
      </div>

      <div className="flex items-start gap-3 rounded-2xl border border-amber-300/25 bg-amber-300/[0.08] p-4 text-sm text-amber-100">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-amber-200" />
        <p>
          Research only. Phase 1 stores units and the current value you enter; it does not import transactions, calculate cost basis/gains/XIRR, or recommend buying, selling, or rebalancing. It is not an investment recommendation.
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-400/25 bg-rose-400/10 p-4 text-sm text-rose-100" role="alert">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Your portfolios</p>
            <p className="mt-1 text-sm text-slate-300">Positions are private to your signed-in account.</p>
          </div>
          <form onSubmit={createPortfolio} className="flex w-full max-w-md gap-2">
            <input
              value={portfolioName}
              onChange={(event) => setPortfolioName(event.target.value)}
              aria-label="New portfolio name"
              maxLength={80}
              className="min-w-0 flex-1 rounded-lg border border-white/15 bg-black/20 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-emerald-400/60"
              placeholder="Portfolio name"
            />
            <button type="submit" disabled={isSaving || !portfolioName.trim()} className="inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-3 py-2 text-xs font-bold text-slate-950 transition hover:bg-emerald-300 disabled:opacity-50">
              <Plus className="h-3.5 w-3.5" /> Create
            </button>
          </form>
        </div>
        {portfolios.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {portfolios.map((portfolio) => (
              <button
                type="button"
                key={portfolio.id}
                onClick={() => setSelectedId(portfolio.id)}
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${portfolio.id === selectedPortfolio?.id ? 'border-emerald-400/60 bg-emerald-400/15 text-emerald-100' : 'border-white/10 bg-white/[0.03] text-slate-300 hover:border-white/25'}`}
              >
                {portfolio.name}
              </button>
            ))}
          </div>
        )}
      </section>

      {!selectedPortfolio ? (
        <section className="rounded-2xl border border-dashed border-white/15 bg-white/[0.02] p-8 text-center">
          <WalletCards className="mx-auto h-8 w-8 text-emerald-300" />
          <h2 className="mt-3 text-lg font-semibold text-white">Create a research portfolio</h2>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-400">Start with a name above, then add scheme codes, units, and the current value you want to review.</p>
        </section>
      ) : (
        <>
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="Manual value" value={formatInr(selectedPortfolio.total_current_value)} note="As entered by you" icon={WalletCards} />
            <Metric label="Schemes" value={String(selectedPortfolio.positions.length)} note="Manual positions" icon={Database} />
            <Metric label="Aggregate overlap" value={selectedPortfolio.aggregate_overlap.total_overlap_percent === null ? 'Not available' : `${selectedPortfolio.aggregate_overlap.total_overlap_percent.toFixed(2)}%`} note={selectedPortfolio.aggregate_overlap.coverage_status === 'partial' ? 'Partial holdings coverage' : 'Stored holdings only'} icon={ShieldCheck} />
            <Metric label="Data freshness" value={selectedPortfolio.freshness.status} note={`${selectedPortfolio.freshness.positions_with_holdings}/${selectedPortfolio.positions.length} with holdings`} icon={RefreshCw} />
          </section>

          <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">Add a mutual-fund position</h2>
                <p className="mt-1 text-xs leading-5 text-slate-400">Use the AMFI scheme code. Values remain manual until transaction import is implemented.</p>
              </div>
            </div>
            <form onSubmit={addPosition} className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_1fr_auto]">
              <label className="text-xs text-slate-300">
                Scheme code
                <input required inputMode="numeric" value={schemeCode} onChange={(event) => setSchemeCode(event.target.value)} placeholder="e.g. 122639" className="mt-1.5 w-full rounded-lg border border-white/15 bg-black/20 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-400/60" />
              </label>
              <label className="text-xs text-slate-300">
                Units
                <input required inputMode="decimal" type="number" min="0.00000001" step="0.00000001" value={units} onChange={(event) => setUnits(event.target.value)} placeholder="0.0000" className="mt-1.5 w-full rounded-lg border border-white/15 bg-black/20 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-400/60" />
              </label>
              <label className="text-xs text-slate-300">
                Current value (INR)
                <input required inputMode="decimal" type="number" min="0" step="0.01" value={currentValue} onChange={(event) => setCurrentValue(event.target.value)} placeholder="0.00" className="mt-1.5 w-full rounded-lg border border-white/15 bg-black/20 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-400/60" />
              </label>
              <button type="submit" disabled={isSaving} className="mt-auto inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-emerald-400 px-4 text-xs font-bold text-slate-950 transition hover:bg-emerald-300 disabled:opacity-50">
                <Plus className="h-3.5 w-3.5" /> Add position
              </button>
            </form>
          </section>

          <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
            <div className="mb-4 flex items-center gap-2">
              <Database className="h-4 w-4 text-emerald-300" />
              <div>
                <h2 className="text-lg font-semibold text-white">Positions and stored data</h2>
                <p className="mt-1 text-xs text-slate-400">Manual value is separate from FundersAI NAV and holdings dates.</p>
              </div>
            </div>
            {selectedPortfolio.positions.length === 0 ? (
              <p className="rounded-xl border border-dashed border-white/15 p-5 text-sm text-slate-400">No positions yet.</p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-white/10">
                <table className="min-w-[920px] w-full text-left text-xs">
                  <thead className="bg-white/[0.05] text-slate-400">
                    <tr>
                      <th className="px-3 py-3 font-semibold">Scheme</th>
                      <th className="px-3 py-3 font-semibold">Units</th>
                      <th className="px-3 py-3 font-semibold">Manual value</th>
                      <th className="px-3 py-3 font-semibold">Holdings as of</th>
                      <th className="px-3 py-3 font-semibold">NAV date</th>
                      <th className="px-3 py-3 font-semibold">Status</th>
                      <th className="px-3 py-3 font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10">
                    {selectedPortfolio.positions.map((position) => {
                      const editing = editingId === position.id;
                      return (
                        <tr key={position.id} className="text-slate-200">
                          <td className="px-3 py-3">
                            <div className="font-semibold text-white">{position.fund.scheme_name || `Scheme ${position.scheme_code}`}</div>
                            <div className="mt-1 text-[10px] text-slate-500">{position.scheme_code} · {position.fund.amc_name || 'AMC unavailable'}{position.fund.category ? ` · ${position.fund.category}` : ''}</div>
                          </td>
                          <td className="px-3 py-3">
                            {editing ? <input value={editUnits} onChange={(event) => setEditUnits(event.target.value)} type="number" min="0.00000001" step="0.00000001" className="w-28 rounded border border-white/15 bg-black/20 px-2 py-1.5 text-white" aria-label={`Units for ${position.scheme_code}`} /> : formatNumber(position.units)}
                          </td>
                          <td className="px-3 py-3 font-mono">
                            {editing ? <input value={editCurrentValue} onChange={(event) => setEditCurrentValue(event.target.value)} type="number" min="0" step="0.01" className="w-32 rounded border border-white/15 bg-black/20 px-2 py-1.5 text-white" aria-label={`Current value for ${position.scheme_code}`} /> : formatInr(position.current_value)}
                          </td>
                          <td className="px-3 py-3 text-slate-300">{formatDate(position.freshness.holdings_as_of_date)}</td>
                          <td className="px-3 py-3 text-slate-300">{formatDate(position.freshness.nav_date)}</td>
                          <td className="px-3 py-3"><span className={`inline-flex rounded-full border px-2 py-1 text-[10px] font-semibold capitalize ${statusClass(position.freshness.status)}`}>{position.freshness.status}</span></td>
                          <td className="px-3 py-3">
                            <div className="flex items-center gap-2">
                              {editing ? (
                                <>
                                  <button type="button" onClick={() => void savePosition(position)} disabled={isSaving} className="inline-flex items-center gap-1 rounded border border-emerald-400/30 px-2 py-1.5 text-[11px] text-emerald-200 hover:bg-emerald-400/10 disabled:opacity-50"><Save className="h-3 w-3" /> Save</button>
                                  <button type="button" onClick={() => setEditingId(null)} className="inline-flex items-center gap-1 rounded border border-white/15 px-2 py-1.5 text-[11px] text-slate-300 hover:bg-white/5"><X className="h-3 w-3" /> Cancel</button>
                                </>
                              ) : (
                                <>
                                  <button type="button" onClick={() => startEditing(position)} className="inline-flex items-center gap-1 rounded border border-white/15 px-2 py-1.5 text-[11px] text-slate-300 hover:border-white/30 hover:text-white"><Pencil className="h-3 w-3" /> Edit</button>
                                  <button type="button" onClick={() => void removePosition(position)} disabled={isSaving} className="inline-flex items-center gap-1 rounded border border-rose-400/20 px-2 py-1.5 text-[11px] text-rose-200 hover:bg-rose-400/10 disabled:opacity-50"><Trash2 className="h-3 w-3" /> Remove</button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-white">Aggregate overlap</h2>
                  <p className="mt-1 text-xs leading-5 text-slate-400">Duplicated underlying exposure = total exposure minus the largest single-fund contribution for each common holding.</p>
                </div>
                <span className={`inline-flex w-fit rounded-full border px-2.5 py-1 text-[10px] font-semibold capitalize ${statusClass(selectedPortfolio.aggregate_overlap.coverage_status)}`}>{selectedPortfolio.aggregate_overlap.coverage_status} coverage</span>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <Metric label="Duplicated exposure" value={selectedPortfolio.aggregate_overlap.total_overlap_percent === null ? 'Not available' : `${selectedPortfolio.aggregate_overlap.total_overlap_percent.toFixed(2)}%`} note={formatInr(selectedPortfolio.aggregate_overlap.total_overlap_exposure)} icon={ShieldCheck} />
                <Metric label="Covered value" value={formatInr(selectedPortfolio.aggregate_overlap.covered_current_value)} note={`${selectedPortfolio.aggregate_overlap.positions_with_holdings} positions`} icon={Database} />
                <Metric label="Uncovered value" value={formatInr(selectedPortfolio.aggregate_overlap.uncovered_current_value)} note="Not included in holdings overlap" icon={AlertTriangle} />
              </div>
              {selectedPortfolio.aggregate_overlap.top_common_holdings.length > 0 ? (
                <div className="mt-5 overflow-x-auto rounded-xl border border-white/10">
                  <table className="min-w-[600px] w-full text-left text-xs">
                    <thead className="bg-white/[0.05] text-slate-400"><tr><th className="px-3 py-2 font-semibold">Common holding</th><th className="px-3 py-2 font-semibold">Funds</th><th className="px-3 py-2 font-semibold">Portfolio exposure</th><th className="px-3 py-2 font-semibold">Duplicated</th></tr></thead>
                    <tbody className="divide-y divide-white/10">
                      {selectedPortfolio.aggregate_overlap.top_common_holdings.map((holding) => (
                        <tr key={`${holding.isin || holding.name}-${holding.sector || ''}`} className="text-slate-200">
                          <td className="px-3 py-3"><div className="font-medium text-white">{holding.name}</div><div className="mt-1 text-[10px] text-slate-500">{holding.isin || holding.sector || 'Identifier unavailable'}</div></td>
                          <td className="px-3 py-3">{holding.fund_count}</td>
                          <td className="px-3 py-3">{holding.portfolio_exposure === null ? 'Not available' : `${holding.portfolio_exposure.toFixed(2)}%`}</td>
                          <td className="px-3 py-3">{holding.overlap_exposure === null ? 'Not available' : `${holding.overlap_exposure.toFixed(2)}%`}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="mt-5 rounded-xl border border-dashed border-white/15 p-4 text-sm text-slate-400">No common holding was computed from the latest stored holdings.</p>
              )}
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
              <div className="flex items-center gap-2"><RefreshCw className="h-4 w-4 text-emerald-300" /><h2 className="text-lg font-semibold text-white">Data freshness</h2></div>
              <p className="mt-2 text-xs leading-5 text-slate-400">Dates are source metadata. They do not make a return or allocation prediction.</p>
              <div className="mt-4 space-y-3 text-xs">
                <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-3"><span className="text-slate-400">Portfolio status</span><span className={`rounded-full border px-2 py-1 capitalize ${statusClass(selectedPortfolio.freshness.status)}`}>{selectedPortfolio.freshness.status}</span></div>
                <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-3"><span className="text-slate-400">Latest stored NAV</span><span className="text-right text-slate-200">{formatDate(selectedPortfolio.freshness.latest_nav_date)}</span></div>
                <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-3"><span className="text-slate-400">Latest holdings disclosure</span><span className="text-right text-slate-200">{formatDate(selectedPortfolio.freshness.latest_holdings_as_of_date)}</span></div>
                <div className="flex items-center justify-between gap-3"><span className="text-slate-400">Holdings coverage</span><span className="text-right text-slate-200">{selectedPortfolio.freshness.positions_with_holdings}/{selectedPortfolio.positions.length || 0} positions</span></div>
              </div>
              <div className="mt-5 rounded-xl border border-blue-300/20 bg-blue-300/[0.06] p-3 text-xs leading-5 text-blue-100"><strong>Source limit:</strong> overlap is unavailable or partial when FundersAI has no latest holdings rows for a scheme.</div>
            </div>
          </section>
        </>
      )}

      <p className="text-center text-[11px] leading-5 text-slate-500">{selectedPortfolio?.research_boundary || 'Manual position snapshot only. Future transaction import requires a separate consented ledger and source-validation flow.'}</p>
    </div>
  );
}

function Metric({ label, value, note, icon: Icon }: { label: string; value: string; note: string; icon: typeof WalletCards }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/15 p-4">
      <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400"><Icon className="h-3.5 w-3.5 text-emerald-300" />{label}</div>
      <div className="mt-2 text-xl font-semibold capitalize text-white">{value}</div>
      <div className="mt-1 text-[11px] text-slate-500">{note}</div>
    </div>
  );
}
