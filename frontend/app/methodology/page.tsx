import type { Metadata } from 'next';
import Link from 'next/link';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import { MagicCard } from '@/components/ui/magic-card';

export const metadata: Metadata = {
  title: 'Methodology Hub & Standards | FundersAI',
  description:
    'How FundersAI sources data, calculates metrics, handles missing fields, and separates deterministic analysis from AI summaries. Full transparency on data freshness, formulas, and guardrails.',
  keywords: [
    'FundersAI methodology',
    'Indian mutual fund calculation standards',
    'Deterministic quantitative finance AI',
    'AMC factsheet parser methodology',
  ],
  alternates: {
    canonical: 'https://www.fundersai.co.in/methodology',
  },
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Methodology Hub & Standards | FundersAI',
    description:
      'Complete transparency on quantitative financial data sourcing, metric formulas, and zero-hallucination guardrails.',
    url: 'https://www.fundersai.co.in/methodology',
    siteName: 'FundersAI',
  },
};

const methodologyPillars = [
  {
    slug: 'data-sources',
    number: '01',
    title: 'Data Sources & Feeds',
    tag: 'Sourcing',
    color: 'text-emerald-400',
    desc: 'AMFI NAV feeds, NSE direct data, AMC PDF factsheet acquisitions, and Cloudflare R2 archival standards.',
    linkText: 'Explore Data Sources →',
  },
  {
    slug: 'formulas',
    number: '02',
    title: 'Metric Formulas & Math',
    tag: 'Quantitative Engine',
    color: 'text-cyan-400',
    desc: 'Mathematical definitions and code formulas for 1Y/3Y/5Y CAGR, Sharpe Ratio, Sortino Ratio, Alpha, Beta, and Max Drawdown.',
    linkText: 'Explore Formulas →',
  },
  {
    slug: 'resolution',
    number: '03',
    title: 'Scheme Resolution & Benchmarks',
    tag: 'Normalization',
    color: 'text-blue-400',
    desc: 'Scheme alias resolution, Direct vs Regular plan separation, Growth vs IDCW option handling, and Nifty/BSE benchmark mapping.',
    linkText: 'Explore Scheme Resolution →',
  },
  {
    slug: 'guardrails',
    number: '04',
    title: 'AI Guardrails & Abstention',
    tag: 'Non-Hallucination Policy',
    color: 'text-indigo-400',
    desc: 'Strict boundaries separating deterministic math from LLM plain-English summaries, and explicit conditions when FundersAI declines to answer.',
    linkText: 'Explore Guardrails →',
  },
];

export default function MethodologyHubPage() {
  return (
    <div className="min-h-screen bg-[#070b12] text-[#dce8fa] flex flex-col selection:bg-blue-500/30">
      <EcosystemHeader />

      <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-12">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
          <Link href="/" className="hover:text-emerald-400">Home</Link>
          <span>/</span>
          <span className="text-gray-200">Documentation</span>
          <span>/</span>
          <span className="text-emerald-400">Methodology Hub</span>
        </div>

        {/* Hero Header */}
        <div className="space-y-4 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-medium">
            <span>🛡️ E-E-A-T Financial Transparency Standard</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
            Research Methodology: <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400">
              Deterministic Math + Verified Evidence
            </span>
          </h1>
          <p className="text-sm sm:text-base text-gray-400 leading-relaxed">
            FundersAI combines deterministic quantitative calculations from official regulated sources with plain-English summaries. We document exactly how data is sourced, how metrics are computed, and where our system refuses to speculate.
          </p>
        </div>

        {/* Pillars Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {methodologyPillars.map((p, idx) => (
            <MagicCard key={idx} className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className={`text-2xl font-black font-mono ${p.color}`}>{p.number}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-gray-300">
                    {p.tag}
                  </span>
                </div>
                <h2 className="text-xl font-bold text-white">{p.title}</h2>
                <p className="text-xs text-gray-400 leading-relaxed">{p.desc}</p>
              </div>

              <div className="pt-2">
                <Link
                  href={`/methodology/${p.slug}`}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors"
                >
                  <span>{p.linkText}</span>
                </Link>
              </div>
            </MagicCard>
          ))}
        </div>

        {/* Core Principles Section */}
        <div className="p-8 rounded-2xl bg-gray-950/90 border border-gray-800 space-y-6 backdrop-blur-xl">
          <div className="space-y-2">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400">System Commitment</span>
            <h2 className="text-2xl font-bold text-white">Why Deterministic Math Comes First</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-xs text-gray-300">
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-white">1. No Synthetic Data</h3>
              <p className="text-gray-400 leading-relaxed">
                Large language models are never allowed to estimate or guess numerical metrics like CAGR, Sharpe ratio, or TER. Math is executed in Python code prior to prompt injection.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-white">2. Open Source Provenance</h3>
              <p className="text-gray-400 leading-relaxed">
                Every factsheet document ingested into FundersAI retains its original AMC PDF download URL and publication timestamp for independent verification.
              </p>
            </div>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
