import type { Metadata } from 'next';
import Link from 'next/link';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import { MagicCard } from '@/components/ui/magic-card';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';

export const metadata: Metadata = {
  title: 'Pricing & Subscription Plans | FundersAI',
  description:
    'Choose the right plan for your research workflows. Transparent pricing for FundersAI Research Platform and Synthesis Report Studio (Free ₹0, Pro ₹99/mo, Ultra ₹199/mo).',
  keywords: [
    'FundersAI pricing',
    'Mutual fund research tool cost',
    'Synthesis studio subscription plans',
    'FundersAI Pro Ultra tier',
  ],
  alternates: {
    canonical: 'https://www.fundersai.co.in/pricing',
  },
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Pricing & Subscription Plans | FundersAI',
    description:
      'Simple, transparent pricing for institutional-grade Indian mutual fund & stock research.',
    url: 'https://www.fundersai.co.in/pricing',
    siteName: 'FundersAI',
  },
};

const faqs = [
  {
    q: 'How do daily and monthly token limits work?',
    a: 'Tokens represent AI research query usage across the chat, quantitative analysis, and synthesis engines. Daily budgets reset every night at midnight IST, while monthly budgets reset on your subscription renewal date.',
  },
  {
    q: 'What is the difference between Research Platform queries and Synthesis Studio reports?',
    a: 'Research Platform queries power interactive multi-turn chat and stock/fund inquiries. Synthesis Studio reports generate multi-page institutional side-by-side comparison reports with risk matrices, Mermaid diagrams, and 1-click PDF exports.',
  },
  {
    q: 'Can I upgrade or cancel my subscription at any time?',
    a: 'Yes! You can upgrade from Free to Pro or Ultra at any time. Subscriptions are billed monthly via Razorpay and can be managed directly in your Billing Dashboard.',
  },
  {
    q: 'Are payments processed securely via Razorpay?',
    a: 'All transactions are processed through Razorpay using official HMAC signature verification and 256-bit SSL encryption. We never store credit card or bank details on our servers.',
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#050810] text-[#dce8fa] flex flex-col selection:bg-blue-500/30 cyber-grid-bg relative">
      {/* Background Subtle Radial Aura */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-blue-600/10 blur-[140px] pointer-events-none rounded-full" />
      
      <EcosystemHeader />

      <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-16 relative z-10">
        {/* Breadcrumb */}
        <Breadcrumbs
          tone="synthesis"
          items={[
            { label: 'FundersAI', href: '/' },
            { label: 'Synthesis', href: '/synthesis' },
            { label: '[ PRICING_PLANS ]' },
          ]}
        />

        {/* Hero Header */}
        <div className="text-center space-y-4 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono font-medium">
            <span>⚡ UNIFIED RESEARCH &amp; SYNTHESIS SUBSCRIPTION</span>
          </div>
          <h1 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight leading-tight font-serif-display">
            Simple, Transparent Pricing. <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-cyan-400">
              No Hidden Fees.
            </span>
          </h1>
          <p className="text-sm sm:text-base text-gray-400 max-w-xl mx-auto leading-relaxed">
            One unified subscription unlocks both Research Platform AI query quotas and Synthesis Studio daily report creation.
          </p>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Free Tier Card */}
          <MagicCard className="p-8 bg-[#070b12]/80 border-gray-800/80 rounded-3xl flex flex-col justify-between space-y-8 backdrop-blur-xl">
            <div className="space-y-6">
              <div>
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-gray-400">Free Tier</span>
                <div className="flex items-baseline gap-1 mt-3">
                  <span className="text-5xl font-extrabold text-white font-mono">₹0</span>
                  <span className="text-xs text-gray-400 font-mono">/ forever</span>
                </div>
                <p className="text-xs text-gray-400 mt-3">Starter research limits for fund research &amp; synthesis reports.</p>
              </div>

              <div className="space-y-3 border-t border-gray-800/80 pt-6 text-xs text-gray-300">
                <div className="flex items-center gap-2.5">
                  <span className="text-blue-400 font-bold">✓</span>
                  <span><strong>1 report per day</strong> (Synthesis Studio)</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="text-blue-400 font-bold">✓</span>
                  <span>Token-based queries in Research platform</span>
                </div>
                <div className="flex items-center gap-2.5 text-gray-400">
                  <span className="text-blue-400 font-bold">✓</span>
                  <span>25k daily / 100k monthly AI tokens</span>
                </div>
                <div className="flex items-center gap-2.5 text-gray-400">
                  <span className="text-blue-400 font-bold">✓</span>
                  <span>Full dashboard &amp; factsheet research access</span>
                </div>
              </div>
            </div>

            <Link href="/login" className="w-full">
              <button className="w-full py-3 rounded-xl bg-gray-900 border border-gray-800 text-gray-300 font-mono font-bold text-xs hover:bg-gray-800 hover:text-white transition-all uppercase tracking-wider">
                Get Started Free
              </button>
            </Link>
          </MagicCard>

          {/* Pro Tier Card (Electric Cobalt Highlight) */}
          <MagicCard className="p-8 bg-[#070b12]/95 border-blue-500/60 rounded-3xl flex flex-col justify-between space-y-8 relative shadow-2xl shadow-blue-600/20 backdrop-blur-xl border-t-blue-500">
            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-blue-600 text-[10px] font-mono font-bold text-white uppercase tracking-wider shadow-md shadow-blue-900/40">
              Most Popular
            </div>

            <div className="space-y-6">
              <div>
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-blue-400">Pro Tier</span>
                <div className="flex items-baseline gap-1 mt-3">
                  <span className="text-5xl font-extrabold text-white font-mono">₹99</span>
                  <span className="text-xs text-gray-400 font-mono">/ month</span>
                </div>
                <p className="text-xs text-gray-400 mt-3">Higher limits for regular mutual-fund and stock research.</p>
              </div>

              <div className="space-y-3 border-t border-gray-800/80 pt-6 text-xs text-gray-200">
                <div className="flex items-center gap-2.5">
                  <span className="text-blue-400 font-bold">✓</span>
                  <span><strong>5 reports per day</strong> (Synthesis Studio)</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="text-blue-400 font-bold">✓</span>
                  <span><strong>10X Higher usage</strong> in Research platform</span>
                </div>
                <div className="flex items-center gap-2.5 text-gray-300">
                  <span className="text-blue-400 font-bold">✓</span>
                  <span>250k daily / 2M monthly AI tokens</span>
                </div>
                <div className="flex items-center gap-2.5 text-gray-300">
                  <span className="text-blue-400 font-bold">✓</span>
                  <span>Dashboard, Canvas &amp; Portfolio Overlap Tool</span>
                </div>
              </div>
            </div>

            <Link href="/billing" className="w-full">
              <button className="w-full py-3 rounded-xl bg-blue-600 text-white font-mono font-bold text-xs hover:bg-blue-500 transition-all shadow-lg shadow-blue-600/30 uppercase tracking-wider">
                Upgrade to Pro (₹99)
              </button>
            </Link>
          </MagicCard>

          {/* Ultra Tier Card */}
          <MagicCard className="p-8 bg-[#070b12]/90 border-cyan-500/50 rounded-3xl flex flex-col justify-between space-y-8 backdrop-blur-xl border-t-cyan-400">
            <div className="space-y-6">
              <div>
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">Ultra Tier</span>
                <div className="flex items-baseline gap-1 mt-3">
                  <span className="text-5xl font-extrabold text-white font-mono">₹199</span>
                  <span className="text-xs text-gray-400 font-mono">/ month</span>
                </div>
                <p className="text-xs text-gray-400 mt-3">Highest limits for heavy institutional research workflows.</p>
              </div>

              <div className="space-y-3 border-t border-gray-800/80 pt-6 text-xs text-gray-200">
                <div className="flex items-center gap-2.5">
                  <span className="text-cyan-400 font-bold">✓</span>
                  <span><strong>15 reports per day</strong> (Synthesis Studio)</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="text-cyan-400 font-bold">✓</span>
                  <span><strong>25X Higher usage than Free</strong> in Research</span>
                </div>
                <div className="flex items-center gap-2.5 text-gray-300">
                  <span className="text-cyan-400 font-bold">✓</span>
                  <span>750k daily / 6M monthly AI tokens</span>
                </div>
                <div className="flex items-center gap-2.5 text-gray-300">
                  <span className="text-cyan-400 font-bold">✓</span>
                  <span>Priority serverless PDF export &amp; budget</span>
                </div>
              </div>
            </div>

            <Link href="/billing" className="w-full">
              <button className="w-full py-3 rounded-xl bg-cyan-600 text-white font-mono font-bold text-xs hover:bg-cyan-500 transition-all shadow-lg shadow-cyan-600/30 uppercase tracking-wider">
                Upgrade to Ultra (₹199)
              </button>
            </Link>
          </MagicCard>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="text-center space-y-2">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-400">[ BILLING_FAQS ]</span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white font-serif-display">Frequently Asked Questions</h2>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, idx) => (
              <div key={idx} className="p-5 rounded-2xl bg-[#070b12]/80 border border-gray-800/80 space-y-2 backdrop-blur-md">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span className="text-xs font-mono text-blue-400">#0{idx + 1}</span>
                  <span>{faq.q}</span>
                </h3>
                <p className="text-xs text-gray-400 leading-relaxed pl-7">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
