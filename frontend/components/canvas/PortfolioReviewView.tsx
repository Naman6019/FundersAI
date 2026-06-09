'use client';

import { AlertCircle, Layers3, ListChecks, PieChart, ShieldCheck } from 'lucide-react';
import type { CanvasPayload } from '@/types/funds';

type PortfolioHolding = {
  input_name?: string;
  amount?: number | string | null;
  weight?: number | string | null;
  matched?: { scheme_name?: string | null } | null;
  matched_fund?: string | null;
  bucket?: string | null;
};

type PortfolioOverlap = {
  coverage_status?: string;
  reason?: string;
  matched_fund_count?: number;
  funds_with_holdings?: number;
  common_holding_count?: number;
  total_overlap_exposure?: number;
  top_common_holdings?: Array<{
    name?: string | null;
    isin?: string | null;
    sector?: string | null;
    fund_count?: number;
    portfolio_exposure?: number;
    overlap_exposure?: number;
  }>;
  sector_overlap?: Array<{
    sector?: string | null;
    fund_count?: number;
    portfolio_exposure?: number;
    overlap_exposure?: number;
  }>;
};

type PortfolioReview = {
  score?: number;
  label?: string;
  holdings?: PortfolioHolding[];
  buckets?: Record<string, number>;
  overlap?: PortfolioOverlap;
  insights?: {
    headline?: string;
    overlap_level?: string;
    review_points?: string[];
    overlap_read?: string[];
    watchpoints?: string[];
    next_questions?: string[];
  };
};

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function formatInr(value: unknown): string {
  const num = toNumber(value);
  if (num === null) return 'N/A';
  return `INR ${Math.round(num).toLocaleString('en-IN')}`;
}

function formatPercent(value: unknown, digits = 1): string {
  const num = toNumber(value);
  if (num === null) return 'N/A';
  return `${num.toFixed(digits)}%`;
}

function getPortfolioReview(auxiliaryData?: CanvasPayload | null): PortfolioReview | null {
  const quant = auxiliaryData?.quant_data;
  if (!quant || typeof quant !== 'object') return null;
  const review = (quant as { portfolio_review?: PortfolioReview }).portfolio_review;
  return review && typeof review === 'object' ? review : null;
}

