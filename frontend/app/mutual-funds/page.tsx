import type { Metadata } from 'next';
import Link from 'next/link';
import { AMC_REGISTRY, CATEGORY_LIST, FUND_REGISTRY, categorySlug } from '@/lib/fund-registry';

export const metadata: Metadata = {
  title: 'Mutual Funds | FundersAI',
  description:
    'Browse and compare Indian mutual funds by AMC or category. Deterministic metrics from official sources — NAV, CAGR, Sharpe, expense ratio, and portfolio holdings.',
};

export default function MutualFundsPage() {
  const categoryFunds = CATEGORY_LIST.map((cat) => ({
    category: cat,
    count: FUND_REGISTRY.filter((f) => f.category === cat).length,
  }));

  return (
    <main className="min-h-dvh bg-[#070b12] text-[#dce8fa]">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#070b12]/90 backdrop-blur-md sticky top-0 z-30">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/" className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            ← FundersAI
          </Link>
          <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#00FF9D]/60">Mutual Funds</span>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
        {/* Hero */}
        <div className="mb-16">
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#00FF9D]/70 mb-3">Browse</p>
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl mb-5">
            Indian Mutual Funds
          </h1>
          <p className="text-base leading-7 text-[#aebed6] max-w-2xl mb-6">
            Research mutual funds by AMC or category. All metrics are calculated deterministically from AMFI
            and official AMC sources — NAV history, expense ratios, holdings, and risk metrics.
          </p>
          {/* Search CTA */}
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-full border border-[#00FF9D]/30 bg-[#00FF9D]/[0.08] px-5 py-2.5 text-sm font-semibold text-[#00FF9D] transition hover:bg-[#00FF9D]/[0.15]"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <circle cx="5.5" cy="5.5" r="4.5" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M9.5 9.5L13 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            Search all funds in workspace
          </Link>
        </div>

        {/* Browse by AMC */}
        <section className="mb-16">
          <div className="flex items-baseline justify-between mb-6">
            <h2 className="text-2xl font-bold text-white">By AMC</h2>
            <span className="text-xs text-[#7183a0]">{AMC_REGISTRY.length} fund houses</span>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {AMC_REGISTRY.map((amc) => {
              const fundCount = FUND_REGISTRY.filter((f) => f.amcSlug === amc.slug).length;
              return (
                <Link
                  key={amc.slug}
                  href={`/mutual-funds/${amc.slug}`}
                  className="group flex flex-col rounded-2xl border border-white/10 bg-white/[0.025] p-5 transition hover:border-white/20 hover:bg-white/[0.04]"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-base font-bold text-white group-hover:text-[#00FF9D] transition-colors">
                      {amc.shortName}
                    </span>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-[#7183a0]">
                      {fundCount} fund{fundCount !== 1 ? 's' : ''} indexed
                    </span>
                  </div>
                  <p className="text-xs leading-5 text-[#7183a0] flex-1 mb-4">{amc.description}</p>
                  <span className="text-xs font-semibold text-[#82aff6] group-hover:text-[#b8d3ff] transition-colors">
                    View funds →
                  </span>
                </Link>
              );
            })}
          </div>
        </section>

        {/* Browse by Category */}
        <section className="mb-16">
          <div className="flex items-baseline justify-between mb-6">
            <h2 className="text-2xl font-bold text-white">By Category</h2>
            <span className="text-xs text-[#7183a0]">SEBI-defined categories</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {categoryFunds.map(({ category, count }) => (
              <Link
                key={category}
                href={`/mutual-funds/category/${categorySlug(category)}`}
                className="group flex flex-col rounded-xl border border-white/10 bg-white/[0.02] p-4 transition hover:border-white/20 hover:bg-white/[0.04]"
              >
                <p className="font-semibold text-white text-sm mb-1 group-hover:text-[#00FF9D] transition-colors">{category}</p>
                <p className="text-xs text-[#7183a0]">{count} fund{count !== 1 ? 's' : ''} in registry</p>
              </Link>
            ))}
          </div>
        </section>

        {/* All indexed funds table */}
        <section>
          <div className="flex items-baseline justify-between mb-6">
            <h2 className="text-2xl font-bold text-white">All indexed funds</h2>
            <span className="text-xs text-[#7183a0]">{FUND_REGISTRY.length} funds · July 2026</span>
          </div>
          <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.015]">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left px-5 py-4 font-semibold text-white">Fund</th>
                  <th className="text-left px-4 py-4 font-semibold text-white">AMC</th>
                  <th className="text-left px-4 py-4 font-semibold text-white">Category</th>
                  <th className="text-left px-4 py-4 font-semibold text-white">Plan</th>
                  <th className="text-left px-4 py-4 font-semibold text-white"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {FUND_REGISTRY.map((fund) => (
                  <tr key={`${fund.amcSlug}-${fund.fundSlug}`} className="transition hover:bg-white/[0.025]">
                    <td className="px-5 py-3.5 text-white font-medium">{fund.schemeName}</td>
                    <td className="px-4 py-3.5 text-[#aebed6]">{fund.amcName}</td>
                    <td className="px-4 py-3.5 text-[#7183a0]">{fund.category}</td>
                    <td className="px-4 py-3.5 text-[#7183a0]">{fund.plan} · {fund.option}</td>
                    <td className="px-4 py-3.5">
                      <Link
                        href={`/mutual-funds/${fund.amcSlug}/${fund.fundSlug}`}
                        className="text-xs font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors whitespace-nowrap"
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Disclosure */}
        <div className="mt-12 rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 text-xs text-[#7183a0]">
          <p>
            <span className="font-semibold text-white/60">Coverage note: </span>
            This registry covers {FUND_REGISTRY.length} funds across {AMC_REGISTRY.length} AMCs as of July 2026.
            Coverage expands as additional AMC documents are acquired and indexed. For comprehensive data,
            use the workspace search which accesses the full Supabase-backed scheme database.
            All data sourced from AMFI and official AMC disclosures.
            FundersAI does not provide investment advice.
          </p>
        </div>

        <div className="mt-8 flex flex-wrap gap-4 border-t border-white/10 pt-6 text-sm">
          <Link href="/" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">Home</Link>
          <Link href="/methodology" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">Methodology</Link>
          <Link href="/dashboard" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">Open workspace</Link>
        </div>
      </div>
    </main>
  );
}
