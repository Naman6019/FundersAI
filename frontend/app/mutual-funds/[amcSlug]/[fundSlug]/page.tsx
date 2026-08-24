import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import {
  FUND_REGISTRY,
  getFundBySlug,
  getAmcBySlug,
  getFundsByAmc,
  getFundsByCategory,
} from '@/lib/fund-registry';
import { FundJsonLd } from '@/components/seo/JsonLd';

type Props = { params: Promise<{ amcSlug: string; fundSlug: string }> };

export async function generateStaticParams() {
  return FUND_REGISTRY.map((f) => ({
    amcSlug: f.amcSlug,
    fundSlug: f.fundSlug,
  }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { amcSlug, fundSlug } = await params;
  const fund = getFundBySlug(amcSlug, fundSlug);
  if (!fund) return { title: 'Fund Not Found | FundersAI' };
  const canonicalUrl = `https://www.fundersai.co.in/mutual-funds/${amcSlug}/${fundSlug}`;
  return {
    title: `${fund.schemeName} – NAV, Returns & Metrics | FundersAI`,
    description: `${fund.schemeName} (${fund.plan} ${fund.option}): NAV, 1Y/3Y/5Y CAGR, Sharpe ratio, expense ratio, benchmark vs ${fund.benchmark}, and portfolio holdings. Deterministic metrics from official AMC sources.`,
    alternates: {
      canonical: canonicalUrl,
    },
    openGraph: {
      title: `${fund.schemeName} – NAV, Returns & Risk Metrics | FundersAI`,
      description: `Analyze ${fund.schemeName} (${fund.category}, ${fund.plan} plan) with verified NAV and benchmark comparisons against ${fund.benchmark}.`,
      url: canonicalUrl,
    },
  };
}

// ─── Stat helpers ────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.025] px-4 py-4 text-center">
      <p className="text-[10px] font-bold uppercase tracking-widest text-[#7183a0] mb-1">{label}</p>
      <p className="text-xl font-bold text-white">{value}</p>
      {sub && <p className="text-[10px] text-[#7183a0] mt-0.5">{sub}</p>}
    </div>
  );
}

function SectionHead({ label, title }: { label: string; title: string }) {
  return (
    <div className="mb-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#00FF9D]/60 mb-1">{label}</p>
      <h2 className="text-xl font-bold text-white">{title}</h2>
    </div>
  );
}

// ─── Static fallback display data ────────────────────────────────────────────
// Pre-renders rich semantic content for crawlers & users while live metrics stream in.

