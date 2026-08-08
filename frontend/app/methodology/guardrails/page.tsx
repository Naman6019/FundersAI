import type { Metadata } from 'next';
import Link from 'next/link';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';

export const metadata: Metadata = {
  title: 'Guardrails & Abstention Policy | FundersAI Methodology',
  description:
    'Full transparency on FundersAI research-only boundaries: zero financial advice, deterministic math isolation, and explicit conditions when the system refuses to answer.',
  keywords: [
    'FundersAI non-hallucination guardrails',
    'Financial AI abstention policy',
    'SEBI non-advisory compliance AI',
    'Zero hallucination mutual fund research',
  ],
  openGraph: {
    title: 'Guardrails & Abstention Policy | FundersAI Methodology',
    description: 'Learn when and why FundersAI refuses to generate un-backed financial claims.',
    url: 'https://www.fundersai.co.in/methodology/guardrails',
    siteName: 'FundersAI',
  },
};

const abstentionConditions = [
  {
    condition: 'Insufficient History (< 1 Year)',
    reason: 'Schemes with less than 12 months of daily NAV history cannot generate 1Y CAGR, Sharpe ratio, or Beta. The system declines to generate speculative performance ratings.',
  },
  {
    condition: 'Missing Factsheet Field',
    reason: 'When TER, AUM, or portfolio disclosures are absent from AMC filings, FundersAI flags the field as "Unavailable" rather than imputing an estimated value.',
  },
  {
    condition: 'Personalised Buy/Sell Recommendations',
    reason: 'FundersAI is strictly a quantitative research tool. Queries asking "Should I buy fund X?" trigger an explicit non-advisory abstention response.',
  },
  {
    condition: 'Unresolved Scheme Names',
    reason: 'If a user query names an ambiguous scheme that cannot be confidently matched to a SEBI scheme code, the system requests clarification instead of guessing.',
  },
];

export default function MethodologyGuardrailsPage() {
  return (
    <div className="min-h-screen bg-[#070b12] text-[#dce8fa] flex flex-col selection:bg-blue-500/30">
      <EcosystemHeader />

      <main className="flex-1 max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-10">
        <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
          <Link href="/methodology" className="hover:text-emerald-400">Methodology</Link>
          <span>/</span>
          <span className="text-indigo-400">04. Guardrails &amp; Abstention</span>
        </div>

        <div className="space-y-4 max-w-3xl">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-indigo-400">Compliance Standard</span>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">AI Guardrails &amp; Abstention Conditions</h1>
          <p className="text-sm text-gray-400 leading-relaxed">
            FundersAI enforces strict boundaries between deterministic quantitative output and AI natural language generation. When data is partial or out-of-scope, the system explicitly refuses to answer.
          </p>
        </div>

        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">When FundersAI Declines to Answer</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {abstentionConditions.map((item, idx) => (
              <div key={idx} className="p-6 rounded-2xl bg-gray-950/80 border border-gray-800 space-y-3">
                <span className="text-xs font-mono text-indigo-400 font-bold">{item.condition}</span>
                <p className="text-xs text-gray-400 leading-relaxed">{item.reason}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
