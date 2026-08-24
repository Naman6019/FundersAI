import type { Metadata } from 'next';
import Link from 'next/link';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';

export const metadata: Metadata = {
  title: 'Contact | FundersAI',
  description:
    'Get in touch with FundersAI for support, feedback, data queries, responsible disclosure, or privacy requests.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/contact',
  },
};

export default function ContactPage() {
  return (
    <div className="min-h-dvh bg-[#070b12] text-[#dce8fa] flex flex-col justify-between">
      <EcosystemHeader />

      <main className="px-4 py-12 sm:px-6 flex-1">
        <article className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#101724] p-6 shadow-2xl sm:p-10">
          <Link href="/" className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            ← Home
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
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Link
                href="/feedback"
                className="inline-flex items-center rounded-full bg-[#82aff6]/10 border border-[#82aff6]/20 px-4 py-2 text-sm font-semibold text-[#82aff6] hover:bg-[#82aff6]/20 transition-colors"
              >
                Open feedback form →
              </Link>
              <a
                href="mailto:support@fundersai.co.in"
                className="inline-flex items-center rounded-full bg-white/5 border border-white/10 px-4 py-2 text-sm font-semibold text-white hover:bg-white/10 transition-colors font-mono"
              >
                ✉ Email support@fundersai.co.in
              </a>
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
      </article>
      </main>

      <PublicFooter />
    </div>
  );
}
