import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Terms of Use | FundersAI',
  description: 'Terms for using the FundersAI research workspace.',
};

export default function TermsPage() {
  return (
    <main className="min-h-dvh bg-[#070b12] px-4 py-12 text-[#dce8fa] sm:px-6">
      <article className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#101724] p-6 shadow-2xl sm:p-10">
        <Link href="/" className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff]">
          ← FundersAI
        </Link>
        <h1 className="mt-6 text-3xl font-semibold tracking-tight text-white">Terms of Use</h1>
        <p className="mt-2 text-sm text-[#7183a0]">Last updated: July 25, 2026</p>

        <div className="mt-8 space-y-7 text-sm leading-7 text-[#aebed6]">
          <section>
            <h2 className="text-lg font-semibold text-white">Research use only</h2>
            <p className="mt-2">
              FundersAI provides general market research and comparison tools. It does not provide personalized
              investment, legal, or tax advice. Verify important information before making a financial decision.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-white">Data limitations</h2>
            <p className="mt-2">
              Market and mutual-fund data may be delayed, incomplete, unavailable, or affected by source changes.
              Freshness and coverage indicators are part of the research output and should be considered when using it.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-white">Account responsibility</h2>
            <p className="mt-2">
              Keep your sign-in details secure and use the service only through your own account. Do not attempt to
              bypass access controls, disrupt the service, or use it for unlawful activity.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-white">Service changes</h2>
            <p className="mt-2">
              Features, data sources, limits, and subscription offerings may change as the product evolves. Material
              changes should be reflected in the product and these terms.
            </p>
          </section>
        </div>

        <div className="mt-10 flex flex-wrap gap-4 border-t border-white/10 pt-6 text-sm">
          <Link href="/auth" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff]">
            Return to sign in
          </Link>
          <Link href="/privacy" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff]">
            Privacy Policy
          </Link>
        </div>
      </article>
    </main>
  );
}
