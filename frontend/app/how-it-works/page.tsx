import type { Metadata } from 'next';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { MagicCard } from '@/components/ui/magic-card';

export const metadata: Metadata = {
  title: 'How It Works & Architecture Flow | FundersAI',
  description:
    'Explore FundersAI autonomous multi-agent architecture: from official AMC factsheet ingestion to deterministic metric calculation, vector retrieval, and serverless PDF generation.',
  keywords: [
    'FundersAI architecture flow',
    'LangGraph financial multi-agent pipeline',
    'Deterministic quantitative mutual fund engine',
    'AMC factsheet ingestion workflow',
  ],
  alternates: {
    canonical: 'https://www.fundersai.co.in/how-it-works',
  },
  openGraph: {
    images: ['/opengraph-image'],
    title: 'How It Works & Architecture Flow | FundersAI',
    description:
      'Learn how FundersAI combines official AMC factsheet ingestion with deterministic metric calculations and zero-hallucination multi-agent verification.',
    url: 'https://www.fundersai.co.in/how-it-works',
    siteName: 'FundersAI',
  },
};

const pipelineSteps = [
  {
    step: '01',
    title: 'AMC Factsheet & Disclosure Ingestion',
    tag: 'Acquisition Layer',
    color: 'text-emerald-400',
    desc: 'Official monthly factsheets, portfolio disclosures (PDF/XLSX), and Scheme Information Documents (SIDs) are acquired directly from SEBI-registered Asset Management Companies and cold-archived in Cloudflare R2.',
  },
  {
    step: '02',
    title: 'Structured Parsing & Vector Embeddings',
    tag: 'Indexation Layer',
    color: 'text-cyan-400',
    desc: 'Factsheet tables, NAV histories (MFapi/NSE), TER, and holdings are extracted into normalized Supabase PostgreSQL tables. Text passages generate direct OpenAI text-embedding-3-small 1,536-dim vector embeddings.',
  },
  {
    step: '03',
    title: 'Deterministic Metric Computation',
    tag: 'Quantitative Engine',
    color: 'text-blue-400',
    desc: 'Metrics including 1Y/3Y/5Y CAGR, Sharpe ratio, Sortino ratio, Alpha, Beta, Max Drawdown, and Portfolio Overlap % are computed strictly using deterministic Python/FastAPI math formulas.',
  },
  {
    step: '04',
    title: 'LangGraph Multi-Agent Orchestration',
    tag: 'Intelligence Layer',
    color: 'text-indigo-400',
    desc: 'Autonomous multi-agent graphs synthesize quantitative metric outputs into structured comparative narratives. Agents operate under strict non-hallucination prompts and explicit abstention triggers.',
  },
  {
    step: '05',
    title: 'Visual Diagram & Matrix Generation',
    tag: 'Rendering Layer',
    color: 'text-violet-400',
    desc: 'Dynamic Mermaid SVG diagrams, portfolio overlap sector trees, and risk matrix tables are rendered to provide clear visual comparisons alongside textual synthesis.',
  },
  {
    step: '06',
    title: 'Institutional Serverless PDF Export',
    tag: 'Export Layer',
    color: 'text-teal-400',
    desc: 'Reports can be exported into institutional-grade multi-page PDFs with 1 click, rendered via a dedicated Playwright serverless Chromium backend on Google Cloud Run.',
  },
];

export default function HowItWorksPage() {
  return (
    <div className="min-h-screen bg-[#070b12] text-[#dce8fa] flex flex-col selection:bg-blue-500/30">
      <EcosystemHeader />

      <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-12">
        {/* Breadcrumb */}
        <Breadcrumbs
          tone="docs"
          currentClassName="text-blue-400"
          items={[
            { label: 'Home', href: '/' },
            { label: 'Architecture' },
            { label: 'System Flow' },
          ]}
        />

        {/* Hero */}
        <div className="space-y-4 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-medium">
            <span>⚙️ End-to-End System Architecture</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
            How FundersAI Operates: <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400">
              The 6-Step Multi-Agent Pipeline
            </span>
          </h1>
          <p className="text-sm sm:text-base text-gray-400 leading-relaxed">
            FundersAI decouples document ingestion, mathematical computation, and LLM text generation to guarantee zero-hallucination quantitative research.
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {pipelineSteps.map((s, idx) => (
            <MagicCard key={idx} className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className={`text-2xl font-black font-mono ${s.color}`}>{s.step}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-gray-300">
                    {s.tag}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white">{s.title}</h3>
                <p className="text-xs text-gray-400 leading-relaxed">{s.desc}</p>
              </div>
            </MagicCard>
          ))}
        </div>

        {/* SLA & Performance Banner */}
        <div className="p-8 rounded-2xl bg-gray-950/90 border border-gray-800 space-y-4 backdrop-blur-xl">
          <h2 className="text-xl font-bold text-white">System Performance &amp; Data Guarantees</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800/60">
              <span className="text-gray-400 text-[10px] uppercase font-mono block">NAV Refresh SLA</span>
              <span className="text-lg font-bold text-emerald-400 font-mono">Daily by 11 PM IST</span>
              <p className="text-gray-400 mt-1">Automatic sync with AMFI daily feeds.</p>
            </div>
            <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800/60">
              <span className="text-gray-400 text-[10px] uppercase font-mono block">Factsheet Latency</span>
              <span className="text-lg font-bold text-cyan-400 font-mono">&lt; 24h Post AMC Release</span>
              <p className="text-gray-400 mt-1">Ingested within 24 hours of AMC publication.</p>
            </div>
            <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800/60">
              <span className="text-gray-400 text-[10px] uppercase font-mono block">Mathematical Accuracy</span>
              <span className="text-lg font-bold text-blue-400 font-mono">100% Deterministic</span>
              <p className="text-gray-400 mt-1">LLMs never generate mathematical values.</p>
            </div>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