function StaticFundDisplay({ fund }: { fund: ReturnType<typeof getFundBySlug> & {} }) {
  const otherFunds = getFundsByAmc(fund.amcSlug).filter((f) => f.fundSlug !== fund.fundSlug);
  const categoryFunds = getFundsByCategory(fund.category).filter((f) => f.fundSlug !== fund.fundSlug);

  return (
    <div className="space-y-14">
      {/* Overview */}
      <section>
        <SectionHead label="Overview" title="Fund details & classification" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <StatCard label="AMC" value={fund.amcName.split(' ')[0]} />
          <StatCard label="Category" value={fund.category} />
          <StatCard label="Plan" value={fund.plan} />
          <StatCard label="Option" value={fund.option} />
          <StatCard label="Benchmark" value={fund.benchmark} sub="vs this index" />
          <StatCard label="AMFI Code" value={fund.schemeCode.toString()} />
        </div>
      </section>

      {/* Fund Mandate & Profile */}
      <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
        <SectionHead label="Investment Mandate" title={`About ${fund.schemeName}`} />
        <div className="space-y-4 text-sm leading-7 text-[#aebed6]">
          <p>
            <strong className="text-white">{fund.schemeName}</strong> is an open-ended equity scheme falling under the SEBI-defined <strong className="text-[#00FF9D]">{fund.category}</strong> category. It is managed by {fund.amcName} and designed for investors seeking long-term capital appreciation by tracking and outperforming its primary benchmark, <span className="text-white">{fund.benchmark}</span>.
          </p>
          <div className="grid sm:grid-cols-3 gap-4 pt-2">
            <div className="rounded-xl border border-white/5 bg-white/[0.015] p-4">
              <p className="text-xs font-semibold text-white mb-1">Direct Plan Advantage</p>
              <p className="text-xs text-[#7183a0]">Zero distributor commissions charged. Savings are added directly to daily NAV compound growth.</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-white/[0.015] p-4">
              <p className="text-xs font-semibold text-white mb-1">Benchmark Standard</p>
              <p className="text-xs text-[#7183a0]">Compared against {fund.benchmark} Total Return Index (TRI) to measure true active Alpha generation.</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-white/[0.015] p-4">
              <p className="text-xs font-semibold text-white mb-1">AMFI Verification</p>
              <p className="text-xs text-[#7183a0]">Official NAV data updated each business evening under AMFI Code {fund.schemeCode}.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Live-data CTA notice */}
      <section className="rounded-xl border border-[#66a3ff]/20 bg-[#66a3ff]/[0.04] px-5 py-5">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-[#66a3ff]/60" />
          <div>
            <p className="font-semibold text-white text-sm mb-1">Live Quantitative Metrics & Overlap in Workspace</p>
            <p className="text-xs leading-6 text-[#7183a0]">
              Calculated 1Y/3Y/5Y CAGR, Sharpe ratio, Sortino, Maximum Drawdown, monthly portfolio sector weights, and stock holdings are fetched directly from official AMFI and AMC disclosures.
            </p>
            <Link
              href={`/dashboard?query=Give me a full quantitative analysis of ${fund.schemeName} vs ${fund.benchmark}`}
              className="inline-flex mt-3 items-center gap-1.5 rounded-full bg-[#66a3ff]/10 border border-[#66a3ff]/20 px-4 py-2 text-xs font-semibold text-[#66a3ff] hover:bg-[#66a3ff]/20 transition-colors"
            >
              Run live analysis in workspace →
            </Link>
          </div>
        </div>
      </section>

      {/* Methodology */}
      <section>
        <SectionHead label="Transparency" title="Data sources & verification" />
        <div className="grid sm:grid-cols-2 gap-3">
          {[
            { label: 'NAV history', desc: 'Daily NAV fetched directly from AMFI via MFapi, updated every business evening.' },
            { label: 'Expense ratio', desc: `Published in official ${fund.amcName} monthly disclosures and SID.` },
            { label: 'Portfolio holdings', desc: `Monthly AMC disclosures mandated by SEBI within 10 business days of month-end.` },
            { label: 'Benchmark', desc: `${fund.benchmark} — as declared in the official Scheme Information Document.` },
          ].map((item) => (
            <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-4">
              <p className="font-semibold text-white text-sm mb-1">{item.label}</p>
              <p className="text-xs leading-5 text-[#7183a0]">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Frequently Asked Questions */}
      <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
        <SectionHead label="FAQ" title={`Frequently Asked Questions: ${fund.schemeName}`} />
        <div className="space-y-5 text-sm">
          <div className="border-b border-white/5 pb-4">
            <h3 className="font-semibold text-white mb-1">What is the AMFI Scheme Code for {fund.schemeName}?</h3>
            <p className="text-xs leading-6 text-[#7183a0]">
              The official AMFI Scheme Code for {fund.schemeName} ({fund.plan} {fund.option}) is <code className="text-[#00FF9D]">{fund.schemeCode}</code>. This code is used to fetch official daily Net Asset Value (NAV) updates.
            </p>
          </div>
          <div className="border-b border-white/5 pb-4">
            <h3 className="font-semibold text-white mb-1">What is the benchmark index for this fund?</h3>
            <p className="text-xs leading-6 text-[#7183a0]">
              This fund benchmarks its performance against {fund.benchmark}. FundersAI measures active alpha and beta relative to this index Total Return Index (TRI).
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-white mb-1">Why invest in the Direct Plan over Regular Plan?</h3>
            <p className="text-xs leading-6 text-[#7183a0]">
              Direct plans do not pay intermediary distribution commissions, resulting in a lower expense ratio and higher compounding net returns for the investor over long investment horizons.
            </p>
          </div>
        </div>
      </section>

      {/* Compare CTA & Category Links */}
      <section className="rounded-xl border border-white/10 bg-white/[0.02] px-5 py-5">
        <p className="font-semibold text-white mb-2">Compare {fund.schemeName} against category peers</p>
        <p className="text-xs text-[#7183a0] mb-4">
          Compare risk-adjusted returns, Sharpe ratios, and portfolio overlap with other {fund.category} funds:
        </p>
        <div className="flex flex-wrap gap-2">
          {categoryFunds.slice(0, 4).map((cf) => (
            <Link
              key={cf.fundSlug}
              href={`/compare/${fund.fundSlug}-vs-${cf.fundSlug}`}
              className="text-xs font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors rounded-full border border-[#82aff6]/20 px-3 py-1.5"
            >
              vs {cf.schemeName.split(' ')[0]} {cf.category} →
            </Link>
          ))}
          <Link
            href={`/dashboard?query=Compare ${fund.schemeName} with its benchmark ${fund.benchmark}`}
            className="text-xs font-semibold text-[#00FF9D] hover:text-[#66ffba] transition-colors rounded-full border border-[#00FF9D]/20 bg-[#00FF9D]/[0.06] px-3 py-1.5"
          >
            Full comparison in workspace →
          </Link>
        </div>
      </section>

      {/* Other funds from same AMC */}
      {otherFunds.length > 0 && (
        <section>
          <h2 className="text-lg font-bold text-white mb-4">More funds from {fund.amcName}</h2>
          <div className="flex flex-wrap gap-2">
            {otherFunds.map((f) => (
              <Link
                key={f.fundSlug}
                href={`/mutual-funds/${f.amcSlug}/${f.fundSlug}`}
                className="rounded-full border border-white/10 bg-white/[0.02] px-3.5 py-1.5 text-xs font-medium text-[#7183a0] transition hover:border-white/20 hover:text-white"
              >
                {f.schemeName}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default async function FundDetailPage({ params }: Props) {
  const { amcSlug, fundSlug } = await params;
  const fund = getFundBySlug(amcSlug, fundSlug);
  if (!fund) notFound();

  const amc = getAmcBySlug(amcSlug);

  return (
    <>
      <FundJsonLd fund={fund} amc={amc} />
      <main className="min-h-dvh bg-[#070b12] text-[#dce8fa]">
        {/* Header */}
        <div className="border-b border-white/10 bg-[#070b12]/90 backdrop-blur-md sticky top-0 z-30">
          <div className="mx-auto flex max-w-6xl items-center gap-4 px-5 py-4 sm:px-8">
            <Link href={`/mutual-funds/${amcSlug}`} className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors shrink-0">
              ← {amc?.shortName ?? amcSlug}
            </Link>
            <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#7183a0] truncate hidden sm:block">
              {fund.schemeName}
            </span>
          </div>
        </div>

        <div className="mx-auto max-w-5xl px-5 py-16 sm:px-8">
          {/* Hero */}
          <div className="mb-12">
            <div className="flex flex-wrap gap-2 mb-4">
              <span className="inline-flex items-center rounded-full border border-[#00FF9D]/20 bg-[#00FF9D]/[0.08] px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#00FF9D]">
                {fund.category}
              </span>
              <span className="inline-flex items-center rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#7183a0]">
                {fund.plan} · {fund.option}
              </span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl mb-3">{fund.schemeName}</h1>
            <p className="text-sm text-[#7183a0]">
              {fund.amcName} · AMFI scheme code {fund.schemeCode} · Benchmark: {fund.benchmark}
            </p>
          </div>

          <StaticFundDisplay fund={fund} />

          {/* Disclosure */}
          <div className="mt-14 rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 text-xs text-[#7183a0]">
            <p>
              <span className="font-semibold text-white/60">Research only. </span>
              This page provides reference data for {fund.schemeName}. Nothing here constitutes personalised
              investment advice. CAGR, Sharpe, and other performance metrics shown in the workspace are calculated
              deterministically from AMFI NAV data. Past performance is not a guarantee of future returns.
              Verify all data with official AMFI sources before any decision.{' '}
              <Link href="/methodology" className="text-[#82aff6] hover:text-[#b8d3ff]">Full methodology →</Link>
            </p>
          </div>

          <div className="mt-8 flex flex-wrap gap-4 border-t border-white/10 pt-6 text-sm">
            <Link href="/mutual-funds" className="text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
              ← All mutual funds
            </Link>
            <span className="text-white/20">|</span>
            <Link href={`/mutual-funds/${amcSlug}`} className="text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
              More {amc?.shortName ?? amcSlug} funds
            </Link>
            <span className="text-white/20">|</span>
            <Link href="/methodology" className="text-[#7183a0] hover:text-white transition-colors">
              Methodology
            </Link>
            <span className="text-white/20">|</span>
            <Link href="/privacy" className="text-[#7183a0] hover:text-white transition-colors">
              Privacy
            </Link>
          </div>
        </div>
      </main>
    </>
  );
}
