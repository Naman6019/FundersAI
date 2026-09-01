import type { Metadata } from 'next';
import Link from 'next/link';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import { MagicCard } from '@/components/ui/magic-card';

export const metadata: Metadata = {
  title: 'Data & Trust Portal | FundersAI',
  description:
    'Full public transparency on data provenance, daily NAV update frequency, AMC document processing status, and strict non-hallucination guardrails.',
  keywords: [
    'Indian mutual fund data freshness',
    'AMFI NAV update timing',
    'Financial AI hallucination prevention',
    'FundersAI data trust portal',
  ],
  alternates: {
    canonical: 'https://www.fundersai.co.in/data-trust',
  },
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Data & Trust Portal | FundersAI',
    description:
      'Inspect real-time data freshness, official feed sources, and zero-hallucination guardrails.',
    url: 'https://www.fundersai.co.in/data-trust',
    siteName: 'FundersAI',
  },
};

const trustMetrics = [
  { label: 'MF NAV History', status: 'FRESH', desc: 'Updated each business day after AMFI releases daily NAVs (typically by 11 PM IST).', color: 'text-emerald-400' },
  { label: 'AMC Factsheets & SIDs', status: 'INGESTED', desc: 'Acquired from AMC disclosures within 24 hours of publication and stored in Cloudflare R2.', color: 'text-emerald-400' },
  { label: 'Missing Fields', status: 'TRANSPARENT', desc: 'Unavailable fields are explicitly disclosed instead of imputed or guessed by AI.', color: 'text-cyan-400' },
  { label: 'Research Boundary', status: 'STRICT', desc: 'Zero investment advice. No automated buy, sell, or hold recommendations are ever generated.', color: 'text-blue-400' },
];

export default function DataTrustPublicPage() {
  return (
    <div className="min-h-screen bg-[#070b12] text-[#dce8fa] flex flex-col selection:bg-blue-500/30">
      <EcosystemHeader currentApp="datatrust" />

      <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-12">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
          <Link href="/" className="hover:text-emerald-400">Home</Link>
          <span>/</span>
          <span className="text-gray-200">Trust</span>
          <span>/</span>
          <span className="text-emerald-400">Data &amp; Provenance</span>
        </div>

        {/* Hero Header */}
        <div className="space-y-4 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-medium">
            <span>🛡️ Verification &amp; Data Transparency Portal</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
            Know What Is Ready: <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400">
              Data Freshness &amp; Provenance
            </span>
          </h1>
          <p className="text-sm sm:text-base text-gray-400 leading-relaxed">
            FundersAI keeps discovery, acquisition, parsing, and validated runtime data separate. We disclose freshness and data gaps transparently.
          </p>
        </div>

        {/* Live Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {trustMetrics.map((item, idx) => (
            <MagicCard key={idx} className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-gray-400 font-semibold uppercase tracking-wider">{item.label}</span>
                <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-gray-900 border border-gray-800 ${item.color}`}>
                  {item.status}
                </span>
              </div>
              <p className="text-xs text-gray-300 leading-relaxed pt-2">{item.desc}</p>
            </MagicCard>
          ))}
        </div>

        {/* Data Principles Card */}
        <div className="p-8 rounded-2xl bg-gray-950/90 border border-gray-800 space-y-6 backdrop-blur-xl">
          <h2 className="text-2xl font-bold text-white">Our 4 Data Principles</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-xs text-gray-300">
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-emerald-400">1. Official Sources Only</h3>
              <p className="leading-relaxed text-gray-400">
                We never use scraped blog estimates or synthetic AI values. Every number traces back to AMFI, NSE, or official AMC disclosures.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-cyan-400">2. Visible Freshness</h3>
              <p className="leading-relaxed text-gray-400">
                Field-level timestamps expose the exact date of NAVs, holdings, and expense ratios so you know if data is current.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-blue-400">3. Explicit Abstention</h3>
              <p className="leading-relaxed text-gray-400">
                When a scheme lacks historical data or required metrics, FundersAI declines to generate speculative answers.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-indigo-400">4. Reader Citation</h3>
              <p className="leading-relaxed text-gray-400">
                Every AI response links directly to the source document page numbers so research can be verified independently.
              </p>
            </div>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
