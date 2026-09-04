import type { Metadata } from 'next';
import Link from 'next/link';
import { COMPARE_PAIRS, getFundBySlug } from '@/lib/fund-registry';
import { CompareIndexJsonLd } from '@/components/seo/JsonLd';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';

export const metadata: Metadata = {
  title: 'Mutual Fund Comparisons — Head-to-Head Analysis | FundersAI',
  description:
    'Side-by-side comparisons of Indian mutual funds: 1Y/3Y/5Y CAGR, Sharpe ratio, max drawdown, expense ratio, AUM, and portfolio overlap — all from official AMC disclosures.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/compare',
  },
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Mutual Fund Comparisons — Head-to-Head Analysis | FundersAI',
    description:
      'Compare Indian mutual funds side by side on deterministic risk and return metrics sourced from official AMC factsheets.',
    url: 'https://www.fundersai.co.in/compare',
  },
};

/**
 * The hub for /compare/[pair]. Every pair rendered here is a real curated page — the
 * detail route 404s anything outside COMPARE_PAIRS, so this list is built from the same
 * registry rather than from arbitrary fund combinations.
 */
export default function CompareIndexPage() {
  const comparisons = COMPARE_PAIRS.map((cp) => {
    const fundA = getFundBySlug(cp.amcSlugA, cp.fundSlugA);
    const fundB = getFundBySlug(cp.amcSlugB, cp.fundSlugB);
    if (!fundA || !fundB) return null;
    return { pair: cp.pair, fundA, fundB };
  }).filter((c): c is NonNullable<typeof c> => c !== null);

  return (
    <div className="min-h-dvh bg-background text-foreground flex flex-col justify-between">
      <CompareIndexJsonLd
        comparisons={comparisons.map((c) => ({
          pair: c.pair,
          nameA: c.fundA.schemeName,
          nameB: c.fundB.schemeName,
        }))}
      />
      <EcosystemHeader currentApp="tools" />

      <main className="flex-1">
        <div className="mx-auto max-w-5xl px-5 py-12 sm:px-8">

          {/* Hero */}
          <div className="mb-12 max-w-2xl">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-primary mb-4 font-mono">
              Head-to-Head
            </p>
            <h1 className="text-2xl sm:text-3xl font-bold font-serif-display tracking-tight text-white mb-4">
              Mutual Fund Comparisons
            </h1>
            <p className="text-sm leading-7 text-text-3">
              Each comparison puts two schemes side by side on the metrics that actually separate them —
              1Y/3Y/5Y CAGR, Sharpe ratio, maximum drawdown, expense ratio, AUM, and portfolio overlap.
              Every figure is computed deterministically from AMFI NAV histories and official AMC
              disclosures, never estimated.
            </p>
          </div>

          {/* Comparison list */}
          <section className="mb-14">
            <h2 className="text-base font-bold text-white mb-4">Available comparisons</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {comparisons.map(({ pair, fundA, fundB }) => (
                <Link
                  key={pair}
                  href={`/compare/${pair}`}
                  className="group rounded-2xl border border-white/10 bg-white/[0.025] p-5 transition hover:border-[#00FF9D]/30 hover:bg-white/[0.04]"
                >
                  <p className="text-[10px] font-bold uppercase tracking-widest text-[#7183a0] mb-3">
                    {fundA.category}
                  </p>
                  <h3 className="text-sm font-bold leading-snug text-white mb-1">
                    {fundA.schemeName}
                    <span className="mx-2 font-normal text-[#7183a0]">vs</span>
                    {fundB.schemeName}
                  </h3>
                  <p className="text-xs text-[#7183a0]">
                    {fundA.amcName} · {fundB.amcName}
                  </p>
                  <span className="mt-4 inline-block text-xs font-semibold text-[#82aff6] group-hover:text-[#b8d3ff]">
                    View comparison →
                  </span>
                </Link>
              ))}
            </div>
          </section>

          {/* Adjacent surfaces — keeps the hub from being a dead end */}
          <section className="mb-12">
            <h2 className="text-base font-bold text-white mb-4">Compare a pair that isn&apos;t listed</h2>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/tools/portfolio-overlap"
                className="rounded-full border border-white/10 bg-white/[0.02] px-3.5 py-1.5 text-xs font-medium text-[#7183a0] transition hover:border-white/20 hover:text-white"
              >
                Portfolio Overlap Calculator →
              </Link>
              <Link
                href="/mutual-funds"
                className="rounded-full border border-white/10 bg-white/[0.02] px-3.5 py-1.5 text-xs font-medium text-[#7183a0] transition hover:border-white/20 hover:text-white"
              >
                Browse all funds →
              </Link>
              <Link
                rel="nofollow"
                href="/dashboard?query=Compare two mutual funds with full metrics"
                className="rounded-full border border-[#00FF9D]/20 bg-[#00FF9D]/[0.06] px-3.5 py-1.5 text-xs font-semibold text-[#00FF9D] transition hover:bg-[#00FF9D]/[0.12]"
              >
                Run a custom comparison in the workspace →
              </Link>
            </div>
          </section>

          {/* Disclosure */}
          <div className="rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 text-xs text-[#7183a0]">
            <p>
              <span className="font-semibold text-white/60">Research only. </span>
              These comparisons are for informational purposes. FundersAI does not provide investment
              advice or recommendations. Past performance is not indicative of future results. Verify all
              data with official AMFI sources before any financial decision.{' '}
              <Link href="/methodology" className="text-[#82aff6] hover:text-[#b8d3ff]">
                Methodology →
              </Link>
            </p>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