export default function PortfolioReviewView({ auxiliaryData }: { auxiliaryData?: CanvasPayload | null }) {
  const review = getPortfolioReview(auxiliaryData);

  if (!review) {
    return (
      <div className="flex h-full items-center justify-center rounded-[1.35rem] border border-white/10 bg-[#0b1325] p-6 text-sm text-slate-300">
        Portfolio review data is unavailable.
      </div>
    );
  }

  const holdings = Array.isArray(review.holdings) ? review.holdings : [];
  const buckets = review.buckets || {};
  const overlap = review.overlap || {};
  const insights = review.insights || {};
  const bucketRows = Object.entries(buckets).sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0));
  const totalAmount = bucketRows.reduce((sum, [, amount]) => sum + Number(amount || 0), 0);
  const overlapAvailable = overlap.coverage_status === 'available';

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-[1.35rem] border border-white/10 bg-[linear-gradient(160deg,rgba(10,18,34,0.96),rgba(3,10,22,0.98))] shadow-[0_20px_44px_rgba(0,0,0,0.35)]">
      <div className="border-b border-white/10 px-6 py-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#66a3ff]">Portfolio canvas</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">Holdings overlap review</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-300">
              Side-by-side view of submitted funds, category allocation, and duplicated stock exposure from latest available holdings.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.12em] text-slate-400">Score</p>
              <p className="mt-1 text-xl font-semibold text-white">{review.score ?? 'N/A'}/100</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.12em] text-slate-400">Label</p>
              <p className="mt-1 text-xl font-semibold text-white">{review.label || 'N/A'}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
              <p className="text-[11px] uppercase tracking-[0.12em] text-slate-400">Overlap</p>
              <p className="mt-1 text-xl font-semibold text-white">{formatPercent(overlap.total_overlap_exposure, 2)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
        <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <section className="rounded-2xl border border-white/10 bg-[#101b2d] p-5">
            <div className="mb-4 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[#66a3ff]" />
              <h3 className="text-sm font-semibold text-white">Submitted funds</h3>
            </div>
            <div className="overflow-hidden rounded-xl border border-white/10">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-white/[0.06] text-[#8ea7cd]">
                  <tr>
                    <th className="px-3 py-2 font-semibold">Input</th>
                    <th className="px-3 py-2 font-semibold">Matched fund</th>
                    <th className="px-3 py-2 font-semibold">Bucket</th>
                    <th className="px-3 py-2 font-semibold">Amount</th>
                    <th className="px-3 py-2 font-semibold">Weight</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10 text-[#d7e4fb]">
                  {holdings.map((item, index) => (
                    <tr key={`${item.input_name}-${index}`}>
                      <td className="px-3 py-3 font-medium text-white">{item.input_name || 'N/A'}</td>
                      <td className="px-3 py-3">{item.matched?.scheme_name || item.matched_fund || 'N/A'}</td>
                      <td className="px-3 py-3">{item.bucket || 'N/A'}</td>
                      <td className="px-3 py-3">{formatInr(item.amount)}</td>
                      <td className="px-3 py-3">{formatPercent((toNumber(item.weight) || 0) * 100)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-2xl border border-white/10 bg-[#101b2d] p-5">
            <div className="mb-4 flex items-center gap-2">
              <PieChart className="h-4 w-4 text-[#66a3ff]" />
              <h3 className="text-sm font-semibold text-white">Category allocation</h3>
            </div>
            <div className="space-y-3">
              {bucketRows.map(([bucket, amount]) => {
                const pct = totalAmount > 0 ? (Number(amount || 0) / totalAmount) * 100 : 0;
                return (
                  <div key={bucket}>
                    <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                      <span className="text-[#d7e4fb]">{bucket}</span>
                      <span className="font-mono text-white">{formatPercent(pct)}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
                      <div className="h-full rounded-full bg-[#66a3ff]" style={{ width: `${Math.max(3, Math.min(100, pct))}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>

        <section className="mt-5 rounded-2xl border border-white/10 bg-[#101b2d] p-5">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-center gap-2">
              <ListChecks className="h-4 w-4 text-[#66a3ff]" />
              <div>
                <h3 className="text-sm font-semibold text-white">Review interpretation</h3>
                <p className="mt-1 text-xs text-[#8ea7cd]">{insights.headline || 'Review points are generated from allocation, matched funds, and latest holdings overlap.'}</p>
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-right">
              <p className="text-[11px] uppercase tracking-[0.12em] text-slate-400">Overlap level</p>
              <p className="text-lg font-semibold text-white">{insights.overlap_level || 'N/A'}</p>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Portfolio read</h4>
              <ul className="mt-3 space-y-2 text-sm leading-relaxed text-[#d7e4fb]">
                {(insights.review_points || []).slice(0, 4).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Overlap read</h4>
              <ul className="mt-3 space-y-2 text-sm leading-relaxed text-[#d7e4fb]">
                {(insights.overlap_read || []).slice(0, 4).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Watchpoints</h4>
              <ul className="mt-3 space-y-2 text-sm leading-relaxed text-[#d7e4fb]">
                {(insights.watchpoints || []).slice(0, 4).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          </div>

          {Array.isArray(insights.next_questions) && insights.next_questions.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {insights.next_questions.slice(0, 3).map((item) => (
                <span key={item} className="rounded-full border border-[#66a3ff]/25 bg-[#66a3ff]/10 px-3 py-1 text-xs text-[#cce0ff]">
                  {item}
                </span>
              ))}
            </div>
          )}
        </section>

        <section className="mt-5 rounded-2xl border border-white/10 bg-[#101b2d] p-5">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-center gap-2">
              <Layers3 className="h-4 w-4 text-[#66a3ff]" />
              <div>
                <h3 className="text-sm font-semibold text-white">Actual holdings overlap</h3>
                <p className="mt-1 text-xs text-[#8ea7cd]">
                  {overlapAvailable
                    ? `${overlap.funds_with_holdings || 0}/${overlap.matched_fund_count || 0} matched funds have holdings data.`
                    : overlap.reason || 'Holdings overlap unavailable.'}
                </p>
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-right">
              <p className="text-[11px] uppercase tracking-[0.12em] text-slate-400">Duplicated exposure</p>
              <p className="text-xl font-semibold text-white">{formatPercent(overlap.total_overlap_exposure, 2)}</p>
            </div>
          </div>

          {overlapAvailable ? (
            <div className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
              <div className="overflow-hidden rounded-xl border border-white/10">
                <table className="min-w-full text-left text-xs">
                  <thead className="bg-white/[0.06] text-[#8ea7cd]">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Common holding</th>
                      <th className="px-3 py-2 font-semibold">Sector</th>
                      <th className="px-3 py-2 font-semibold">Funds</th>
                      <th className="px-3 py-2 font-semibold">Portfolio exposure</th>
                      <th className="px-3 py-2 font-semibold">Duplicated</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10 text-[#d7e4fb]">
                    {(overlap.top_common_holdings || []).slice(0, 12).map((item, index) => (
                      <tr key={`${item.isin || item.name}-${index}`}>
                        <td className="px-3 py-3 font-medium text-white">{item.name || 'N/A'}</td>
                        <td className="px-3 py-3">{item.sector || 'Unclassified'}</td>
                        <td className="px-3 py-3">{item.fund_count || 0}</td>
                        <td className="px-3 py-3">{formatPercent(item.portfolio_exposure, 2)}</td>
                        <td className="px-3 py-3">{formatPercent(item.overlap_exposure, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Sector overlap</h4>
                <div className="mt-3 space-y-3">
                  {(overlap.sector_overlap || []).slice(0, 8).map((sector) => (
                    <div key={sector.sector || 'Unclassified'} className="flex items-center justify-between gap-3 text-xs text-[#d7e4fb]">
                      <span className="truncate">{sector.sector || 'Unclassified'}</span>
                      <span className="font-mono text-white">{formatPercent(sector.overlap_exposure, 2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3 rounded-xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm text-amber-100">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>Overlap appears when at least two matched funds have latest holdings rows in the database.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
