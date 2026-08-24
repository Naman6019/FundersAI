import type { Metadata } from 'next';
import Link from 'next/link';
import { Layers, Calculator, Search, Scale, Sparkles, ArrowRight, ShieldCheck } from 'lucide-react';
import { ToolJsonLd } from '@/components/seo/JsonLd';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';

export const metadata: Metadata = {
  title: 'Free Mutual Fund & Investor Tools | FundersAI',
  description:
    'Institutional-grade investor tools: Mutual Fund Portfolio Overlap Calculator, SIP & Step-Up Compounding Calculator, Scheme Screener, and Head-to-Head Comparison.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/tools',
  },
  openGraph: {
    title: 'Free Mutual Fund & Investor Tools | FundersAI',
    description:
      'Analyze portfolio overlap, calculate SIP & Step-Up compounding wealth, and compare Indian mutual funds with official SEBI factsheet data.',
    url: 'https://www.fundersai.co.in/tools',
  },
};

const TOOLS = [
  {
    title: 'Portfolio Overlap Calculator',
    slug: '/tools/portfolio-overlap',
    badge: 'Popular',
    icon: Layers,
    color: '#00FF9D',
    description:
      'Calculate stock holding duplication between any two mutual funds. Identify overlapping stocks, unique assets, and sector concentration to prevent false diversification.',
    highlights: ['3-Way Holding Decomposition', 'Sector Overlap Bars', 'Diversification Health Score'],
  },
  {
    title: 'SIP & Compounding Calculator',
    slug: '/tools/sip-calculator',
    badge: 'High Intent',
    icon: Calculator,
    color: '#66a3ff',
    description:
      'Estimate wealth accumulation for Systematic Investment Plans (SIP), one-time lumpsum, and annual step-up increments with inflation-adjusted purchasing power.',
    highlights: ['Annual Step-Up Increment', 'SEBI Category Benchmarks', 'Inflation-Adjusted Wealth'],
  },
  {
    title: 'Interactive Mutual Fund Screener',
    slug: '/mutual-funds',
    badge: 'Live Database',
    icon: Search,
    color: '#a855f7',
    description:
      'Screen and filter top Indian mutual funds by AMC house, SEBI category, benchmark indices, and live AMFI codes. Inspect verified NAV and factsheets.',
    highlights: ['Dual AMC + Category Filters', 'Active Metric Inspector', '1-Click Factsheets'],
  },
  {
    title: 'Head-to-Head Scheme Comparator',
    slug: '/compare',
    badge: 'Deep Dive',
    icon: Scale,
    color: '#f59e0b',
    description:
      'Perform side-by-side quantitative evaluation across 3-year CAGR, Sharpe ratio, expense ratios, portfolio overlap, and downside risk capture.',
    highlights: ['Side-by-Side Canvas', 'ISIN Overlap Breakdown', 'Risk-Adjusted Alpha'],
  },
];

export default function ToolsIndexPage() {
  return (
    <div className="min-h-screen bg-[#05070f] text-slate-100 flex flex-col justify-between">
      <EcosystemHeader currentApp="tools" />
      <ToolJsonLd
        name="FundersAI Investor Tools Suite"
        description="Suite of free quantitative mutual fund tools for Indian retail investors including portfolio overlap calculators, SIP compounding estimators, and scheme comparators."
        url="https://www.fundersai.co.in/tools"
      />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12 flex-1 w-full">
        {/* Header */}
        <header className="space-y-4 text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00FF9D]/10 border border-[#00FF9D]/20 text-[#00FF9D] text-xs font-mono font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>100% Free • Deterministic Data • No Login Required</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Free Investor Research Tools
          </h1>
          <p className="text-sm sm:text-base text-[#aebed6] leading-relaxed">
            Institutional-grade calculations built for Indian mutual fund investors. Powered by official SEBI disclosures, AMFI data, and deterministic mathematical models.
          </p>
        </header>

        {/* Tools Grid */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {TOOLS.map((tool) => {
            const Icon = tool.icon;
            return (
              <Link
                key={tool.slug}
                href={tool.slug}
                className="group relative rounded-3xl border border-white/10 bg-gradient-to-br from-[#0c1527] to-[#070c17] p-8 shadow-2xl hover:border-white/20 transition-all hover:scale-[1.01] flex flex-col justify-between"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div
                      className="p-3 rounded-2xl border border-white/10 bg-white/[0.03]"
                      style={{ color: tool.color }}
                    >
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className="text-[10px] font-mono font-semibold px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-[#aebed6]">
                      {tool.badge}
                    </span>
                  </div>

                  <div>
                    <h2 className="text-xl font-bold text-white group-hover:text-[#00FF9D] transition-colors">
                      {tool.title}
                    </h2>
                    <p className="text-xs sm:text-sm text-[#7183a0] mt-2 leading-relaxed">
                      {tool.description}
                    </p>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-white/5">
                    {tool.highlights.map((item) => (
                      <div key={item} className="flex items-center gap-2 text-xs text-[#aebed6]">
                        <ShieldCheck className="w-3.5 h-3.5 text-[#00FF9D]" />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-6 flex items-center justify-between text-xs font-bold text-[#00FF9D]">
                  <span>Launch Tool</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            );
          })}
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
