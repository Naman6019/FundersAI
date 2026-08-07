import type { Metadata } from 'next';
import Link from 'next/link';
import PublicHeader from '@/components/layout/PublicHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import { MagicCard } from '@/components/ui/magic-card';
import { ShimmerButton } from '@/components/ui/shimmer-button';

export const metadata: Metadata = {
  title: 'Synthesis by FundersAI | Autonomous AI Mutual Fund Research Studio',
  description:
    'Synthesis by FundersAI leverages autonomous multi-agent graph intelligence to synthesize institutional mutual fund comparison reports, risk metrics, portfolio overlap, and 1-click PDF exports.',
  keywords: [
    'Synthesis by FundersAI',
    'Synthesis Studio',
    'FundersAI Synthesis',
    'AI mutual fund synthesis report',
    'autonomous financial multi-agent research',
    'mutual fund factsheet parser India',
    'Parag Parikh vs HDFC Flexi Cap report',
    'institutional mutual fund comparison PDF',
  ],
  openGraph: {
    title: 'Synthesis by FundersAI | Autonomous AI Mutual Fund Research Studio',
    description:
      'Instant institutional-grade mutual fund comparison reports with quantitative risk metrics, portfolio overlap, and direct serverless PDF exports.',
    url: 'https://www.fundersai.co.in/synthesis',
    siteName: 'Synthesis by FundersAI',
    locale: 'en_IN',
    type: 'website',
    images: [
      {
        url: '/Synthesis_FUNDERSAI.png',
        width: 1200,
        height: 630,
        alt: 'Synthesis by FundersAI',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Synthesis by FundersAI | Autonomous AI Mutual Fund Research Studio',
    description:
      'Instant institutional-grade mutual fund comparison reports with risk metrics, portfolio overlap, and PDF export.',
    images: ['/Synthesis_FUNDERSAI.png'],
  },
};

const features = [
  {
    step: '01',
    title: 'Official AMC Factsheet Parsing',
    color: 'text-emerald-400',
    desc: 'Automated ingestion of monthly factsheets, portfolio holdings (PDF/XLSX), TER disclosures, and SIDs directly from official AMC repositories.',
  },
  {
    step: '02',
    title: 'Deterministic Risk & Ratio Matrix',
    color: 'text-cyan-400',
    desc: '3Y/5Y CAGR, Sharpe Ratio, Sortino Ratio, Jensen’s Alpha, Beta, and Max Drawdown computed mathematically from daily NAV series.',
  },
  {
    step: '03',
    title: 'Portfolio Overlap & Sector Concentration',
    color: 'text-blue-400',
    desc: 'Identifies identical stock holdings across mutual fund schemes to prevent over-diversification and highlight portfolio sector risks.',
  },
  {
    step: '04',
    title: 'LangGraph Multi-Agent Orchestration',
    color: 'text-indigo-400',
    desc: 'Autonomous multi-agent workflows execute separate tasks under strict non-hallucination prompts and zero-advice research boundaries.',
  },
  {
    step: '05',
    title: 'Mermaid SVG Visual Diagrams',
    color: 'text-violet-400',
    desc: 'Generates visual decision trees, portfolio asset allocation charts, and historical drawdown comparisons dynamically inside reports.',
  },
  {
    step: '06',
    title: '1-Click Serverless PDF Export',
    color: 'text-teal-400',
    desc: 'Export complete multi-page institutional reports into formatted PDFs, rendered via a dedicated Playwright serverless Chromium backend.',
  },
];

export default function SynthesisServicePage() {
  return (
    <div className="min-h-screen bg-[#070b12] text-[#dce8fa] flex flex-col selection:bg-blue-500/30">
      <PublicHeader />

      <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-16">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
          <Link href="/" className="hover:text-emerald-400">Home</Link>
          <span>/</span>
          <span className="text-gray-200">Products</span>
          <span>/</span>
          <span className="text-blue-400">Synthesis by FundersAI</span>
        </div>

        {/* Hero Header */}
        <div className="text-center space-y-6 max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono font-semibold shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            <span>Synthesis Engine Active v2.4</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight leading-[1.1]">
            Synthesis by FundersAI <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-teal-400 to-emerald-400">
              Autonomous Financial Intelligence
            </span>
          </h1>

          <p className="text-base sm:text-lg text-gray-300 max-w-2xl mx-auto leading-relaxed">
            Generate institutional-grade mutual fund comparison reports, factsheet disclosures, quantitative risk ratios, and portfolio overlap analysis in seconds.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link href="/reports/generate">
              <ShimmerButton className="px-8 py-3.5 shadow-2xl" borderRadius="9999px" background="#2563eb">
                <span className="text-white font-semibold text-sm tracking-wide flex items-center gap-2">
                  <span>Open Synthesis Studio</span>
                  <span>→</span>
                </span>
              </ShimmerButton>
            </Link>
            <Link
              href="/sample"
              className="px-6 py-3.5 bg-gray-900 border border-gray-800 text-gray-300 font-medium text-sm rounded-full hover:bg-gray-800 hover:text-white transition-all backdrop-blur-md"
            >
              View Sample Report
            </Link>
          </div>
        </div>

        {/* Features Grid */}
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400">Core Capabilities</span>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-white">Institutional Factsheet Synthesis</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, idx) => (
              <MagicCard key={idx} className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-3 flex flex-col justify-between">
                <div className="space-y-2">
                  <span className={`text-2xl font-black font-mono ${f.color}`}>{f.step}</span>
                  <h3 className="text-base font-bold text-white">{f.title}</h3>
                  <p className="text-xs text-gray-400 leading-relaxed">{f.desc}</p>
                </div>
              </MagicCard>
            ))}
          </div>
        </div>

        {/* Unified Subscriptions Section */}
        <div className="p-8 rounded-3xl bg-gray-950/90 border border-gray-800 space-y-6 backdrop-blur-xl max-w-4xl mx-auto text-center">
          <span className="text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400">Unified Pricing</span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white">Available in Free, Pro &amp; Ultra Plans</h2>
          <p className="text-sm text-gray-400 max-w-xl mx-auto leading-relaxed">
            Synthesis Studio is fully integrated with FundersAI subscriptions. Get 1 report/day on Free (₹0), 5 reports/day on Pro (₹99/mo), and 15 reports/day on Ultra (₹199/mo).
          </p>
          <div className="pt-2 flex justify-center">
            <Link
              href="/pricing"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-500 text-white font-semibold text-xs hover:brightness-110 transition-all shadow-lg shadow-blue-500/20"
            >
              <span>Explore Subscriptions &amp; Pricing</span>
              <span>→</span>
            </Link>
          </div>
        </div>
      </main>

      <PublicFooter />

      {/* JSON-LD Schema.org Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'SoftwareApplication',
            'name': 'Synthesis by FundersAI',
            'operatingSystem': 'Web',
            'applicationCategory': 'FinanceApplication',
            'offers': {
              '@type': 'Offer',
              'price': '0',
              'priceCurrency': 'INR',
            },
            'description':
              'Synthesis by FundersAI is an autonomous multi-agent platform for generating institutional mutual fund comparison reports, factsheet analysis, risk metrics, and PDF exports.',
            'image': 'https://www.fundersai.co.in/Synthesis_FUNDERSAI.png',
            'publisher': {
              '@type': 'Organization',
              'name': 'FundersAI',
              'url': 'https://www.fundersai.co.in',
              'logo': 'https://www.fundersai.co.in/Synthesis_FUNDERSAI.png',
            },
          }),
        }}
      />
    </div>
  );
}
