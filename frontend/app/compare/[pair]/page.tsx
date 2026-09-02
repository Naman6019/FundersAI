import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { getFundBySlug, COMPARE_PAIRS } from '@/lib/fund-registry';
import { CompareJsonLd } from '@/components/seo/JsonLd';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';

type Props = { params: Promise<{ pair: string }> };

export async function generateStaticParams() {
  return COMPARE_PAIRS.map((p) => ({ pair: p.pair }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { pair } = await params;
  const entry = COMPARE_PAIRS.find((p) => p.pair === pair);
  if (!entry) return { title: 'Comparison Not Found | FundersAI' };
  const fundA = getFundBySlug(entry.amcSlugA, entry.fundSlugA);
  const fundB = getFundBySlug(entry.amcSlugB, entry.fundSlugB);
  if (!fundA || !fundB) return { title: 'Comparison Not Found | FundersAI' };
  const canonicalUrl = `https://www.fundersai.co.in/compare/${pair}`;
  return {
    title: `${fundA.schemeName} vs ${fundB.schemeName} | FundersAI`,
    description: `Compare ${fundA.schemeName} and ${fundB.schemeName} — 1Y/3Y/5Y CAGR, Sharpe ratio, max drawdown, expense ratio, AUM, and portfolio overlap. Deterministic metrics from official AMC sources.`,
    alternates: {
      canonical: canonicalUrl,
    },
    openGraph: {
      images: ['/opengraph-image'],
      title: `${fundA.schemeName} vs ${fundB.schemeName} | FundersAI`,
      description: `Head-to-head comparison of ${fundA.schemeName} and ${fundB.schemeName} with deterministic metrics.`,
      url: canonicalUrl,
    },
  };
}

// Static snapshot data for the two main Flexi Cap pair — others show live-analysis CTA
const STATIC_SNAPSHOTS: Record<string, {
  fundA: { nav: string; aum: string; ter: string; returns: Record<string, string>; sharpe: string; maxDD: string; stdDev: string };
  fundB: { nav: string; aum: string; ter: string; returns: Record<string, string>; sharpe: string; maxDD: string; stdDev: string };
  overlap: string;
  snapshotDate: string;
}> = {
  'hdfc-flexi-cap-fund-vs-parag-parikh-flexi-cap-fund': {
    fundA: { nav: '₹2,076', aum: '₹67,400 Cr', ter: '0.75%', returns: { '1Y': '28.4%', '3Y': '22.1%', '5Y': '27.8%' }, sharpe: '1.41', maxDD: '-19.2%', stdDev: '13.8%' },
    fundB: { nav: '₹86.2', aum: '₹87,900 Cr', ter: '0.57%', returns: { '1Y': '19.8%', '3Y': '17.3%', '5Y': '29.1%' }, sharpe: '1.38', maxDD: '-16.7%', stdDev: '11.2%' },
    overlap: '~38% by weight',
    snapshotDate: 'July 2026',
  },
};

function MetricRow({ label, a, b }: { label: string; a: string; b: string }) {
  return (
    <tr className="border-b border-white/5">
      <td className="py-3 pr-4 text-[#7183a0] text-xs font-medium">{label}</td>
      <td className="py-3 pr-4 text-center text-white font-semibold text-sm">{a}</td>
      <td className="py-3 text-center text-white font-semibold text-sm">{b}</td>
    </tr>
  );
}

export default async function ComparePage({ params }: Props) {
  const { pair } = await params;
  const entry = COMPARE_PAIRS.find((p) => p.pair === pair);
  if (!entry) notFound();

  const fundA = getFundBySlug(entry.amcSlugA, entry.fundSlugA);
  const fundB = getFundBySlug(entry.amcSlugB, entry.fundSlugB);
  if (!fundA || !fundB) notFound();

  const snapshot = STATIC_SNAPSHOTS[pair];

  return (
    <div className="min-h-dvh bg-[#070b12] text-[#dce8fa] flex flex-col justify-between">
      <CompareJsonLd fundA={fundA} fundB={fundB} pair={pair} />
      <EcosystemHeader currentApp="tools" />

      <main className="flex-1">
        <div className="mx-auto max-w-5xl px-5 py-12 sm:px-8">
          {/* Breadcrumb */}
          <Breadcrumbs
            className="mb-8"
            items={[
              { label: 'Home', href: '/' },
              { label: 'Mutual Funds', href: '/mutual-funds' },
              { label: 'Compare', href: '/compare' },
              { label: `${fundA.schemeName} vs ${fundB.schemeName}`, truncate: true },
            ]}
          />
        {/* Hero */}
        <div className="mb-12 text-center">
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#00FF9D]/70 mb-4">Fund Comparison</p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-3">
            {fundA.schemeName}
            <span className="mx-3 text-[#7183a0] font-normal">vs</span>
            {fundB.schemeName}
          </h1>
          {/*
            Reads fund A's fields for both funds only where they genuinely agree. With
            cross-category pairs in the registry (an index fund against an active large cap,
            say), asserting one fund's category or benchmark for the other would be wrong.
          */}
          <p className="text-sm text-[#7183a0]">
            {fundA.category === fundB.category ? fundA.category : `${fundA.category} vs ${fundB.category}`}
            {' · '}
            {fundA.option === fundB.option ? `Both ${fundA.option} plans` : `${fundA.option} vs ${fundB.option}`}
            {' · '}
            {fundA.benchmark === fundB.benchmark
              ? `Benchmark: ${fundA.benchmark}`
              : `Benchmarks: ${fundA.benchmark} / ${fundB.benchmark}`}
          </p>
          {snapshot && (
            <p className="mt-2 text-xs text-[#7183a0]">
              Static snapshot as of <span className="text-white/60 font-medium">{snapshot.snapshotDate}</span> — open workspace for live data
            </p>
          )}
        </div>

        {snapshot ? (
          <>
            {/* Side-by-side fund summary */}
            <div className="grid gap-4 sm:grid-cols-2 mb-8">
              {[
                { fund: fundA, data: snapshot.fundA, label: 'Fund A' },
                { fund: fundB, data: snapshot.fundB, label: 'Fund B' },
              ].map(({ fund, data }) => (
                <div key={fund.fundSlug} className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-[#7183a0] mb-2">{fund.amcName}</p>
                  <h2 className="text-base font-bold text-white mb-3 leading-snug">{fund.schemeName}</h2>
                  {/* Returns */}
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    {Object.entries(data.returns).map(([period, val]) => (
                      <div key={period} className="rounded-lg bg-[#00FF9D]/[0.07] border border-[#00FF9D]/20 px-2 py-2 text-center">
                        <p className="text-[9px] font-bold uppercase tracking-widest text-[#00FF9D]/70 mb-0.5">{period}</p>
                        <p className="text-base font-bold text-[#00FF9D]">{val}</p>
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-[#7183a0]">
                    <span><span className="text-white">NAV:</span> {data.nav}</span>
                    <span><span className="text-white">AUM:</span> {data.aum}</span>
                    <span><span className="text-white">TER:</span> {data.ter}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Head-to-head table */}
            <div className="rounded-2xl border border-white/10 bg-white/[0.015] overflow-x-auto mb-6">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left px-5 py-4 font-semibold text-[#7183a0] text-xs uppercase tracking-widest">Metric</th>
                    <th className="text-center px-4 py-4 font-semibold text-white">{fundA.schemeName.split(' ').slice(0, 3).join(' ')}</th>
                    <th className="text-center px-4 py-4 font-semibold text-white">{fundB.schemeName.split(' ').slice(0, 2).join(' ')}</th>
                  </tr>
                </thead>
                <tbody className="px-5">
                  <MetricRow label="Sharpe ratio" a={snapshot.fundA.sharpe} b={snapshot.fundB.sharpe} />
                  <MetricRow label="Std deviation (annualised)" a={snapshot.fundA.stdDev} b={snapshot.fundB.stdDev} />
                  <MetricRow label="Max drawdown" a={snapshot.fundA.maxDD} b={snapshot.fundB.maxDD} />
                  <MetricRow label="Expense ratio (TER)" a={snapshot.fundA.ter} b={snapshot.fundB.ter} />
                  <MetricRow label="AUM" a={snapshot.fundA.aum} b={snapshot.fundB.aum} />
                </tbody>
              </table>
            </div>

            {/* Overlap callout */}
            <div className="rounded-xl border border-[#66a3ff]/20 bg-[#66a3ff]/[0.05] px-5 py-4 mb-6 text-sm flex flex-col sm:flex-row sm:items-center gap-2">
              <span className="font-bold text-[#66a3ff]">Portfolio overlap:</span>
              <span className="text-[#aebed6]">{snapshot.overlap} (HDFC Bank, ICICI Bank common to both)</span>
              <span className="sm:ml-auto text-[10px] uppercase tracking-widest text-[#7183a0]">Source: AMC portfolio disclosures</span>
            </div>

            {/* Disclaimer + guardrails */}
            <div className="rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 flex flex-col sm:flex-row gap-4 text-xs text-[#7183a0] mb-8">
              <div className="flex items-start gap-2">
                <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-[#00FF9D]/50" />
                <span>Data sourced from AMFI, MFapi, and official AMC factsheets. All metrics are calculated deterministically.</span>
              </div>
              <div className="flex items-start gap-2 sm:border-l sm:border-white/10 sm:pl-4">
                <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-amber-400/50" />
                <span>Snapshot as of {snapshot.snapshotDate}. Returns are time-sensitive. Verify before any decision.</span>
              </div>
            </div>
          </>
        ) : (
          /*
           * Pairs without a hand-written performance snapshot still get the scheme identity
           * both funds are actually registered under — AMFI code, SEBI category, benchmark,
           * plan and option. That is verifiable registry data rather than a bare CTA, which
           * is what made these pages thin enough for Google to crawl and skip.
           */
          <>
            <div className="rounded-2xl border border-white/10 bg-white/[0.015] overflow-x-auto mb-6">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left px-5 py-4 font-semibold text-[#7183a0] text-xs uppercase tracking-widest">
                      Scheme identity
                    </th>
                    <th className="text-center px-4 py-4 font-semibold text-white">
                      {fundA.schemeName.split(' ').slice(0, 3).join(' ')}
                    </th>
                    <th className="text-center px-4 py-4 font-semibold text-white">
                      {fundB.schemeName.split(' ').slice(0, 3).join(' ')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <MetricRow label="Fund house" a={fundA.amcName} b={fundB.amcName} />
                  <MetricRow label="AMFI scheme code" a={String(fundA.schemeCode)} b={String(fundB.schemeCode)} />
                  <MetricRow label="SEBI category" a={fundA.category} b={fundB.category} />
                  <MetricRow label="Benchmark" a={fundA.benchmark} b={fundB.benchmark} />
                  <MetricRow label="Plan" a={`${fundA.plan} · ${fundA.option}`} b={`${fundB.plan} · ${fundB.option}`} />
                </tbody>
              </table>
            </div>

            <div className="rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 mb-6 text-xs leading-6 text-[#7183a0]">
              <p>
                {fundA.category === fundB.category ? (
                  <>
                    Both schemes sit in the same SEBI category ({fundA.category}), so they draw from a
                    comparable universe and the comparison turns on manager selection, concentration and
                    cost rather than on mandate.
                  </>
                ) : (
                  <>
                    These schemes sit in different SEBI categories — {fundA.schemeName} is {fundA.category}{' '}
                    and {fundB.schemeName} is {fundB.category} — so they are held to different mandates.
                    Read return differences against each fund&apos;s own benchmark, not against each other.
                  </>
                )}{' '}
                {fundA.benchmark === fundB.benchmark ? (
                  <>Both are benchmarked to {fundA.benchmark}, so relative alpha is directly comparable.</>
                ) : (
                  <>
                    They benchmark against different indices ({fundA.benchmark} and {fundB.benchmark}),
                    so alpha figures are not directly comparable between the two.
                  </>
                )}
              </p>
            </div>

            <div className="rounded-xl border border-[#66a3ff]/20 bg-[#66a3ff]/[0.04] px-6 py-6 mb-8 text-center">
            <p className="font-semibold text-white mb-2">Live performance metrics</p>
            <p className="text-sm text-[#7183a0] max-w-lg mx-auto mb-5">
              NAV, CAGR, Sharpe ratio, drawdown and portfolio overlap for this pair are computed on
              demand from AMFI history in the FundersAI workspace.
            </p>
            <Link
              rel="nofollow"
              href={`/dashboard?query=Compare ${fundA.schemeName} and ${fundB.schemeName}`}
              className="inline-flex items-center gap-2 rounded-full border border-[#66a3ff]/30 bg-[#66a3ff]/10 px-5 py-2.5 text-sm font-semibold text-[#66a3ff] hover:bg-[#66a3ff]/20 transition-colors"
            >
              Run this comparison →
            </Link>
            </div>
          </>
        )}

        {/* Live analysis CTA */}
        <div className="text-center mb-12">
          <Link
            rel="nofollow"
            href={`/dashboard?query=Compare ${fundA.schemeName} and ${fundB.schemeName} with full metrics`}
            className="inline-flex items-center gap-2 rounded-full border border-[#00FF9D]/30 bg-[#00FF9D]/[0.08] px-6 py-3 text-sm font-bold text-[#00FF9D] hover:bg-[#00FF9D]/[0.15] transition-colors"
          >
            Run live comparison in workspace →
          </Link>
        </div>

        {/* Other comparisons */}
        <section>
          <h2 className="text-base font-bold text-white mb-4">Other comparisons</h2>
          <div className="flex flex-wrap gap-2">
            {COMPARE_PAIRS.filter((p) => p.pair !== pair).map((p) => {
              const fA = getFundBySlug(p.amcSlugA, p.fundSlugA);
              const fB = getFundBySlug(p.amcSlugB, p.fundSlugB);
              if (!fA || !fB) return null;
              return (
                <Link
                  key={p.pair}
                  href={`/compare/${p.pair}`}
                  className="rounded-full border border-white/10 bg-white/[0.02] px-3.5 py-1.5 text-xs font-medium text-[#7183a0] transition hover:border-white/20 hover:text-white"
                >
                  {fA.schemeName.split(' ')[0]} vs {fB.schemeName.split(' ')[0]}
                </Link>
              );
            })}
          </div>
        </section>

        {/* Disclosure */}
        <div className="mt-10 rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 text-xs text-[#7183a0]">
          <p>
            <span className="font-semibold text-white/60">Research only. </span>
            This comparison is for informational purposes. FundersAI does not provide investment advice or
            recommendations. Past performance is not indicative of future results. Verify all data with official
            AMFI sources before any financial decision.{' '}
            <Link href="/methodology" className="text-[#82aff6] hover:text-[#b8d3ff]">Methodology →</Link>
          </p>
        </div>

        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
