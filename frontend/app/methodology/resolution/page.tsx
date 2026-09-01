import type { Metadata } from 'next';
import Link from 'next/link';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';

export const metadata: Metadata = {
  title: 'Scheme Resolution & Benchmarks | FundersAI Methodology',
  description:
    'Documentation on how FundersAI handles scheme alias matching, Direct vs Regular plans, Growth vs IDCW option separation, and benchmark index mapping.',
  keywords: [
    'Mutual fund scheme name resolution',
    'Direct vs Regular plan separation',
    'Growth vs IDCW option handling',
    'FundersAI benchmark mapping',
  ],
  alternates: {
    canonical: 'https://www.fundersai.co.in/methodology/resolution',
  },
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Scheme Resolution & Benchmarks | FundersAI Methodology',
    description: 'Learn how FundersAI resolves scheme names and maps primary benchmark indexes.',
    url: 'https://www.fundersai.co.in/methodology/resolution',
    siteName: 'FundersAI',
  },
};

export default function MethodologyResolutionPage() {
  return (
    <div className="min-h-screen bg-[#070b12] text-[#dce8fa] flex flex-col selection:bg-blue-500/30">
      <EcosystemHeader />

      <main className="flex-1 max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-10">
        <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
          <Link href="/methodology" className="hover:text-emerald-400">Methodology</Link>
          <span>/</span>
          <span className="text-blue-400">03. Scheme Resolution</span>
        </div>

        <div className="space-y-4 max-w-3xl">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-blue-400">Normalization Standard</span>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">Scheme Name Resolution &amp; Benchmark Mapping</h1>
          <p className="text-sm text-gray-400 leading-relaxed">
            Indian mutual fund schemes often appear with varying name strings across factsheets, AMFI feeds, and brokers. FundersAI normalizes names to exact SEBI scheme codes.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 rounded-2xl bg-gray-950/80 border border-gray-800 space-y-3">
            <h3 className="text-base font-bold text-white">Direct vs Regular Plan Handling</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Direct plans (zero distributor commission) and Regular plans are treated as separate database entities with distinct NAV histories and expense ratios. Direct plans are preferred by default in research queries unless specified otherwise.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-gray-950/80 border border-gray-800 space-y-3">
            <h3 className="text-base font-bold text-white">Growth vs IDCW Option Isolation</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Growth options (where gains reinvest) and Income Distribution cum Capital Withdrawal (IDCW) options are isolated. Performance return metrics (CAGR/Sharpe) are computed exclusively on Growth options to eliminate distribution distortions.
            </p>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
