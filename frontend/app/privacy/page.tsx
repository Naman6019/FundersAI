import type { Metadata } from 'next';
import Link from 'next/link';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';

export const metadata: Metadata = {
  title: 'Privacy Policy | FundersAI',
  description:
    'How FundersAI collects, uses, and protects your data. Covers third-party service providers, data retention, prompt handling, account deletion, cookies, and privacy request contacts.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/privacy',
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

export default function PrivacyPage() {
  return (
    <div className="min-h-dvh bg-[#070b12] text-[#dce8fa] flex flex-col justify-between">
      <EcosystemHeader />

      <main className="px-4 py-12 sm:px-6 flex-1">
        <article className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#101724] p-6 shadow-2xl sm:p-10">
          <Link href="/" className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            ← Home
          </Link>
        <h1 className="mt-6 text-3xl font-semibold tracking-tight text-white">Privacy Policy</h1>
        <p className="mt-2 text-sm text-[#7183a0]">Last updated: July 31, 2026</p>

        <div className="mt-8 space-y-8 text-sm leading-7 text-[#aebed6]">

          <Section title="Information we handle">
            <p>
              FundersAI processes the following categories of information to operate the service:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-[#aebed6]">
              <li><span className="text-white font-medium">Account data</span> — email address, name (if provided), and authentication tokens via Supabase.</li>
              <li><span className="text-white font-medium">Profile data</span> — subscription tier and role (free, pro, ultra; user, admin, tester).</li>
              <li><span className="text-white font-medium">Research sessions</span> — saved chat sessions and messages you choose to keep, stored in Supabase and accessible only by your account.</li>
              <li><span className="text-white font-medium">Feedback</span> — ratings and text you submit via the in-product feedback form.</li>
              <li><span className="text-white font-medium">Billing data</span> — subscription status and payment events processed by Razorpay. Card details are handled entirely by Razorpay and are never stored by FundersAI.</li>
              <li><span className="text-white font-medium">Operational metadata</span> — request timestamps, IP addresses (for rate limiting), and error logs needed to run and protect the service. These are not used for advertising.</li>
            </ul>
          </Section>

          <Section title="How information is used">
            <p>
              We use this information to: authenticate you, deliver research features, save your owned sessions,
              manage your subscription, investigate failures, prevent abuse, and improve product quality.
              FundersAI does not use your data for advertising, does not sell it to third parties, and does not
              share it with data brokers.
            </p>
          </Section>

          <Section title="Third-party service providers">
            <p>
              The following providers process data on our behalf. Each receives only the information needed for
              their specific function:
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse mt-2">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-2 pr-4 font-semibold text-white">Provider</th>
                    <th className="text-left py-2 pr-4 font-semibold text-white">Purpose</th>
                    <th className="text-left py-2 font-semibold text-white">Data shared</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {[
                    ['Supabase', 'Database, authentication, RLS-protected storage', 'Account, sessions, feedback'],
                    ['Vercel', 'Frontend hosting and edge functions', 'Request metadata, IP (rate limiting)'],
                    ['Google Cloud Run', 'Backend API hosting', 'Request content, IP'],
                    ['OpenAI', 'Text embeddings for document search', 'Document chunks only (no user queries to embedding API)'],
                    ['OpenRouter / Groq', 'LLM inference for chat synthesis', 'Research query and retrieved context for the current request'],
                    ['Razorpay', 'Subscription payments', 'Billing details, plan selection'],
                    ['Cloudflare R2', 'Cold storage for AMC documents', 'AMC disclosure documents only'],
                    ['Upstash (Redis)', 'Rate limiting', 'Request counts keyed by user ID or IP'],
                    ['Langfuse', 'Optional LLM tracing (feature-flagged)', 'Prompt and completion traces when enabled'],
                  ].map(([provider, purpose, data]) => (
                    <tr key={provider as string}>
                      <td className="py-2 pr-4 font-medium text-white align-top">{provider}</td>
                      <td className="py-2 pr-4 text-[#aebed6] align-top">{purpose}</td>
                      <td className="py-2 text-[#7183a0] align-top">{data}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <Section title="Prompt handling and model training">
            <p>
              Research queries you send to FundersAI are forwarded to OpenRouter or Groq for LLM inference. These
              providers process the query within the current request context.
            </p>
            <p>
              <span className="text-white font-medium">FundersAI does not use your queries to train its own models.</span> Whether your queries are used for training by OpenRouter or Groq depends on your agreement with those providers and their current data use policies. We recommend reviewing{' '}
              <a href="https://openrouter.ai/privacy" target="_blank" rel="noopener noreferrer" className="text-[#82aff6] hover:text-[#b8d3ff]">OpenRouter&apos;s privacy policy</a>
              {' '}and{' '}
              <a href="https://groq.com/privacy-policy/" target="_blank" rel="noopener noreferrer" className="text-[#82aff6] hover:text-[#b8d3ff]">Groq&apos;s privacy policy</a>
              {' '}if this is a concern.
            </p>
            <p>
              Text embeddings sent to OpenAI are document chunks from official AMC disclosures only — not your personal queries.
            </p>
          </Section>

          <Section title="Data retention">
            <p>The following retention periods apply:</p>
            <ul className="list-disc pl-5 space-y-1.5">
              <li><span className="text-white font-medium">Chat sessions and messages</span> — Kept until you delete them or close your account. You can delete individual sessions from within the workspace.</li>
              <li><span className="text-white font-medium">Account data</span> — Retained while your account is active and for up to 30 days after deletion to allow recovery and complete billing cycles.</li>
              <li><span className="text-white font-medium">Feedback</span> — Retained for product quality review. Anonymous (post-sign-out) feedback is retained without account linkage.</li>
              <li><span className="text-white font-medium">Operational logs</span> — Retained for up to 90 days for security, debugging, and rate-limit enforcement.</li>
              <li><span className="text-white font-medium">Billing events</span> — Retained as required by applicable financial regulations and Razorpay&apos;s record-keeping obligations.</li>
            </ul>
          </Section>

          <Section title="Cookies and analytics">
            <p>
              FundersAI uses cookies and browser storage for session authentication (via Supabase Auth) and to
              remember UI preferences. We do not use third-party advertising or tracking cookies.
            </p>
            <p>
              Basic operational analytics (page loads, error rates) may be collected via Vercel. No cross-site
              tracking or behavioural profiling is performed.
            </p>
          </Section>

          <Section title="Age requirements">
            <p>
              FundersAI is not directed at children under the age of 18. If you believe a minor has created an
              account, please contact us via the in-product feedback form so we can delete the account.
            </p>
          </Section>

          <Section title="Your choices and rights">
            <p>You can:</p>
            <ul className="list-disc pl-5 space-y-1.5">
              <li>Delete individual chat sessions directly from the workspace.</li>
              <li>Sign out at any time to end your active session.</li>
              <li>Request access to, correction of, or deletion of your personal data by submitting a request through the in-product feedback form. Include your registered email address for verification.</li>
              <li>Request a data export (structured copy of your chat history and account data) via the feedback form.</li>
              <li>Close your account by contacting us through the feedback form. Account data is deleted within 30 days.</li>
            </ul>
            <p>
              Privacy requests do not require you to be signed in. You may submit them from any browser.
            </p>
          </Section>

          <Section title="Security">
            <p>
              User-owned data (chat sessions, messages) is protected by Supabase Row-Level Security policies
              that enforce <code className="text-xs bg-white/5 px-1 py-0.5 rounded">auth.uid() = user_id</code> at the database level.
              Service-role credentials never leave the server. All connections use TLS.
            </p>
            <p>
              If you discover a security vulnerability, please report it privately via the in-product feedback
              form before any public disclosure. See the{' '}
              <Link href="/contact" className="text-[#82aff6] hover:text-[#b8d3ff]">Contact</Link> page for details.
            </p>
          </Section>

          <Section title="Changes to this policy">
            <p>
              We will update this policy when our data practices change in a material way. The &ldquo;Last updated&rdquo; date at
              the top of this page reflects the most recent revision. Continued use of the service after a policy
              update constitutes acceptance of the updated terms.
            </p>
          </Section>

        </div>
      </article>
      </main>

      <PublicFooter />
    </div>
  );
}
