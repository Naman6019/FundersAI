import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import {
  AMC_REGISTRY,
  getAmcBySlug,
  getFundsByAmc,
} from '@/lib/fund-registry';

type Props = { params: Promise<{ amcSlug: string }> };

export async function generateStaticParams() {
  return AMC_REGISTRY.map((amc) => ({ amcSlug: amc.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { amcSlug } = await params;
  const amc = getAmcBySlug(amcSlug);
  if (!amc) return { title: 'AMC Not Found | FundersAI' };
  const canonicalUrl = `https://www.fundersai.co.in/mutual-funds/${amcSlug}`;
  return {
    title: `${amc.name} Mutual Funds | FundersAI`,
    description: `Research ${amc.name} mutual funds. Deterministic metrics from official sources — NAV history, CAGR, Sharpe ratio, expense ratio, and portfolio holdings for ${amc.shortName} schemes.`,
    alternates: {
      canonical: canonicalUrl,
    },
    openGraph: {
      title: `${amc.name} Mutual Funds | FundersAI`,
      description: `Research ${amc.name} mutual funds with deterministic metrics from AMFI and official AMC disclosures.`,
      url: canonicalUrl,
    },
  };
}

const CATEGORY_COLORS: Record<string, string> = {
  'Flexi Cap': 'bg-[#00FF9D]/10 text-[#00FF9D] border-[#00FF9D]/20',
  'Large Cap': 'bg-[#66a3ff]/10 text-[#66a3ff] border-[#66a3ff]/20',
  'Mid Cap': 'bg-purple-400/10 text-purple-300 border-purple-400/20',
  'Small Cap': 'bg-amber-400/10 text-amber-300 border-amber-400/20',
  'Large & Mid Cap': 'bg-teal-400/10 text-teal-300 border-teal-400/20',
  'ELSS': 'bg-rose-400/10 text-rose-300 border-rose-400/20',
  'Index Fund': 'bg-sky-400/10 text-sky-300 border-sky-400/20',
  'Sectoral/Thematic': 'bg-orange-400/10 text-orange-300 border-orange-400/20',
};

function CategoryBadge({ category }: { category: string }) {
  const cls = CATEGORY_COLORS[category] ?? 'bg-white/10 text-[#aebed6] border-white/10';
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${cls}`}>
      {category}
    </span>
  );
}

export default async function AmcPage({ params }: Props) {
  const { amcSlug } = await params;
  const amc = getAmcBySlug(amcSlug);
  if (!amc) notFound();

  const funds = getFundsByAmc(amcSlug);
  const allAmcs = AMC_REGISTRY.filter((a) => a.slug !== amcSlug);

  return (
    <main className="min-h-dvh bg-[#070b12] text-[#dce8fa]">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#070b12]/90 backdrop-blur-md sticky top-0 z-30">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/mutual-funds" className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            ← Mutual Funds
          </Link>
          <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#7183a0]">{amc.shortName}</span>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
        {/* Hero */}
        <div className="mb-12">
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#00FF9D]/70 mb-3">AMC</p>
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl mb-4">{amc.name}</h1>
          <p className="text-base leading-7 text-[#aebed6] max-w-2xl">{amc.description}</p>
        </div>

        {/* Fund cards */}
        {funds.length > 0 ? (
          <section className="mb-16">
            <div className="flex items-baseline justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Indexed funds</h2>
              <span className="text-xs text-[#7183a0]">{funds.length} fund{funds.length !== 1 ? 's' : ''}</span>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {funds.map((fund) => (
                <Link
                  key={fund.fundSlug}
                  href={`/mutual-funds/${fund.amcSlug}/${fund.fundSlug}`}
                  className="group flex flex-col rounded-2xl border border-white/10 bg-white/[0.025] p-6 transition hover:border-white/20 hover:bg-white/[0.04]"
                >
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <h3 className="text-base font-bold text-white group-hover:text-[#00FF9D] transition-colors leading-snug">
                      {fund.schemeName}
                    </h3>
                    <CategoryBadge category={fund.category} />
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#7183a0] mb-4">
                    <span>{fund.plan} · {fund.option}</span>
                    <span>Benchmark: {fund.benchmark}</span>
                    <span>AMFI: {fund.schemeCode}</span>
                  </div>
                  <span className="mt-auto text-xs font-semibold text-[#82aff6] group-hover:text-[#b8d3ff] transition-colors">
                    View metrics →
                  </span>
                </Link>
              ))}
            </div>
          </section>
        ) : (
          <div className="mb-16 rounded-xl border border-white/10 bg-white/[0.02] px-6 py-8 text-center">
            <p className="text-[#7183a0] text-sm">
              No funds indexed for {amc.name} yet. Use the{' '}
              <Link href="/dashboard" className="text-[#82aff6] hover:text-[#b8d3ff]">workspace</Link>{' '}
              to search all schemes.
            </p>
          </div>
        )}

        {/* Other AMCs */}
        <section className="mb-12">
          <h2 className="text-lg font-bold text-white mb-4">Other AMCs</h2>
          <div className="flex flex-wrap gap-2">
            {allAmcs.map((a) => (
              <Link
                key={a.slug}
                href={`/mutual-funds/${a.slug}`}
                className="rounded-full border border-white/10 bg-white/[0.02] px-3.5 py-1.5 text-xs font-semibold text-[#7183a0] transition hover:border-white/20 hover:text-white"
              >
                {a.shortName}
              </Link>
            ))}
          </div>
        </section>

        {/* Disclosure */}
        <div className="rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 text-xs text-[#7183a0]">
          <p>
            <span className="font-semibold text-white/60">Coverage note: </span>
            This page shows funds from {amc.name} that are currently indexed in FundersAI. Coverage is partial —
            not every scheme offered by this AMC is listed here. For full scheme search, use the workspace.
            Data sourced from AMFI and official AMC disclosures. Last updated July 2026.
            FundersAI does not provide investment advice.
          </p>
        </div>

        <div className="mt-8 flex flex-wrap gap-4 border-t border-white/10 pt-6 text-sm">
          <Link href="/mutual-funds" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">All AMCs</Link>
          <Link href="/methodology" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">Methodology</Link>
          <Link href="/dashboard" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">Open workspace</Link>
        </div>
      </div>
    </main>
  );
}
