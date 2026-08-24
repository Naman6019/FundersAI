import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Terms of Use | FundersAI',
  description:
    'Terms governing your use of the FundersAI research workspace — including research-only scope, subscription cancellation and refunds, data limitations, governing law, and acceptable use.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/terms',
  },
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  );
}

export default function TermsPage() {
  return (
    <main className="min-h-dvh bg-[#070b12] px-4 py-12 text-[#dce8fa] sm:px-6">
      <article className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#101724] p-6 shadow-2xl sm:p-10">
        <Link href="/" className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
          ← FundersAI
        </Link>
        <h1 className="mt-6 text-3xl font-semibold tracking-tight text-white">Terms of Use</h1>
        <p className="mt-2 text-sm text-[#7183a0]">Last updated: July 31, 2026</p>

        <div className="mt-8 space-y-8 text-sm leading-7 text-[#aebed6]">

          <Section title="Research use only">
            <p>
              FundersAI provides general market research and mutual fund comparison tools for informational
              purposes. It does not provide personalised investment, legal, or tax advice. Nothing on the platform
              constitutes a securities recommendation or a financial product offer.
            </p>
            <p>
              FundersAI will not generate buy, sell, or hold recommendations. When a query pushes past the
              research boundary, the system declines and explains why. Verify all information with official
              sources and consult a qualified financial adviser before making investment decisions.
            </p>
          </Section>

          <Section title="Data limitations">
            <p>
              Market and mutual fund data may be delayed, incomplete, unavailable, or affected by source changes.
              Freshness status labels and missing-field warnings are part of every research output — they must be
              considered alongside any conclusions drawn from the data.
            </p>
            <p>
              FundersAI makes no warranty that the data is accurate, complete, or current. Metrics are calculated
              deterministically from source data; errors in the underlying source data will propagate.
            </p>
          </Section>

          <Section title="Account responsibility">
            <p>
              Keep your sign-in credentials secure and use the service only through your own account. Do not
              attempt to bypass access controls, scrape the platform systematically, reverse-engineer proprietary
              components, or use the service for unlawful activity.
            </p>
            <p>
              You are responsible for all activity that occurs under your account. If you believe your account has
              been compromised, contact us immediately via the in-product feedback form.
            </p>
          </Section>

          <Section title="Subscriptions, cancellation, and refunds">
            <p>
              FundersAI offers free and paid subscription tiers. Paid subscriptions are billed through Razorpay
              on the cycle shown at checkout (monthly or annual).
            </p>
            <ul className="list-disc pl-5 space-y-1.5">
              <li>
                <span className="text-white font-medium">Cancellation:</span> You may cancel your subscription at
                any time from within the product. Cancellation takes effect at the end of the current billing
                period. You retain access to paid features until that date.
              </li>
              <li>
                <span className="text-white font-medium">Refunds:</span> FundersAI does not offer prorated
                refunds for unused portions of a billing period unless required by applicable law. If you
                believe you were charged in error, contact us via the feedback form within 14 days of the charge
                for review.
              </li>
              <li>
                <span className="text-white font-medium">Free tier:</span> The free tier may have usage limits
                (rate limits, token budgets) that are enforced automatically. These limits may change as the
                product evolves.
              </li>
            </ul>
          </Section>

          <Section title="Service changes">
            <p>
              Features, data sources, coverage, limits, and subscription offerings may change as the product
              evolves. We will make reasonable efforts to communicate material changes in advance. Continued use
              of the service after a material change constitutes acceptance of the updated terms.
            </p>
            <p>
              We may suspend or terminate accounts that violate these terms, with or without notice depending on
              the severity of the violation.
            </p>
          </Section>

          <Section title="Intellectual property">
            <p>
              FundersAI&apos;s software, design, and proprietary methodology are owned by FundersAI. Mutual fund data,
              official AMC documents, and index data remain the property of their respective sources (AMFI, AMCs,
              NSE, BSE). FundersAI does not claim ownership of third-party data.
            </p>
            <p>
              You may use research outputs for personal, non-commercial analysis. Systematic extraction,
              redistribution, or resale of data or outputs is not permitted without explicit written permission.
            </p>
          </Section>

          <Section title="Limitation of liability">
            <p>
              To the fullest extent permitted by applicable law, FundersAI is not liable for investment losses,
              decisions made in reliance on research outputs, data inaccuracies, service interruptions, or any
              indirect, incidental, or consequential damages arising from use of the platform.
            </p>
          </Section>

          <Section title="Governing law and jurisdiction">
            <p>
              These terms are governed by the laws of India. Any dispute arising from the use of FundersAI that
              cannot be resolved informally shall be subject to the exclusive jurisdiction of the courts of India.
            </p>
          </Section>

          <Section title="Contact">
            <p>
              For questions about these terms, use the in-product feedback form or visit the{' '}
              <Link href="/contact" className="text-[#82aff6] hover:text-[#b8d3ff]">Contact</Link> page.
            </p>
          </Section>

        </div>

        <div className="mt-10 flex flex-wrap gap-4 border-t border-white/10 pt-6 text-sm">
          <Link href="/" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">Home</Link>
          <Link href="/privacy" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">Privacy Policy</Link>
          <Link href="/contact" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">Contact</Link>
          <Link href="/feedback" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">Feedback form</Link>
        </div>
      </article>
    </main>
  );
}
