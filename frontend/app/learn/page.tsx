import Link from 'next/link';

export const metadata = {
  title: 'Learn | FundersAI Research',
  description: 'Educational resources and guides on Indian stock and mutual fund research. Learn how to compare mutual funds, read stock fundamentals, and understand risk metrics.',
};

const TOPICS = [
  {
    title: 'P/E Ratio Explained',
    description: 'Understand the Price-to-Earnings ratio and how to use it when analyzing Indian stocks.',
    slug: 'pe-ratio',
  },
  {
    title: 'Mutual Fund Comparison Guide',
    description: 'How to compare mutual funds, evaluate expense ratios, and analyze historical performance.',
    slug: 'mutual-fund-comparison',
  },
  {
    title: 'Understanding Alpha, Beta, and Sharpe Ratio',
    description: 'A guide to risk metrics for mutual funds and what they mean for your portfolio.',
    slug: 'alpha-beta-sharpe',
  },
  {
    title: 'Large Cap vs Flexi Cap Funds',
    description: 'Comparison of market cap strategies in Indian mutual funds to help you build a diversified portfolio.',
    slug: 'large-cap-vs-flexi-cap',
  },
  {
    title: 'Reading Stock Fundamentals',
    description: 'A beginner\'s guide to reading stock fundamentals, balance sheets, and earnings reports.',
    slug: 'reading-stock-fundamentals',
  }
];

export default function LearnIndexPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-serif text-4xl md:text-5xl font-semibold tracking-tight text-white mb-4">
          Investing Concepts & Guides
        </h1>
        <p className="text-lg text-slate-400 max-w-2xl">
          Understand key financial metrics and research concepts. Our educational resources help you make data-driven decisions when comparing stocks and mutual funds.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 mt-8">
        {TOPICS.map((topic) => (
          <Link href={`/learn/${topic.slug}`} key={topic.slug} className="group block p-6 rounded-2xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] hover:border-[#00FF9D]/40 transition-all shadow-sm">
            <h2 className="text-xl font-medium text-white group-hover:text-[#00FF9D] transition-colors mb-2">
              {topic.title}
            </h2>
            <p className="text-sm text-slate-400">
              {topic.description}
            </p>
          </Link>
        ))}
      </div>

      <div className="mt-12 p-6 rounded-2xl border border-[#00FF9D]/20 bg-[#00FF9D]/[0.05]">
        <h3 className="text-lg font-medium text-white mb-2">Ready to apply these concepts?</h3>
        <p className="text-sm text-slate-300 mb-4">
          Use FundersAI to compare mutual funds and stocks with verified, official-source evidence.
        </p>
        <Link href="/dashboard" className="inline-flex items-center justify-center rounded-lg bg-[#00FF9D] px-6 py-2.5 text-sm font-semibold text-black hover:bg-[#00FF9D]/90 transition">
          Start Researching
        </Link>
      </div>

      <div className="pt-8 text-center border-t border-white/10">
        <p className="text-xs text-slate-500">
          Disclaimer: FundersAI provides educational insights and data-driven research. The information provided here is not financial advice.
        </p>
      </div>
    </div>
  );
}
