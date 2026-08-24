import type { Metadata } from 'next';
import Link from 'next/link';
import PortfolioOverlapCalculator from '@/components/tools/PortfolioOverlapCalculator';
import { ToolJsonLd } from '@/components/seo/JsonLd';
import { Layers, HelpCircle, ArrowLeft, ShieldCheck } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Mutual Fund Portfolio Overlap Calculator | Check Common Stocks | FundersAI',
  description:
    'Free Mutual Fund Portfolio Overlap Calculator for Indian investors. Calculate stock duplication % between any two mutual funds, find shared holdings, and eliminate portfolio redundancy.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/tools/portfolio-overlap',
  },
  openGraph: {
    title: 'Mutual Fund Portfolio Overlap Calculator | FundersAI',
    description:
      'Check stock overlap % between Indian mutual funds before investing. Identify shared ISIN holdings and eliminate duplicate expense ratios.',
    url: 'https://www.fundersai.co.in/tools/portfolio-overlap',
  },
};

const OVERLAP_FAQS = [
  {
    q: 'What is mutual fund portfolio overlap?',
    a: 'Portfolio overlap occurs when two or more mutual funds in your portfolio invest in the exact same underlying companies (e.g., both holding HDFC Bank, ICICI Bank, or Infosys). When overlap is high, adding another fund does not improve diversification—it simply duplicates your existing risk while charging duplicate expense ratios.',
  },
  {
    q: 'What is a good or acceptable portfolio overlap percentage?',
    a: 'Generally: Under 20% overlap indicates healthy diversification across distinct market segments. 20% to 40% is moderate and acceptable when funds focus on different sectors or market caps. Over 40% overlap indicates redundant duplication where one fund is likely unnecessary.',
  },
  {
    q: 'Why should investors avoid high mutual fund overlap?',
    a: 'High overlap creates the illusion of diversification ("diworsification"). You pay two separate total expense ratios (TER) for essentially the same basket of stocks, and market downturns in shared mega-caps impact your overall portfolio with concentrated volatility.',
  },
  {
    q: 'How does FundersAI calculate portfolio overlap?',
    a: 'FundersAI uses official monthly AMC portfolio disclosures published under SEBI regulations. For each common stock (matched by ISIN code), the overlap contribution is min(Weight in Fund A, Weight in Fund B). Summing these minimum weights across all shared holdings gives the exact portfolio overlap percentage.',
  },
];

export default function PortfolioOverlapPage() {
  return (
    <main className="min-h-screen bg-[#05070f] text-slate-100 px-4 sm:px-6 lg:px-8 py-10">
      <ToolJsonLd
        name="Mutual Fund Portfolio Overlap Calculator"
        description="Calculate stock holding overlap and duplication between any two Indian mutual funds based on official SEBI portfolio disclosures."
        url="https://www.fundersai.co.in/tools/portfolio-overlap"
        faqs={OVERLAP_FAQS}
      />

      <div className="max-w-6xl mx-auto space-y-12">
        {/* Breadcrumb & Header */}
        <header className="space-y-4">
          <div className="flex items-center gap-2 text-xs font-mono text-[#7183a0]">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <span>/</span>
            <Link href="/tools" className="hover:text-white transition-colors">Tools</Link>
            <span>/</span>
            <span className="text-[#00FF9D]">Portfolio Overlap Calculator</span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
            <div>
              <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight flex items-center gap-3">
                <span>Mutual Fund Portfolio Overlap Calculator</span>
              </h1>
              <p className="text-xs sm:text-sm text-[#aebed6] mt-2 max-w-3xl leading-relaxed">
                Compare stock holding duplication between any two Indian mutual funds. Discover shared ISINs, unique holdings, and sector concentration before investing.
              </p>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#00FF9D]/10 border border-[#00FF9D]/20 text-[#00FF9D] text-xs font-mono font-semibold shrink-0">
              <Layers className="w-4 h-4" />
              <span>SEBI Disclosure Powered</span>
            </div>
          </div>
        </header>

        {/* Interactive Overlap Tool */}
        <PortfolioOverlapCalculator />

        {/* Educational FAQ Section */}
        <section className="space-y-6 pt-8 border-t border-white/10">
          <div className="flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-[#00FF9D]" />
            <h2 className="text-xl font-bold text-white">Frequently Asked Questions</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {OVERLAP_FAQS.map((faq) => (
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
      </div>
    </main>
  );
}
