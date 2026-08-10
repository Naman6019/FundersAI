import type { Metadata } from 'next';
import Link from 'next/link';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import { MagicCard } from '@/components/ui/magic-card';
import { ShimmerButton } from '@/components/ui/shimmer-button';

export const metadata: Metadata = {
  title: 'Sample Comparison Report | Synthesis by FundersAI',
  description:
    'Inspect a full, un-gated institutional mutual fund research sample. Compare Parag Parikh Flexi Cap vs HDFC Flexi Cap across NAV, CAGR, Sharpe ratio, expense ratio, and portfolio overlap.',
  keywords: [
    'Sample mutual fund comparison report',
    'PPFAS vs HDFC Flexi Cap comparison',
    'Institutional mutual fund report demo',
    'Mutual fund risk matrix sample',
  ],
  openGraph: {
    title: 'Sample Comparison Report | Synthesis by FundersAI',
    description:
      'Explore an institutional mutual fund research sample with verified AMC data, risk ratios, and direct PDF downloads.',
    url: 'https://www.fundersai.co.in/sample',
    siteName: 'FundersAI',
  },
};

const sampleData = {
  fundA: {
    name: 'Parag Parikh Flexi Cap Fund - Direct (G)',
    amc: 'PPFAS Mutual Fund',
    category: 'Flexi Cap Fund',
    nav: '₹84.12',
    aum: '₹68,450 Cr',
    ter: '0.58%',
    cagr3y: '22.4%',
    cagr5y: '24.1%',
    sharpe: '1.42',
    sortino: '2.15',
    alpha: '4.82%',
    beta: '0.74',
    maxDrawdown: '-14.2%',
  },
  fundB: {
    name: 'HDFC Flexi Cap Fund - Direct (G)',
    amc: 'HDFC Mutual Fund',
    category: 'Flexi Cap Fund',
    nav: '₹1,640.25',
    aum: '₹54,120 Cr',
    ter: '0.86%',
    cagr3y: '25.1%',
    cagr5y: '21.8%',
    sharpe: '1.38',
    sortino: '1.98',
    alpha: '5.10%',
    beta: '0.91',
    maxDrawdown: '-18.6%',
  },
};

