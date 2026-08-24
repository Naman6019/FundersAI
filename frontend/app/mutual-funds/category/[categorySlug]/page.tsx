import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import {
  CATEGORY_LIST,
  categorySlug,
  getCategoryBySlug,
  getFundsByCategory,
} from '@/lib/fund-registry';
import { CategoryJsonLd } from '@/components/seo/JsonLd';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';

type Props = { params: Promise<{ categorySlug: string }> };

export async function generateStaticParams() {
  return CATEGORY_LIST.map((cat) => ({ categorySlug: categorySlug(cat) }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { categorySlug: slug } = await params;
  const category = getCategoryBySlug(slug);
  if (!category) return { title: 'Category Not Found | FundersAI' };
  const canonicalUrl = `https://www.fundersai.co.in/mutual-funds/category/${slug}`;
  return {
    title: `${category} Mutual Funds | FundersAI`,
    description: `Research ${category} mutual funds available in India. Deterministic metrics from official sources — NAV history, CAGR, Sharpe ratio, expense ratio, and portfolio holdings.`,
    alternates: {
      canonical: canonicalUrl,
    },
    openGraph: {
      title: `${category} Mutual Funds | FundersAI`,
      description: `Explore ${category} mutual funds with verified NAV and risk-adjusted metrics.`,
      url: canonicalUrl,
    },
  };
}

export default async function CategoryPage({ params }: Props) {
  const { categorySlug: slug } = await params;
  const category = getCategoryBySlug(slug);
  if (!category) notFound();

  const funds = getFundsByCategory(category);
  const otherCategories = CATEGORY_LIST.filter((cat) => cat !== category);

  return (
    <div className="min-h-dvh bg-[#070b12] text-[#dce8fa] flex flex-col justify-between">
      <CategoryJsonLd category={category} categorySlug={slug} fundCount={funds.length} />
      <EcosystemHeader currentApp="mutual-funds" />

      <main className="flex-1">
        <div className="mx-auto max-w-6xl px-5 py-12 sm:px-8">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-xs font-mono text-[#7183a0] mb-8">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <span>/</span>
            <Link href="/mutual-funds" className="hover:text-white transition-colors">Mutual Funds</Link>
            <span>/</span>
            <span className="text-[#00FF9D]">{category}</span>
          </div>
        {/* Hero */}
        <div className="mb-12">
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#00FF9D]/70 mb-3">SEBI Category</p>
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl mb-4">{category} Funds</h1>
          <p className="text-base leading-7 text-[#aebed6] max-w-2xl">
            Indian mutual funds in the {category} category, indexed from AMFI and official AMC sources.
          </p>
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
                    <span className="inline-flex items-center rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#aebed6] whitespace-nowrap">
                      {fund.amcName.replace(' Mutual Fund', '')}
                    </span>
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
              No {category} funds indexed yet. Use the{' '}
              <Link href="/dashboard" className="text-[#82aff6] hover:text-[#b8d3ff]">workspace</Link>{' '}
              to search all schemes.
            </p>
          </div>
        )}

        {/* Other categories */}
        <section className="mb-12">
          <h2 className="text-lg font-bold text-white mb-4">Other categories</h2>
          <div className="flex flex-wrap gap-2">
            {otherCategories.map((cat) => (
              <Link
                key={cat}
                href={`/mutual-funds/category/${categorySlug(cat)}`}
                className="rounded-full border border-white/10 bg-white/[0.02] px-3.5 py-1.5 text-xs font-semibold text-[#7183a0] transition hover:border-white/20 hover:text-white"
              >
                {cat}
              </Link>
            ))}
          </div>
        </section>

        {/* Disclosure */}
        <div className="rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 text-xs text-[#7183a0]">
          <p>
            <span className="font-semibold text-white/60">Coverage note: </span>
            This page shows {category} funds currently indexed in FundersAI. Coverage is partial —
            not every scheme in this SEBI category is listed here. For full scheme search, use the workspace.
            Data sourced from AMFI and official AMC disclosures. Last updated July 2026.
            FundersAI does not provide investment advice.
          </p>
        </div>

        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
