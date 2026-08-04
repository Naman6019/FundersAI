import Link from 'next/link';

export const metadata = {
  title: 'Large Cap vs Flexi Cap Funds | FundersAI Learn',
  description: 'Comparison of market cap strategies in Indian mutual funds to help you build a diversified portfolio.',
};

export default function MarketCapPage() {
  return (
    <article className="prose prose-invert prose-slate max-w-none">
      <div className="mb-8">
        <Link href="/learn" className="text-[#00FF9D] hover:underline text-sm font-medium">
          &larr; Back to Learning Hub
        </Link>
      </div>
      
      <h1 className="text-3xl md:text-4xl font-serif font-semibold tracking-tight text-white mb-6">
        Large Cap vs Flexi Cap Funds
      </h1>
      
      <div className="text-slate-300 space-y-6 leading-relaxed">
        <p>
          When building a mutual fund portfolio in India, two of the most popular equity categories are Large Cap and Flexi Cap funds. While both invest in equities, their regulatory constraints and risk profiles are quite different.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">What is a Large Cap Fund?</h2>
        <p>
          According to SEBI regulations, a Large Cap mutual fund must invest a minimum of 80% of its total assets in equity and equity-related instruments of large-cap companies (the top 100 companies in India by market capitalization).
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Pros:</strong> Stability, consistent dividends, lower volatility during market downturns, and high liquidity.</li>
          <li><strong>Cons:</strong> Lower growth potential compared to smaller companies. It&apos;s difficult for active fund managers to generate significant alpha over the Nifty 50 or Sensex indices.</li>
        </ul>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">What is a Flexi Cap Fund?</h2>
        <p>
          A Flexi Cap fund has the mandate to invest a minimum of 65% of its assets in equity, but the fund manager has complete flexibility to invest across large, mid, and small-cap stocks without any upper or lower limits.
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Pros:</strong> Dynamic allocation. The fund manager can shift money to large caps during volatile times and to mid/small caps during bull runs.</li>
          <li><strong>Cons:</strong> Heavily reliant on the fund manager&apos;s skill to make the right market cap calls. Can be more volatile than pure large-cap funds.</li>
        </ul>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Which one should you choose?</h2>
        <p>
          Many investors use a Flexi Cap fund as their core portfolio holding because it provides built-in diversification. However, conservative investors or those nearing their financial goals might prefer the stability of Large Cap funds (or a low-cost Nifty 50 Index fund).
        </p>

        <div className="mt-12 p-6 rounded-2xl border border-[#00FF9D]/20 bg-[#00FF9D]/[0.05]">
          <h3 className="text-lg font-medium text-white mb-2">Compare Categories on FundersAI</h3>
          <p className="text-sm text-slate-300 mb-4">
            Use the &quot;Explore by Category&quot; feature in FundersAI to list top Flexi Cap and Large Cap funds, and compare their 3-year returns side-by-side.
          </p>
          <Link href="/dashboard" className="inline-flex items-center justify-center rounded-lg bg-[#00FF9D] px-6 py-2.5 text-sm font-semibold text-black hover:bg-[#00FF9D]/90 transition">
            Go to Dashboard
          </Link>
        </div>
      </div>
    </article>
  );
}
