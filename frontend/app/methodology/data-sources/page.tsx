import type { Metadata } from 'next';
import Link from 'next/link';
import PublicHeader from '@/components/layout/PublicHeader';
import PublicFooter from '@/components/layout/PublicFooter';

export const metadata: Metadata = {
  title: 'Data Sources & Feeds | FundersAI Methodology',
  description:
    'Full technical documentation on how FundersAI sources NAV history from AMFI/NSE, monthly disclosures from AMCs, TER reports, and factsheet PDF filings.',
  keywords: [
    'FundersAI data sources',
    'AMFI NAV API feed',
    'NSE mutual fund data feed',
    'AMC factsheet ingestion source',
  ],
  openGraph: {
    title: 'Data Sources & Feeds | FundersAI Methodology',
    description: 'Learn how FundersAI acquires, parses, and validates official AMC disclosures.',
    url: 'https://www.fundersai.co.in/methodology/data-sources',
    siteName: 'FundersAI',
  },
};

export default function MethodologyDataSourcesPage() {
  return (
    <div className="min-h-screen bg-[#070b12] text-[#dce8fa] flex flex-col selection:bg-blue-500/30">
      <PublicHeader />

      <main className="flex-1 max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-10">
        <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
          <Link href="/methodology" className="hover:text-emerald-400">Methodology</Link>
          <span>/</span>
          <span className="text-emerald-400">01. Data Sources</span>
        </div>

        <div className="space-y-4 max-w-3xl">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400">Sourcing Standard</span>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">Data Sources &amp; Acquisition Feeds</h1>
          <p className="text-sm text-gray-400 leading-relaxed">
            Every numerical field in FundersAI traces to an official or SEBI-regulated source. Synthetic data, scraped blog estimates, and AI-imputed metrics are strictly prohibited.
          </p>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-gray-800 bg-gray-950/80">
          <table className="w-full text-xs sm:text-sm text-left">
            <thead className="bg-gray-900/90 text-gray-300 font-mono text-[11px] uppercase tracking-wider border-b border-gray-800">
              <tr>
                <th className="py-3.5 px-4">Data Type</th>
                <th className="py-3.5 px-4 text-emerald-400">Primary Regulated Source</th>
                <th className="py-3.5 px-4 text-gray-400">Secondary Fallback Feed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 text-gray-200">
              {[
                ['Daily NAV History', 'MFapi (AMFI Official API)', 'NSE Direct Data Feed'],
                ['Scheme AUM', 'AMFI Monthly Disclosure Filing', 'AMC Factsheet PDF'],
                ['Total Expense Ratio (TER)', 'Official AMC Factsheet Disclosure', 'AMFI Monthly TER Report'],
                ['Portfolio Stock Holdings', 'AMC Monthly Portfolio PDF/XLSX', 'SEBI Mandatory Filing'],
                ['Risk Ratios (Sharpe/Beta)', 'Computed from NAV History', 'N/A (Calculated)'],
                ['Benchmark Returns', 'NSE / BSE Index Official Feeds', 'N/A'],
                ['Fund Manager Details', 'AMC Factsheet & SID Filings', 'AMFI Master Database'],
              ].map(([type, primary, fallback], idx) => (
                <tr key={idx}>
                  <td className="py-3.5 px-4 font-semibold text-white">{type}</td>
                  <td className="py-3.5 px-4 font-mono text-emerald-400">{primary}</td>
                  <td className="py-3.5 px-4 text-gray-400">{fallback}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
