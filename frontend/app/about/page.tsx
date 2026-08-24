import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'About | FundersAI',
  description:
    'FundersAI is an independent mutual fund research tool built for Indian investors who want deterministic metrics, official-source evidence, and visible data limits — not AI-generated opinions.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/about',
  },
};

export default function AboutPage() {
  return (
    <main className="min-h-dvh bg-[#070b12] px-4 py-12 text-[#dce8fa] sm:px-6">
      <article className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#101724] p-6 shadow-2xl sm:p-10">
        <Link href="/" className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
          ← FundersAI
        </Link>

        <h1 className="mt-6 text-3xl font-semibold tracking-tight text-white">About FundersAI</h1>
        <p className="mt-2 text-sm text-[#7183a0]">Updated July 2026</p>

        <div className="mt-8 space-y-8 text-sm leading-7 text-[#aebed6]">

          <section>
            <h2 className="text-lg font-semibold text-white">Why this exists</h2>
            <p className="mt-3">
              Indian retail investors have access to thousands of mutual fund schemes but almost no reliable way to
              compare them on the same terms. Public tools either hide stale data, strip out missing-field
              warnings, or produce AI-generated summaries that are fluent but unverifiable.
            </p>
            <p className="mt-3">
              FundersAI was built to fix that gap: a research tool that shows exactly what it knows, where the data
              came from, when it was last updated, and what it does not know — before drawing any conclusion.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-white">What FundersAI does</h2>
            <p className="mt-3">
              FundersAI indexes official AMC disclosures — factsheets, portfolio holdings, and scheme information
              documents — and combines them with daily NAV history from AMFI and NSE. Every metric (CAGR, Sharpe,
              max drawdown, expense ratio, AUM) is calculated deterministically from those sources.
            </p>
            <p className="mt-3">
              An AI layer reads the deterministic output and writes a plain-English summary. It does not have
              access to external training-time fund data — it writes about the numbers FundersAI just calculated.
              The boundary between deterministic and AI-generated content is visible in every response.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-white">What FundersAI does not do</h2>
            <p className="mt-3">
              FundersAI does not give investment advice. It does not tell you which fund to buy, sell, or hold. It
              does not generate personalised recommendations. When a question pushes past the research boundary,
              the system declines and explains why.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-white">Product stage</h2>
            <p className="mt-3">
              FundersAI is in early access. Coverage, freshness, and feature depth will improve over time. The
              current supported AMC registry covers 12 fund houses. Data limitations are always disclosed inside
              the product — not hidden behind confident-sounding language.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-white">Who built it</h2>
            <p className="mt-3">
              FundersAI is an independent project built in India, focused on bringing research-grade transparency
              to retail mutual fund analysis. The product is live at{' '}
              <a
                href="https://www.fundersai.co.in"
                className="font-medium text-[#82aff6] hover:text-[#b8d3ff] transition-colors"
              >
                fundersai.co.in
              </a>
              .
            </p>
          </section>

        </div>

        <div className="mt-10 flex flex-wrap gap-4 border-t border-white/10 pt-6 text-sm">
          <Link href="/" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            Home
          </Link>
          <Link href="/methodology" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            Methodology
          </Link>
          <Link href="/contact" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            Contact
          </Link>
          <Link href="/dashboard" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            Open workspace
          </Link>
        </div>
      </article>
    </main>
  );
}
