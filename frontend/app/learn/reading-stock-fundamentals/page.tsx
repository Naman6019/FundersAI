import type { Metadata } from 'next';
import Link from 'next/link';
import { ArticleJsonLd } from '@/components/seo/JsonLd';

export const metadata: Metadata = {
  title: 'Reading Stock Fundamentals | FundersAI Learn',
  description: 'A beginner\'s guide to reading stock fundamentals, balance sheets, and earnings reports.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/learn/reading-stock-fundamentals',
  },
};

export default function StockFundamentalsPage() {
  return (
    <>
      <ArticleJsonLd
        title="Reading Stock Fundamentals"
        description="A beginner's guide to reading stock fundamentals, balance sheets, and earnings reports."
        slug="reading-stock-fundamentals"
      />
      <article className="prose prose-invert prose-slate max-w-none">
      <div className="mb-8">
        <Link href="/learn" className="text-[#00FF9D] hover:underline text-sm font-medium">
          &larr; Back to Learning Hub
        </Link>
      </div>
      
      <h1 className="text-3xl md:text-4xl font-serif font-semibold tracking-tight text-white mb-6">
        Reading Stock Fundamentals
      </h1>
      
      <div className="text-slate-300 space-y-6 leading-relaxed">
        <p>
          Fundamental analysis is the process of evaluating a company&apos;s financial health, management, and market position to determine its intrinsic value. While it sounds intimidating, focusing on a few key metrics can give you a clear picture of a company&apos;s standing.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">1. Revenue & Profit Growth</h2>
        <p>
          Look at the top line (Revenue/Sales) and bottom line (Net Profit) over the last 3-5 years. 
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li>Are sales growing consistently?</li>
          <li>Is the profit growing faster or slower than sales? (If profit grows slower, margins are shrinking).</li>
        </ul>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">2. Debt-to-Equity Ratio</h2>
        <p>
          This metric tells you how much debt a company is using to finance its assets relative to the value of shareholders&apos; equity. 
        </p>
        <p>
          A Debt-to-Equity ratio of greater than 1 means the company has more debt than equity. While acceptable in capital-intensive industries (like telecom or infrastructure), a high debt load can be dangerous during economic downturns when interest rates rise.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">3. Return on Equity (ROE) & Return on Capital Employed (ROCE)</h2>
        <p>
          These efficiency ratios measure how well the company uses its capital to generate profits.
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>ROE:</strong> Measures profitability against shareholders&apos; equity. Consistently high ROE (15%+) is a sign of a strong business moat.</li>
          <li><strong>ROCE:</strong> Measures profitability against total capital employed (Equity + Debt). It&apos;s a better metric than ROE for companies with significant debt.</li>
        </ul>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">4. Operating Profit Margin (OPM)</h2>
        <p>
          OPM shows what percentage of revenue is left after paying for variable costs of production (like wages and raw materials). A rising OPM indicates the company has pricing power or is becoming more efficient.
        </p>

        <div className="mt-12 p-6 rounded-2xl border border-[#00FF9D]/20 bg-[#00FF9D]/[0.05]">
          <h3 className="text-lg font-medium text-white mb-2">Analyze Fundamentals Instantly</h3>
          <p className="text-sm text-slate-300 mb-4">
            FundersAI provides structured views of balance sheets, income statements, and cash flows for Indian stocks, along with AI explanations of what the numbers mean.
          </p>
          <Link href="/dashboard" className="inline-flex items-center justify-center rounded-lg bg-[#00FF9D] px-6 py-2.5 text-sm font-semibold text-black hover:bg-[#00FF9D]/90 transition">
            Analyze a Stock
          </Link>
        </div>
      </div>
    </article>
    </>
  );
}
