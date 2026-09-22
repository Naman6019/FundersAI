import type { Metadata } from 'next';
import Link from 'next/link';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import PortfolioOverlapCalculator from '@/components/tools/PortfolioOverlapCalculator';
import { ToolJsonLd } from '@/components/seo/JsonLd';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import { Layers, HelpCircle } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Mutual Fund Portfolio Overlap Calculator | Check Common Stocks | FundersAI',
  description:
    'Free Mutual Fund Portfolio Overlap Calculator for Indian investors. Compute shared-weight overlap between two mutual funds and see which holdings they have in common. Illustrative reference holdings; not a live AMC disclosure.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/tools/portfolio-overlap',
  },
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Mutual Fund Portfolio Overlap Calculator | FundersAI',
    description:
      'Compute shared-weight overlap between two Indian mutual funds from curated reference holdings. Illustrative, not a live AMC disclosure.',
    url: 'https://www.fundersai.co.in/tools/portfolio-overlap',
  },
};

const OVERLAP_FAQS = [
  {
    q: 'What is mutual fund portfolio overlap?',
    a: 'Portfolio overlap occurs when two or more mutual funds hold the same underlying companies — both holding HDFC Bank, ICICI Bank or Infosys, for example. When overlap is high, adding another fund adds little diversification: you hold a similar basket twice and pay two expense ratios for it.',
  },
  {
    q: 'How does FundersAI calculate overlap?',
    a: 'For each common stock, matched by ISIN, the overlap contribution is the smaller of its weight in the two funds. Summing those minimum weights across every shared holding gives the shared-weight overlap percentage. This is the same convention used in portfolio disclosure analysis, and it is why the result can never exceed the smaller fund\'s total equity weight.',
  },
  {
    q: 'Are the holdings on this page live AMC disclosures?',
    a: 'No. This calculator uses a curated reference snapshot of holdings for a limited set of schemes, labelled with the month it describes. It is illustrative and may differ from the AMC\'s current statutory portfolio. Where we have no curated holdings for a scheme, the calculator shows no overlap figure at all rather than estimating from a proxy.',
  },
  {
    q: 'What is an acceptable portfolio overlap percentage?',
    a: 'Conventionally, under 20% shared weight is read as largely distinct holdings, 20% to 40% as partial duplication that can still be acceptable when the mandates differ, and above 40% as substantial duplication where the two schemes are largely the same basket. These are description conventions, not a recommendation to hold or change any fund.',
  },
  {
    q: 'Why does a fund show "overlap unavailable"?',
    a: 'Because FundersAI does not hold a holdings snapshot it can attribute to that specific scheme. Rather than substitute a category-level proxy — which would attribute one fund\'s stocks to another — the tool reports that overlap cannot be computed for that pair.',
  },
  {
    q: 'Does high overlap mean I should change my funds?',
    a: 'Not by itself. Overlap is one descriptive input. FundersAI is research-only and does not provide investment advice or recommendations; any decision should follow your own review of the official AMC disclosures and, where appropriate, a registered adviser.',
  },
];

export default function PortfolioOverlapPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col justify-between">
      <EcosystemHeader currentApp="tools" />
      <ToolJsonLd
        name="Mutual Fund Portfolio Overlap Calculator"
        description="Compute shared-weight stock overlap between two Indian mutual funds from curated reference holdings. Illustrative snapshot, not a live AMC disclosure."
        url="https://www.fundersai.co.in/tools/portfolio-overlap"
        faqs={OVERLAP_FAQS}
      />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 flex-1 w-full">
        {/* Breadcrumb & Header */}
        <header className="space-y-4">
          <Breadcrumbs
            items={[
              { label: 'Home', href: '/' },
              { label: 'Tools', href: '/tools' },
              { label: 'Portfolio Overlap Calculator' },
            ]}
          />

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-line pb-6">
            <div>
              <h1 className="text-2xl sm:text-4xl font-extrabold font-serif-display text-white tracking-tight flex items-center gap-3">
                <span>Mutual Fund Portfolio Overlap Calculator</span>
              </h1>
              <p className="text-xs sm:text-sm text-text-3 mt-2 max-w-3xl leading-relaxed">
                Compare stock holding duplication between two Indian mutual funds. Shared holdings,
                common ISINs and sector concentration are computed from a curated reference snapshot.
              </p>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-mono font-semibold shrink-0">
              <Layers className="w-4 h-4" />
              <span>Illustrative Reference Data</span>
            </div>
          </div>

          {/*
            The disclosure sits above the tool, not in fine print below it. The figures are a
            curated snapshot rather than the AMC's live monthly disclosure, and the page must
            say so before a reader acts on any number.
          */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] px-5 py-4 text-xs leading-6 text-[#aebed6]">
            <p>
              <span className="font-semibold text-white">How to read this tool. </span>
              Overlap is computed from a curated reference holdings snapshot labelled with the month it
              describes — it is illustrative and is <span className="text-white">not</span> a live read of
              the AMC&apos;s current statutory portfolio disclosure. Holdings are shown only for schemes
              where FundersAI holds a snapshot it can attribute to that specific scheme; for any other
              scheme the calculator reports overlap as unavailable rather than estimating from a proxy.
              Treat the result as a demonstration of the method, and verify current holdings against the
              official AMC disclosure before relying on it.
            </p>
            <p className="mt-2 text-[#7183a0]">
              Research only. Not personalized investment advice or a recommendation.{' '}
              <Link href="/methodology/data-sources" className="text-[#82aff6] hover:text-[#b8d3ff]">
                Data sources →
              </Link>
            </p>
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
      </main>

      <PublicFooter />
    </div>
  );
}
