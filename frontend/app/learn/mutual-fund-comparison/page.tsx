import type { Metadata } from 'next';
import Link from 'next/link';
import { ArticleJsonLd } from '@/components/seo/JsonLd';

export const metadata: Metadata = {
  title: 'Mutual Fund Comparison Guide | FundersAI Learn',
  description: 'How to compare mutual funds, evaluate expense ratios, and analyze historical performance.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/learn/mutual-fund-comparison',
  },
};

export default function MutualFundComparisonPage() {
  return (
    <>
      <ArticleJsonLd
        title="Mutual Fund Comparison Guide"
        description="How to compare mutual funds, evaluate expense ratios, and analyze historical performance."
        slug="mutual-fund-comparison"
      />
      <article className="prose prose-invert prose-slate max-w-none">
      <div className="mb-8">
        <Link href="/learn" className="text-[#00FF9D] hover:underline text-sm font-medium">
          &larr; Back to Learning Hub
        </Link>
      </div>
      
      <h1 className="text-3xl md:text-4xl font-serif font-semibold tracking-tight text-white mb-6">
        Mutual Fund Comparison Guide
      </h1>
      
      <div className="text-slate-300 space-y-6 leading-relaxed">
        <p>
          With thousands of mutual fund schemes available in India, choosing the right one can be overwhelming. Comparing funds requires looking past short-term returns and evaluating consistency, costs, and risk.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Key Metrics for Comparison</h2>
        
        <div className="space-y-6">
          <div className="bg-white/[0.02] p-5 rounded-xl border border-white/10">
            <h3 className="text-lg font-medium text-[#00FF9D] mb-2">1. Expense Ratio (TER)</h3>
            <p className="text-sm">
              The Total Expense Ratio is the annual fee charged by the Asset Management Company (AMC) to manage the fund. A lower TER is generally better as it directly impacts your net returns. Direct plans always have a lower TER than Regular plans.
            </p>
          </div>

          <div className="bg-white/[0.02] p-5 rounded-xl border border-white/10">
            <h3 className="text-lg font-medium text-[#00FF9D] mb-2">2. Rolling Returns</h3>
            <p className="text-sm">
              Instead of looking at point-to-point trailing returns (like &quot;1-Year Return&quot;), rolling returns give a clearer picture of a fund&apos;s consistency across different market cycles.
            </p>
          </div>

          <div className="bg-white/[0.02] p-5 rounded-xl border border-white/10">
            <h3 className="text-lg font-medium text-[#00FF9D] mb-2">3. Risk-Adjusted Returns</h3>
            <p className="text-sm">
              A fund that delivers 15% returns with extreme volatility might be worse than a fund delivering 12% returns with stability. Look at metrics like the Sharpe Ratio and Sortino Ratio to evaluate how much risk the fund manager took to generate those returns.
            </p>
          </div>

          <div className="bg-white/[0.02] p-5 rounded-xl border border-white/10">
            <h3 className="text-lg font-medium text-[#00FF9D] mb-2">4. Portfolio Overlap</h3>
            <p className="text-sm">
              When investing in multiple funds, check their portfolio overlap. If you buy two Flexi Cap funds that hold 80% of the same stocks, you aren&apos;t actually diversifying your portfolio.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Apples to Apples</h2>
        <p>
          Always compare funds within the same category. Comparing a Small Cap fund&apos;s returns to a Large Cap fund is misleading because they have entirely different risk profiles and regulatory constraints.
        </p>

        <div className="mt-12 p-6 rounded-2xl border border-[#00FF9D]/20 bg-[#00FF9D]/[0.05]">
          <h3 className="text-lg font-medium text-white mb-2">Compare Funds on FundersAI</h3>
          <p className="text-sm text-slate-300 mb-4">
            FundersAI provides a deterministic side-by-side comparison canvas for Indian mutual funds, showing expense ratios, risk metrics, and AUM in one clear view.
          </p>
          <Link href="/dashboard" className="inline-flex items-center justify-center rounded-lg bg-[#00FF9D] px-6 py-2.5 text-sm font-semibold text-black hover:bg-[#00FF9D]/90 transition">
            Open Comparison Canvas
          </Link>
        </div>
      </div>
    </article>
    </>
  );
}
