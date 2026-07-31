import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import {
  FUND_REGISTRY,
  getFundBySlug,
  getAmcBySlug,
  getFundsByAmc,
} from '@/lib/fund-registry';

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
  return {
    title: `${fund.schemeName} – NAV, Returns & Metrics | FundersAI`,
    description: `${fund.schemeName} (${fund.plan} ${fund.option}): NAV, 1Y/3Y/5Y CAGR, Sharpe ratio, expense ratio, benchmark vs ${fund.benchmark}, and portfolio holdings. Deterministic metrics from official AMC sources.`,
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

function ReturnCard({ period, value, accent }: { period: string; value: string; accent?: boolean }) {
  return (
    <div className={`rounded-xl px-3 py-3 text-center border ${accent ? 'bg-[#00FF9D]/[0.07] border-[#00FF9D]/20' : 'bg-white/[0.02] border-white/10'}`}>
      <p className={`text-[10px] font-bold uppercase tracking-widest mb-1 ${accent ? 'text-[#00FF9D]/70' : 'text-[#7183a0]'}`}>{period}</p>
      <p className={`text-2xl font-bold ${accent ? 'text-[#00FF9D]' : 'text-white'}`}>{value}</p>
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
// Shown while the live API data loads on the client.
// Keeps the page useful even if the backend is unavailable.

function StaticFundDisplay({ fund }: { fund: ReturnType<typeof getFundBySlug> & {} }) {
  // These are illustrative placeholders — clearly dated and labelled.
  // The client-side fetch will replace them with live API data when available.
  const placeholderReturns = [
    { period: '1Y', value: '—' },
    { period: '3Y', value: '—' },
    { period: '5Y', value: '—' },
  ];

  const otherFunds = getFundsByAmc(fund.amcSlug).filter((f) => f.fundSlug !== fund.fundSlug);

  return (
    <div className="space-y-14">
      {/* Overview */}
      <section>
        <SectionHead label="Overview" title="Fund details" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <StatCard label="AMC" value={fund.amcName.split(' ')[0]} />
          <StatCard label="Category" value={fund.category} />
          <StatCard label="Plan" value={fund.plan} />
          <StatCard label="Option" value={fund.option} />
          <StatCard label="Benchmark" value={fund.benchmark} sub="vs this index" />
          <StatCard label="AMFI Code" value={fund.schemeCode.toString()} />
        </div>
      </section>

      {/* Live-data notice */}
      <section className="rounded-xl border border-[#66a3ff]/20 bg-[#66a3ff]/[0.04] px-5 py-5">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-[#66a3ff]/60" />
          <div>
            <p className="font-semibold text-white text-sm mb-1">Live metrics require workspace access</p>
            <p className="text-xs leading-6 text-[#7183a0]">
              NAV, CAGR, Sharpe ratio, max drawdown, expense ratio, AUM, and portfolio holdings are fetched
              live from AMFI and official AMC sources. Open the workspace to run a full analysis of this fund.
            </p>
            <Link
              href={`/dashboard?query=Give me a full analysis of ${fund.schemeName}`}
              className="inline-flex mt-3 items-center gap-1.5 rounded-full bg-[#66a3ff]/10 border border-[#66a3ff]/20 px-4 py-2 text-xs font-semibold text-[#66a3ff] hover:bg-[#66a3ff]/20 transition-colors"
            >
              Analyse in workspace →
            </Link>
          </div>
        </div>
      </section>

      {/* Return preview (static skeleton) */}
      <section>
        <SectionHead label="Performance" title="Returns (CAGR)" />
        <div className="grid grid-cols-3 gap-3 mb-4">
          {placeholderReturns.map(({ period, value }) => (
            <ReturnCard key={period} period={period} value={value} accent={true} />
          ))}
        </div>
        <p className="text-xs text-[#7183a0]">
          Returns require a live backend connection. Open the workspace for calculated values.
        </p>
      </section>

      {/* Methodology */}
      <section>
        <SectionHead label="How it works" title="Data sources for this fund" />
        <div className="grid sm:grid-cols-2 gap-3">
          {[
            { label: 'NAV history', desc: 'Daily NAV from AMFI via MFapi, updated each business day.' },
            { label: 'Expense ratio', desc: `Official ${fund.amcName} factsheet.` },
            { label: 'Portfolio holdings', desc: `Monthly AMC disclosure. SEBI mandates filing within 10 business days of month-end.` },
            { label: 'Benchmark', desc: `${fund.benchmark} — as declared in the fund's SID/Factsheet.` },
          ].map((item) => (
            <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-4">
              <p className="font-semibold text-white text-sm mb-1">{item.label}</p>
              <p className="text-xs leading-5 text-[#7183a0]">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Compare CTA */}
      <section className="rounded-xl border border-white/10 bg-white/[0.02] px-5 py-5">
        <p className="font-semibold text-white mb-2">Compare with another fund</p>
        <p className="text-xs text-[#7183a0] mb-4">
          FundersAI can compare {fund.schemeName} against any fund in the registry — or any AMFI scheme code.
        </p>
        <div className="flex flex-wrap gap-2">
          {fund.category === 'Flexi Cap' && (
            <Link
              href={`/compare/hdfc-flexi-cap-fund-vs-parag-parikh-flexi-cap-fund`}
              className="text-xs font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors rounded-full border border-[#82aff6]/20 px-3 py-1.5"
            >
              HDFC Flexi Cap vs PPFAS →
            </Link>
          )}
          <Link
            href={`/dashboard?query=Compare ${fund.schemeName} with its benchmark ${fund.benchmark}`}
            className="text-xs font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors rounded-full border border-[#82aff6]/20 px-3 py-1.5"
          >
            vs benchmark →
          </Link>
          <Link
            href={`/dashboard?query=Analyse ${fund.schemeName}`}
            className="text-xs font-semibold text-[#00FF9D] hover:text-[#66ffba] transition-colors rounded-full border border-[#00FF9D]/20 bg-[#00FF9D]/[0.06] px-3 py-1.5"
          >
            Full analysis in workspace →
          </Link>
        </div>
      </section>

      {/* Other funds from same AMC */}
      {otherFunds.length > 0 && (
        <section>
          <h2 className="text-lg font-bold text-white mb-4">More from {fund.amcName.split(' ')[0]}</h2>
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
          <Link href="/mutual-funds" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">All funds</Link>
          <Link href={`/mutual-funds/${amcSlug}`} className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">{amc?.name}</Link>
          <Link href="/methodology" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">Methodology</Link>
        </div>
      </div>
    </main>
  );
}
