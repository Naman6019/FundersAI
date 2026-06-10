'use client';

import { BarChart3, Layers3, ListChecks, ShieldCheck } from 'lucide-react';
import type { CanvasPayload, CategoryComparePayload, CategoryFundRow } from '@/types/funds';

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function formatPercent(value: unknown, digits = 2): string {
  const num = toNumber(value);
  if (num === null) return 'N/A';
  return `${num.toFixed(digits)}%`;
}

function formatAum(value: unknown): string {
  const num = toNumber(value);
  if (num === null) return 'N/A';
  return `INR ${Math.round(num).toLocaleString('en-IN')}`;
}

function formatRiskLabel(value: unknown): string {
  const label = typeof value === 'string' ? value.trim() : '';
  return label || 'Risk label unavailable';
}

function getComparePayload(auxiliaryData?: CanvasPayload | null): CategoryComparePayload | null {
  const quant = auxiliaryData?.quant_data;
  if (!quant || typeof quant !== 'object') return null;
  const payload = (quant as { category_compare?: CategoryComparePayload }).category_compare;
  return payload && typeof payload === 'object' ? payload : null;
}

function compactName(name: unknown): string {
  return String(name || 'N/A')
    .replace(/\s*-\s*Direct Plan\s*-\s*Growth/gi, '')
    .replace(/\s*Direct\s*Growth/gi, '')
    .trim();
}

function metricValue(fund: CategoryFundRow, key: keyof CategoryFundRow): string {
  if (key === 'aum') return formatAum(fund[key]);
  if (key === 'risk_level') return formatRiskLabel(fund[key]);
  if (['return_1y', 'return_3y', 'return_5y', 'expense_ratio', 'volatility_1y', 'max_drawdown_1y', 'alpha'].includes(key)) {
    return formatPercent(fund[key]);
  }
  const value = fund[key];
  return value === null || value === undefined || value === '' ? 'N/A' : String(value);
}

