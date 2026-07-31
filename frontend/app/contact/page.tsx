import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Contact | FundersAI',
  description:
    'Get in touch with FundersAI for support, feedback, data queries, responsible disclosure, or privacy requests.',
};

export default function ContactPage() {
  return (
    <main className="min-h-dvh bg-[#070b12] px-4 py-12 text-[#dce8fa] sm:px-6">
      <article className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#101724] p-6 shadow-2xl sm:p-10">
        <Link href="/" className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
          ← FundersAI
        </Link>

        <h1 className="mt-6 text-3xl font-semibold tracking-tight text-white">Contact</h1>
        <p className="mt-2 text-sm text-[#7183a0]">We aim to respond within 2 business days.</p>

        <div className="mt-8 space-y-6 text-sm leading-7 text-[#aebed6]">

          {/* General support */}
          <section className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
            <h2 className="text-base font-semibold text-white">General support &amp; feedback</h2>
            <p className="mt-2 text-[#aebed6]">
              For questions about the product, data accuracy issues, feature requests, or account problems, use
              the in-product feedback form — it reaches us fastest and keeps the context attached.
            </p>
            <div className="mt-4">
              <Link
                href="/feedback"
                className="inline-flex items-center rounded-full bg-[#82aff6]/10 border border-[#82aff6]/20 px-4 py-2 text-sm font-semibold text-[#82aff6] hover:bg-[#82aff6]/20 transition-colors"
              >
                Open feedback form →
              </Link>
            </div>
          </section>

          {/* Privacy requests */}
          <section className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
            <h2 className="text-base font-semibold text-white">Privacy requests</h2>
            <p className="mt-2 text-[#aebed6]">
              For requests about your personal data — access, correction, deletion, or data export — use the
              feedback form and mark your message as a privacy request. This keeps the request on a secure,
              auditable channel.
            </p>
            <p className="mt-3 text-[#7183a0] text-xs">
              You do not need to be signed in to submit a privacy request. Include your registered email address
              so we can verify identity before acting.
            </p>
          </section>

          {/* Responsible disclosure */}
          <section className="rounded-xl border border-amber-400/15 bg-amber-400/[0.04] p-5">
            <h2 className="text-base font-semibold text-white">Responsible disclosure</h2>
            <p className="mt-2 text-[#aebed6]">
              If you find a security vulnerability, please report it privately before any public disclosure. Use
              the in-product feedback form and describe the issue, affected surface, and any reproduction steps.
              We will acknowledge receipt within 2 business days and coordinate a fix timeline with you.
            </p>
            <p className="mt-3 text-[#7183a0] text-xs">
              We do not operate a paid bug bounty programme at this stage, but we do credit responsible reporters
              (with permission) after a fix is deployed.
            </p>
          </section>

          {/* Data queries */}
          <section className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
            <h2 className="text-base font-semibold text-white">Data queries</h2>
            <p className="mt-2 text-[#aebed6]">
              If you notice a data discrepancy — a stale field, an incorrect metric, or a missing official
              document — use the feedback form and include the fund name, field, and the value you expected to
              see along with your source. We take data accuracy reports seriously.
            </p>
          </section>

        </div>

        <div className="mt-8 rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 text-xs text-[#7183a0]">
          <p>
            <span className="font-semibold text-white/60">Operating context: </span>
            FundersAI is an early-access product. Response times may vary. We prioritise security and privacy
            requests above general support.
          </p>
        </div>

        <div className="mt-8 flex flex-wrap gap-4 border-t border-white/10 pt-6 text-sm">
          <Link href="/" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            Home
          </Link>
          <Link href="/about" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            About
          </Link>
          <Link href="/privacy" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            Privacy Policy
          </Link>
          <Link href="/feedback" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            Feedback form
          </Link>
        </div>
      </article>
    </main>
  );
}
