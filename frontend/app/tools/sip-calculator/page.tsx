import type { Metadata } from 'next';
import Link from 'next/link';
import SipCalculatorPublic from '@/components/tools/SipCalculatorPublic';
import { ToolJsonLd } from '@/components/seo/JsonLd';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import { Calculator, HelpCircle } from 'lucide-react';

export const metadata: Metadata = {
  title: 'SIP Calculator – Systematic Investment Plan & Step-Up Calculator | FundersAI',
  description:
    'Free SIP Calculator & Step-Up Investment Calculator for Indian mutual funds. Calculate wealth accumulation, compounded maturity returns, and inflation-adjusted corpus.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/tools/sip-calculator',
  },
  openGraph: {
    title: 'SIP Calculator & Wealth Compounding Tool | FundersAI',
    description:
      'Calculate maturity corpus for Monthly SIP, Lumpsum, and Step-Up investments with SEBI category return benchmarks.',
    url: 'https://www.fundersai.co.in/tools/sip-calculator',
  },
};

const SIP_FAQS = [
  {
    q: 'How does an SIP calculate wealth growth?',
    a: 'A Systematic Investment Plan (SIP) uses periodic monthly compounding based on the formula: FV = P × [((1 + r)^n - 1) / r] × (1 + r), where P is monthly investment, r is monthly rate of return, and n is total number of monthly payments. Compounding allows both your principal and previous earnings to generate returns over time.',
  },
  {
    q: 'What is a Step-Up SIP and why should I use it?',
    a: 'A Step-Up SIP automatically increases your monthly investment amount by a fixed percentage (e.g., +10% every year) in line with your annual salary increments. Step-up compounding dramatically accelerates wealth accumulation compared to a static SIP.',
  },
  {
    q: 'What return rates are reasonable for Indian mutual funds?',
    a: 'Historically, over 10+ year holding horizons: Large Cap / Nifty 50 index funds have returned ~12%–13% CAGR; Flexi Cap funds ~13%–15% CAGR; Mid Cap funds ~15%–17% CAGR; and Small Cap funds ~17%–20% CAGR. Returns are subject to market cycles and are not guaranteed.',
  },
  {
    q: 'Should I invest via SIP or Lumpsum?',
    a: 'SIP is generally recommended for salaried investors as it instills financial discipline and utilizes rupee cost averaging (buying more units when markets are down and fewer when markets are up). Lumpsum is effective during broad market corrections or when investing one-time windfall funds.',
  },
];

export default function SipCalculatorPage() {
  return (
    <div className="min-h-screen bg-[#05070f] text-slate-100 flex flex-col justify-between">
      <EcosystemHeader currentApp="tools" />
      <ToolJsonLd
        name="Mutual Fund SIP & Step-Up Calculator"
        description="Estimate compound growth, maturity corpus, and inflation-adjusted future wealth for Systematic Investment Plans and Lumpsum mutual fund investments."
        url="https://www.fundersai.co.in/tools/sip-calculator"
        faqs={SIP_FAQS}
      />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 flex-1 w-full">
        {/* Breadcrumb & Header */}
        <header className="space-y-4">
          <div className="flex items-center gap-2 text-xs font-mono text-[#7183a0]">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <span>/</span>
            <Link href="/tools" className="hover:text-white transition-colors">Tools</Link>
            <span>/</span>
            <span className="text-[#00FF9D]">SIP Calculator</span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
            <div>
              <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight flex items-center gap-3">
                <span>Mutual Fund SIP & Step-Up Calculator</span>
              </h1>
              <p className="text-xs sm:text-sm text-[#aebed6] mt-2 max-w-3xl leading-relaxed">
                Calculate your future investment corpus from monthly SIPs or one-time lumpsum investments. Model annual step-up salary increments and inflation adjustments in real-time.
              </p>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#66a3ff]/10 border border-[#66a3ff]/20 text-[#66a3ff] text-xs font-mono font-semibold shrink-0">
              <Calculator className="w-4 h-4" />
              <span>Monthly Compounding Engine</span>
            </div>
          </div>
        </header>

        {/* Interactive SIP Calculator */}
        <SipCalculatorPublic />

        {/* Educational FAQ Section */}
        <section className="space-y-6 pt-8 border-t border-white/10">
          <div className="flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-[#00FF9D]" />
            <h2 className="text-xl font-bold text-white">Frequently Asked Questions</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SIP_FAQS.map((faq) => (
              <div
                key={faq.q}
                className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-2"
              >
                <h3 className="text-sm font-bold text-white">{faq.q}</h3>
                <p className="text-xs text-[#aebed6] leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
