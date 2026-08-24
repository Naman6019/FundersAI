import type { Metadata } from 'next';
import { Suspense } from 'react';
import Link from 'next/link';
import {
  AMC_REGISTRY,
  CATEGORY_LIST,
  FUND_REGISTRY,
  categorySlug,
} from '@/lib/fund-registry';
import { DirectoryJsonLd } from '@/components/seo/JsonLd';
import MutualFundExplorer from '@/components/funds/MutualFundExplorer';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';

export const metadata: Metadata = {
  title: 'Indian Mutual Funds Screener & Directory | FundersAI',
  description:
    'Search and filter Indian mutual funds by AMC house (HDFC, SBI, ICICI, Nippon, Quant, PPFAS) and SEBI category (Flexi Cap, Large, Mid, Small Cap). Deterministic metrics from AMFI and official AMC disclosures.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/mutual-funds',
  },
  openGraph: {
    title: 'Indian Mutual Funds Screener & Directory | FundersAI',
    description:
      'Search and filter Indian mutual funds by AMC fund house and SEBI category with deterministic risk-adjusted return metrics.',
    url: 'https://www.fundersai.co.in/mutual-funds',
    siteName: 'FundersAI',
  },
};

export default function MutualFundsPage() {
  const categoryFunds = CATEGORY_LIST.map((cat) => ({
    category: cat,
    count: FUND_REGISTRY.filter((f) => f.category === cat).length,
  }));

  return (
    <div className="min-h-dvh bg-[#070b12] text-[#dce8fa] flex flex-col justify-between">
      <DirectoryJsonLd funds={FUND_REGISTRY} />
      <EcosystemHeader currentApp="mutual-funds" />

      <main className="flex-1">
        <div className="mx-auto max-w-6xl px-5 py-12 sm:px-8 space-y-16">
          {/* Hero */}
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#00FF9D]/20 bg-[#00FF9D]/[0.06] px-3 py-1 text-xs font-semibold text-[#00FF9D] mb-4">
              <span>Verified AMFI &amp; AMC Dataset</span>
              <span>•</span>
              <span className="text-white/80">{FUND_REGISTRY.length} Direct Growth Schemes</span>
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl mb-4">
              Indian Mutual Funds Screener
            </h1>
            <p className="text-base leading-7 text-[#aebed6] max-w-3xl">
              Filter mutual funds by <strong className="text-white">Fund House (AMC Family)</strong> and <strong className="text-white">SEBI Category</strong>, or search by scheme name and AMFI code. Inspect individual fund metrics, calculate benchmark performance, or launch a full quantitative analysis in the workspace.
            </p>
          </div>

          {/* Interactive Screener & Metric Inspector Canvas */}
          <section>
            <Suspense fallback={
              <div className="h-64 rounded-2xl border border-white/10 bg-white/[0.02] flex items-center justify-center text-sm text-[#7183a0]">
                Loading Mutual Fund Screener...
              </div>
            }>
              <MutualFundExplorer
                initialFunds={FUND_REGISTRY}
                amcs={AMC_REGISTRY}
                categories={CATEGORY_LIST}
              />
            </Suspense>
          </section>

          {/* Browse by AMC (Permanent Crawlable SEO Anchor Hub) */}
          <section className="pt-8 border-t border-white/5">
            <div className="flex items-baseline justify-between mb-6">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#00FF9D]/70 mb-1">Crawl Directory</p>
                <h2 className="text-2xl font-bold text-white">Browse by AMC Fund House</h2>
              </div>
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
                      View all {amc.shortName} schemes →
                    </span>
                  </Link>
                );
              })}
            </div>
          </section>

          {/* Browse by Category (Permanent Crawlable SEO Anchor Hub) */}
          <section className="pt-8 border-t border-white/5">
            <div className="flex items-baseline justify-between mb-6">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#66a3ff]/70 mb-1">SEBI Categories</p>
                <h2 className="text-2xl font-bold text-white">Browse by Investment Category</h2>
              </div>
              <span className="text-xs text-[#7183a0]">{CATEGORY_LIST.length} categories</span>
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

          {/* Disclosure & E-E-A-T Footnote */}
          <div className="rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 text-xs text-[#7183a0]">
            <p>
              <span className="font-semibold text-white/60">Research only. </span>
              FundersAI provides deterministic metric computation from official Association of Mutual Funds in India (AMFI) daily NAV disclosures and monthly AMC portfolio filings. Nothing on this page constitutes financial advice or personalized investment recommendation. Always verify with official AMC Scheme Information Documents (SID).
            </p>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