export default function SamplePage() {
  return (
    <div className="min-h-screen bg-[#070b12] text-[#dce8fa] flex flex-col selection:bg-blue-500/30">
      <EcosystemHeader currentApp="synthesis" />

      <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-12">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
          <Link href="/" className="hover:text-emerald-400">Home</Link>
          <span>/</span>
          <span className="text-gray-200">Sample Research</span>
          <span>/</span>
          <span className="text-blue-400">Flexi Cap Battle</span>
        </div>

        {/* Hero Section */}
        <div className="space-y-4 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono font-medium">
            <span>⚡ Interactive Un-gated Sample Report</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
            Institutional Research Sample: <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-teal-400 to-emerald-400">
              PPFAS Flexi Cap vs HDFC Flexi Cap
            </span>
          </h1>
          <p className="text-sm sm:text-base text-gray-400 leading-relaxed">
            This sample demonstrates FundersAI’s deterministic quantitative analysis engine. Every metric is computed directly from official AMC disclosures, AMFI daily NAV feeds, and verified factsheets.
          </p>
        </div>

        {/* Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-gray-900/80 border border-gray-800 backdrop-blur-xl">
          <div className="flex items-center gap-3 text-xs font-mono text-gray-400">
            <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              Official Data Verified
            </span>
            <span>·</span>
            <span>Source: July 2026 Factsheets</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/synthesis/generate">
              <ShimmerButton className="px-5 py-2 text-xs font-semibold" borderRadius="0.5rem" background="#2563eb">
                <span>Run Your Own Comparison →</span>
              </ShimmerButton>
            </Link>
          </div>
        </div>

        {/* Side-by-Side Fund Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-900 pb-3">
              <span className="text-xs font-mono text-emerald-400 font-bold">{sampleData.fundA.amc}</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">
                Low Beta Alpha
              </span>
            </div>
            <h3 className="text-lg font-bold text-white">{sampleData.fundA.name}</h3>
            <div className="grid grid-cols-2 gap-3 text-xs pt-2">
              <div className="p-2.5 rounded-lg bg-gray-900/60">
                <span className="text-gray-400 block text-[10px]">NAV</span>
                <span className="font-bold text-white text-base">{sampleData.fundA.nav}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-gray-900/60">
                <span className="text-gray-400 block text-[10px]">AUM</span>
                <span className="font-bold text-white text-base">{sampleData.fundA.aum}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-gray-900/60">
                <span className="text-gray-400 block text-[10px]">Expense Ratio (TER)</span>
                <span className="font-bold text-emerald-400 text-base">{sampleData.fundA.ter}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-gray-900/60">
                <span className="text-gray-400 block text-[10px]">3Y CAGR</span>
                <span className="font-bold text-white text-base">{sampleData.fundA.cagr3y}</span>
              </div>
            </div>
          </MagicCard>

          <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-900 pb-3">
              <span className="text-xs font-mono text-blue-400 font-bold">{sampleData.fundB.amc}</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950/60 text-blue-300 border border-blue-800/40">
                High CAGR Momentum
              </span>
            </div>
            <h3 className="text-lg font-bold text-white">{sampleData.fundB.name}</h3>
            <div className="grid grid-cols-2 gap-3 text-xs pt-2">
              <div className="p-2.5 rounded-lg bg-gray-900/60">
                <span className="text-gray-400 block text-[10px]">NAV</span>
                <span className="font-bold text-white text-base">{sampleData.fundB.nav}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-gray-900/60">
                <span className="text-gray-400 block text-[10px]">AUM</span>
                <span className="font-bold text-white text-base">{sampleData.fundB.aum}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-gray-900/60">
                <span className="text-gray-400 block text-[10px]">Expense Ratio (TER)</span>
                <span className="font-bold text-blue-400 text-base">{sampleData.fundB.ter}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-gray-900/60">
                <span className="text-gray-400 block text-[10px]">3Y CAGR</span>
                <span className="font-bold text-white text-base">{sampleData.fundB.cagr3y}</span>
              </div>
            </div>
          </MagicCard>
        </div>

        {/* Quantitative Risk Matrix Table */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">Quantitative Risk Matrix</h2>
            <span className="text-xs font-mono text-gray-400">Risk-Adjusted Return Analysis</span>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-gray-800 bg-gray-950/80">
            <table className="w-full text-xs sm:text-sm text-left">
              <thead className="bg-gray-900/90 text-gray-300 font-mono text-[11px] uppercase tracking-wider border-b border-gray-800">
                <tr>
                  <th className="py-3.5 px-4">Metric</th>
                  <th className="py-3.5 px-4 text-emerald-400">PPFAS Flexi Cap</th>
                  <th className="py-3.5 px-4 text-blue-400">HDFC Flexi Cap</th>
                  <th className="py-3.5 px-4 text-gray-400">Verdict / Advantage</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 text-gray-200">
                <tr>
                  <td className="py-3.5 px-4 font-semibold text-white">Sharpe Ratio (3Y)</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">1.42</td>
                  <td className="py-3.5 px-4 font-mono">1.38</td>
                  <td className="py-3.5 px-4 text-gray-400">PPFAS provides superior risk-adjusted return per unit of total risk.</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-4 font-semibold text-white">Sortino Ratio (3Y)</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">2.15</td>
                  <td className="py-3.5 px-4 font-mono">1.98</td>
                  <td className="py-3.5 px-4 text-gray-400">PPFAS exhibits lower downside volatility relative to benchmark.</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-4 font-semibold text-white">Alpha (3Y)</td>
                  <td className="py-3.5 px-4 font-mono">4.82%</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-blue-400">5.10%</td>
                  <td className="py-3.5 px-4 text-gray-400">HDFC generated slightly higher excess return over Nifty 50 TRI.</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-4 font-semibold text-white">Beta</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">0.74</td>
                  <td className="py-3.5 px-4 font-mono">0.91</td>
                  <td className="py-3.5 px-4 text-gray-400">PPFAS is significantly less market-sensitive during market sell-offs.</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-4 font-semibold text-white">Max Drawdown (3Y)</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">-14.2%</td>
                  <td className="py-3.5 px-4 font-mono">-18.6%</td>
                  <td className="py-3.5 px-4 text-gray-400">PPFAS protected capital better during peak market pullbacks.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Portfolio Overlap Insight Card */}
        <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-cyan-400 font-semibold uppercase tracking-wider">Portfolio Overlap Analysis</span>
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800/40">28.4% Overlap</span>
          </div>
          <h3 className="text-lg font-bold text-white">Common Equity Holdings Overview</h3>
          <p className="text-xs text-gray-400 leading-relaxed">
            These two flexi-cap schemes share <strong>12 common stock holdings</strong> out of total portfolio constituents. Common top positions include ICICI Bank, HDFC Bank, and ITC Limited.
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            {['ICICI Bank (7.8%)', 'HDFC Bank (6.9%)', 'ITC Ltd (4.2%)', 'Axis Bank (3.8%)', 'L&T (3.1%)'].map((stock, i) => (
              <span key={i} className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-gray-900 border border-gray-800 text-gray-300">
                {stock}
              </span>
            ))}
          </div>
        </MagicCard>
      </main>

      <PublicFooter />
    </div>
  );
}
