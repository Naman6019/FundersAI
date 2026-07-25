import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Privacy Policy | FundersAI',
  description: 'How FundersAI handles account, research, feedback, and billing data.',
};

export default function PrivacyPage() {
  return (
    <main className="min-h-dvh bg-[#070b12] px-4 py-12 text-[#dce8fa] sm:px-6">
      <article className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#101724] p-6 shadow-2xl sm:p-10">
        <Link href="/" className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff]">
          ← FundersAI
        </Link>
        <h1 className="mt-6 text-3xl font-semibold tracking-tight text-white">Privacy Policy</h1>
        <p className="mt-2 text-sm text-[#7183a0]">Last updated: July 25, 2026</p>

        <div className="mt-8 space-y-7 text-sm leading-7 text-[#aebed6]">
          <section>
            <h2 className="text-lg font-semibold text-white">Information we handle</h2>
            <p className="mt-2">
              FundersAI processes account and profile details, saved research chats, feedback, subscription status,
              and limited operational metadata needed to provide and protect the service.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-white">How information is used</h2>
            <p className="mt-2">
              We use this information to authenticate users, deliver research features, save owned sessions, manage
              subscriptions, investigate failures, prevent abuse, and improve product quality.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-white">Service providers</h2>
            <p className="mt-2">
              Account, hosting, storage, payment, and model providers process only the information needed for their
              part of the service. Secret provider credentials stay on the server. Payment card details are handled
              by the checkout provider and are not stored by FundersAI.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold text-white">Your choices</h2>
            <p className="mt-2">
              You can sign out at any time. For questions about saved account information or a privacy request, use
              the in-product feedback form so the request can be reviewed securely.
            </p>
          </section>
        </div>

        <div className="mt-10 flex flex-wrap gap-4 border-t border-white/10 pt-6 text-sm">
          <Link href="/auth" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff]">
            Return to sign in
          </Link>
          <Link href="/feedback" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff]">
            Send feedback
          </Link>
        </div>
      </article>
    </main>
  );
}