export default function CategoryCompareView({ auxiliaryData }: { auxiliaryData?: CanvasPayload | null }) {
  const payload = getComparePayload(auxiliaryData);
  if (!payload) {
    return (
      <div className="flex h-full items-center justify-center rounded-[1.35rem] border border-white/10 bg-[#0b1325] p-6 text-sm text-slate-300">
        Category comparison data is unavailable.
      </div>
    );
  }

  const funds = Array.isArray(payload.selected_funds) ? payload.selected_funds : [];
  const overlap = payload.overlap || {};
  const insights = payload.insights || {};
  const commonHoldings = Array.isArray(overlap.top_common_holdings) ? overlap.top_common_holdings as Array<Record<string, unknown>> : [];
  const sectorOverlap = Array.isArray(overlap.sector_overlap) ? overlap.sector_overlap as Array<Record<string, unknown>> : [];
  const metrics: Array<{ label: string; key: keyof CategoryFundRow }> = [
    { label: '1Y Return', key: 'return_1y' },
    { label: '3Y Return', key: 'return_3y' },
    { label: '5Y Return', key: 'return_5y' },
    { label: 'Expense Ratio', key: 'expense_ratio' },
    { label: 'AUM', key: 'aum' },
    { label: 'Official Risk Label', key: 'risk_level' },
    { label: 'Volatility 1Y', key: 'volatility_1y' },
    { label: 'Max Drawdown 1Y', key: 'max_drawdown_1y' },
    { label: 'Sharpe', key: 'sharpe_ratio' },
    { label: 'Beta', key: 'beta' },
    { label: 'NAV Date', key: 'nav_date' },
  ];

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-[1.35rem] border border-white/10 bg-[linear-gradient(160deg,rgba(10,18,34,0.96),rgba(3,10,22,0.98))] shadow-[0_20px_44px_rgba(0,0,0,0.35)]">
      <div className="border-b border-white/10 px-6 py-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#66a3ff]">Category compare</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">{payload.category} fund comparison</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-300">
              Metrics, latest portfolios, and equal-weighted overlap across the selected funds.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.12em] text-slate-400">Funds</p>
              <p className="mt-1 text-xl font-semibold text-white">{funds.length}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.12em] text-slate-400">Label</p>
              <p className="mt-1 text-xl font-semibold text-white">{payload.label || 'N/A'}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.12em] text-slate-400">Overlap</p>
              <p className="mt-1 text-xl font-semibold text-white">{formatPercent(overlap.total_overlap_exposure)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
        <section className="rounded-2xl border border-white/10 bg-[#101b2d] p-5">
          <div className="mb-4 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-[#66a3ff]" />
            <h3 className="text-sm font-semibold text-white">Metrics across selected funds</h3>
          </div>
          <div className="overflow-x-auto rounded-xl border border-white/10">
            <table className="min-w-full text-left text-xs">
              <thead className="bg-white/[0.06] text-[#8ea7cd]">
                <tr>
                  <th className="px-3 py-2 font-semibold">Metric</th>
                  {funds.map((fund) => (
                    <th key={String(fund.scheme_code)} className="min-w-44 px-3 py-2 font-semibold">{compactName(fund.scheme_name)}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10 text-[#d7e4fb]">
                {metrics.map((metric) => (
                  <tr key={metric.key}>
                    <td className="px-3 py-3 font-medium text-white">{metric.label}</td>
                    {funds.map((fund) => (
                      <td key={`${fund.scheme_code}-${metric.key}`} className="px-3 py-3 font-mono">{metricValue(fund, metric.key)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-5 rounded-2xl border border-white/10 bg-[#101b2d] p-5">
          <div className="mb-4 flex items-center gap-2">
            <ListChecks className="h-4 w-4 text-[#66a3ff]" />
            <h3 className="text-sm font-semibold text-white">Review interpretation</h3>
          </div>
          <p className="text-sm leading-relaxed text-[#d7e4fb]">{insights.headline || payload.research_note}</p>
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            {[
              ['Portfolio read', insights.review_points || []],
              ['Overlap read', insights.overlap_read || []],
              ['Watchpoints', insights.watchpoints || []],
            ].map(([title, items]) => (
              <div key={String(title)} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">{String(title)}</h4>
                <ul className="mt-3 space-y-2 text-sm leading-relaxed text-[#d7e4fb]">
                  {(items as string[]).slice(0, 4).map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-5 grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
          <div className="rounded-2xl border border-white/10 bg-[#101b2d] p-5">
            <div className="mb-4 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[#66a3ff]" />
              <h3 className="text-sm font-semibold text-white">Top holdings per fund</h3>
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              {funds.map((fund) => (
                <div key={String(fund.scheme_code)} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <h4 className="line-clamp-2 text-sm font-semibold text-white">{compactName(fund.scheme_name)}</h4>
                  <p className="mt-2 text-xs text-[#8ea7cd]">
                    {formatRiskLabel(fund.risk_level)}
                    {fund.risk_level ? ' · Official AMC factsheet' : ''}
                  </p>
                  <div className="mt-3 space-y-2">
                    {(fund.top_holdings || []).slice(0, 6).map((holding) => (
                      <div key={String(holding.isin || holding.security_name)} className="flex items-center justify-between gap-3 text-xs text-[#d7e4fb]">
                        <span className="truncate">{String(holding.security_name || 'N/A')}</span>
                        <span className="font-mono text-white">{formatPercent(holding.weight_pct)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#101b2d] p-5">
            <div className="mb-4 flex items-center gap-2">
              <Layers3 className="h-4 w-4 text-[#66a3ff]" />
              <h3 className="text-sm font-semibold text-white">Overlap</h3>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <p className="text-[11px] uppercase tracking-[0.12em] text-slate-400">Duplicated exposure</p>
              <p className="mt-1 text-2xl font-semibold text-white">{formatPercent(overlap.total_overlap_exposure)}</p>
              <p className="mt-1 text-xs text-[#8ea7cd]">{Number(overlap.common_holding_count || 0)} common holdings</p>
            </div>
            <div className="mt-4 space-y-2">
              {commonHoldings.slice(0, 8).map((item) => (
                <div key={String(item.isin || item.name)} className="flex items-center justify-between gap-3 text-xs text-[#d7e4fb]">
                  <span className="truncate">{String(item.name || 'N/A')}</span>
                  <span className="font-mono text-white">{formatPercent(item.overlap_exposure)}</span>
                </div>
              ))}
            </div>
            {sectorOverlap.length > 0 && (
              <div className="mt-5 border-t border-white/10 pt-4">
                <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Sector overlap</h4>
                <div className="mt-3 space-y-2">
                  {sectorOverlap.slice(0, 6).map((item) => (
                    <div key={String(item.sector)} className="flex items-center justify-between gap-3 text-xs text-[#d7e4fb]">
                      <span className="truncate">{String(item.sector || 'Unclassified')}</span>
                      <span className="font-mono text-white">{formatPercent(item.overlap_exposure)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
