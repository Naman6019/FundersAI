import type { Metadata } from 'next';
import Link from 'next/link';
import PublicHeader from '@/components/layout/PublicHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import { MagicCard } from '@/components/ui/magic-card';

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
  openGraph: {
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
    <div className="min-h-screen bg-[#070b12] text-[#dce8fa] flex flex-col selection:bg-blue-500/30">
      <PublicHeader />

      <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-20 w-full space-y-16">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
          <Link href="/" className="hover:text-emerald-400">Home</Link>
          <span>/</span>
          <span className="text-gray-200">Billing</span>
          <span>/</span>
          <span className="text-emerald-400">Pricing Plans</span>
        </div>

        {/* Hero Header */}
        <div className="text-center space-y-4 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-medium">
            <span>⚡ Unified Research &amp; Synthesis Subscription</span>
          </div>
          <h1 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight leading-tight">
            Simple, Transparent Pricing. <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400">
              No Hidden Fees.
            </span>
          </h1>
          <p className="text-sm sm:text-base text-gray-400 max-w-xl mx-auto leading-relaxed">
            One subscription unlocks both Research Platform token quotas and Synthesis Studio daily report creation.
          </p>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Free Tier Card */}
          <MagicCard className="p-8 bg-gray-950/80 border-gray-800 rounded-3xl flex flex-col justify-between space-y-8">
            <div className="space-y-6">
              <div>
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-gray-400">Free Tier</span>
                <div className="flex items-baseline gap-1 mt-3">
                  <span className="text-5xl font-extrabold text-white">₹0</span>
                  <span className="text-xs text-gray-400">/ forever</span>
                </div>
                <p className="text-xs text-gray-400 mt-3">Starter research limits for fund research &amp; synthesis reports.</p>
              </div>

              <div className="space-y-3 border-t border-gray-900 pt-6 text-xs text-gray-300">
                <div className="flex items-center gap-2.5">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>1 report per day</strong> (Synthesis Studio)</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>Token-based queries in Research platform</span>
                </div>
                <div className="flex items-center gap-2.5 text-gray-400">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>25k daily / 100k monthly AI tokens</span>
                </div>
                <div className="flex items-center gap-2.5 text-gray-400">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>Full dashboard &amp; factsheet research access</span>
                </div>
              </div>
            </div>

            <Link href="/login" className="w-full">
              <button className="w-full py-3 rounded-xl bg-gray-900 border border-gray-800 text-gray-300 font-medium text-xs hover:bg-gray-800 hover:text-white transition-all">
                Get Started Free
              </button>
            </Link>
          </MagicCard>

          {/* Pro Tier Card */}
          <MagicCard className="p-8 bg-gray-950/90 border-emerald-500/50 rounded-3xl flex flex-col justify-between space-y-8 relative shadow-2xl shadow-emerald-500/10">
            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-emerald-500 text-[10px] font-mono font-bold text-black uppercase tracking-wider shadow-sm">
              Most Popular
            </div>

            <div className="space-y-6">
              <div>
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400">Pro Tier</span>
                <div className="flex items-baseline gap-1 mt-3">
                  <span className="text-5xl font-extrabold text-white">₹99</span>
                  <span className="text-xs text-gray-400">/ month</span>
                </div>
                <p className="text-xs text-gray-400 mt-3">Higher limits for regular mutual-fund and stock research.</p>
              </div>

              <div className="space-y-3 border-t border-gray-900 pt-6 text-xs text-gray-200">
                <div className="flex items-center gap-2.5">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>5 reports per day</strong> (Synthesis Studio)</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>10X Higher usage</strong> in Research platform</span>
                </div>
                <div className="flex items-center gap-2.5 text-gray-300">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>250k daily / 2M monthly AI tokens</span>
                </div>
                <div className="flex items-center gap-2.5 text-gray-300">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>Dashboard, Canvas &amp; Portfolio Overlap Tool</span>
                </div>
              </div>
            </div>

            <Link href="/billing" className="w-full">
              <button className="w-full py-3 rounded-xl bg-emerald-500 text-black font-bold text-xs hover:bg-emerald-400 transition-all shadow-lg shadow-emerald-500/25">
                Upgrade to Pro (₹99)
              </button>
            </Link>
          </MagicCard>

          {/* Ultra Tier Card */}
          <MagicCard className="p-8 bg-gray-950/80 border-cyan-500/40 rounded-3xl flex flex-col justify-between space-y-8">
            <div className="space-y-6">
              <div>
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">Ultra Tier</span>
                <div className="flex items-baseline gap-1 mt-3">
                  <span className="text-5xl font-extrabold text-white">₹199</span>
                  <span className="text-xs text-gray-400">/ month</span>
                </div>
                <p className="text-xs text-gray-400 mt-3">Highest limits for heavy institutional research workflows.</p>
              </div>

              <div className="space-y-3 border-t border-gray-900 pt-6 text-xs text-gray-200">
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
              <button className="w-full py-3 rounded-xl bg-cyan-600 text-white font-bold text-xs hover:bg-cyan-500 transition-all">
                Upgrade to Ultra (₹199)
              </button>
            </Link>
          </MagicCard>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="text-center space-y-2">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400">Billing FAQs</span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white">Frequently Asked Questions</h2>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, idx) => (
              <div key={idx} className="p-5 rounded-2xl bg-gray-950/80 border border-gray-800 space-y-2">
                <h3 className="text-sm font-bold text-white">{faq.q}</h3>
                <p className="text-xs text-gray-400 leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
