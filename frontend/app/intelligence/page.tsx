import type { Metadata } from 'next';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { MagicCard } from '@/components/ui/magic-card';

export const metadata: Metadata = {
  title: 'Source Intelligence & Factsheet Engine | FundersAI',
  description:
    'Deep dive into FundersAI source intelligence layer: official AMC factsheet parsing, R2 document archiving, vector embeddings, and direct PDF claim citation.',
  keywords: [
    'AMC factsheet parser India',
    'Mutual fund portfolio disclosure tracking',
    'SEBI factsheet extraction AI',
    'FundersAI source intelligence',
  ],
  alternates: {
    canonical: 'https://www.fundersai.co.in/intelligence',
  },
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Source Intelligence & Factsheet Engine | FundersAI',
    description:
      'Learn how FundersAI ingests, parses, and indexes official AMC disclosures with zero-hallucination vector search.',
    url: 'https://www.fundersai.co.in/intelligence',
    siteName: 'FundersAI',
  },
};

const amcRegistry = [
  { name: 'PPFAS Mutual Fund', documents: 'Factsheets, Portfolio Holdings, SID', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
  { name: 'HDFC Mutual Fund', documents: 'Factsheets, Monthly Portfolio, TER', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
  { name: 'ICICI Prudential MF', documents: 'Factsheets, SIDs, Holdings XLSX', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
  { name: 'SBI Mutual Fund', documents: 'Factsheets, Portfolio Disclosures', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
  { name: 'Kotak Mutual Fund', documents: 'Factsheets, SIDs, TER Reports', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
  { name: 'Axis Mutual Fund', documents: 'Factsheets, Holdings PDF/XLSX', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
  { name: 'Nippon India MF', documents: 'Factsheets, Risk-o-meter, SIDs', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
  { name: 'Mirae Asset MF', documents: 'Factsheets, Portfolio Holdings', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
  { name: 'Quant Mutual Fund', documents: 'Factsheets, Turnover Ratio, TER', status: 'Active (Daily Sync)', color: 'text-blue-400' },
  { name: 'DSP Mutual Fund', documents: 'Factsheets, Portfolio Holdings', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
  { name: 'Motilal Oswal MF', documents: 'Factsheets, Portfolio Holdings', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
  { name: 'Aditya Birla Sun Life', documents: 'Factsheets, SIDs, TER Disclosures', status: 'Active (Daily Sync)', color: 'text-emerald-400' },
];

export default function IntelligencePage() {
  return (
    <div className="min-h-screen bg-[#070b12] text-[#dce8fa] flex flex-col selection:bg-blue-500/30">
      <EcosystemHeader />

      <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-12">
        {/* Breadcrumb */}
        <Breadcrumbs
          tone="docs"
          currentClassName="text-cyan-400"
          items={[
            { label: 'Home', href: '/' },
            { label: 'Architecture' },
            { label: 'Source Intelligence' },
          ]}
        />

        {/* Hero */}
        <div className="space-y-4 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-mono font-medium">
            <span>🔍 Factsheet Indexation &amp; Document Ingestion Engine</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
            Source Intelligence: <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-400 to-emerald-400">
              Official Document Fact Extraction
            </span>
          </h1>
          <p className="text-sm sm:text-base text-gray-400 leading-relaxed">
            Every text summary and data point in FundersAI links back to official AMC source filings. We store cold PDFs in Cloudflare R2 and index structured tables in Supabase PostgreSQL.
          </p>
        </div>

        {/* Intelligence Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-3">
            <div className="text-xs font-mono text-cyan-400">Component 01</div>
            <h3 className="text-lg font-bold text-white">Hybrid PDF &amp; Table Parser</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Combines PyMuPDF, pdfplumber, and custom layout parsers to extract portfolio stock weights, sector allocations, and expense ratios from complex multi-column AMC PDFs.
            </p>
          </MagicCard>

          <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-3">
            <div className="text-xs font-mono text-emerald-400">Component 02</div>
            <h3 className="text-lg font-bold text-white">1,536-Dim Vector Retrieval</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Text passages are embedded using OpenAI <code className="text-emerald-300 font-mono">text-embedding-3-small</code>. Search queries execute direct cosine similarity retrieval over verified document chunks.
            </p>
          </MagicCard>

          <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-3">
            <div className="text-xs font-mono text-blue-400">Component 03</div>
            <h3 className="text-lg font-bold text-white">Claim-Level Citation</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Answers include reader-friendly claim badges (e.g., <em>[Source: PPFAS July 2026 Factsheet, p.4]</em>) allowing users to verify facts against the original AMC publication.
            </p>
          </MagicCard>
        </div>

        {/* AMC Coverage Matrix */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">AMC Ingestion Registry &amp; Coverage</h2>
            <span className="text-xs font-mono text-gray-400">12 Asset Management Companies</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {amcRegistry.map((amc, idx) => (
              <div key={idx} className="p-4 bg-gray-950/80 rounded-xl border border-gray-800 space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-white">{amc.name}</h3>
                  <span className={`text-[10px] font-mono ${amc.color}`}>{amc.status}</span>
                </div>
                <p className="text-[11px] text-gray-400">{amc.documents}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
