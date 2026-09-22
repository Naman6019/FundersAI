import type { Metadata } from 'next';
import Link from 'next/link';
import { ArticleJsonLd } from '@/components/seo/JsonLd';

export const metadata: Metadata = {
  title: 'P/E Ratio Explained: Formula, PEG, and How to Use It in Indian Stocks | FundersAI',
  description:
    'What the Price-to-Earnings ratio measures, how to calculate it, why high and low P/E differ by sector, how the PEG ratio and earnings yield complete the picture, and the limits of using P/E to judge Indian stocks and mutual funds.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/learn/pe-ratio',
  },
  openGraph: {
    title: 'P/E Ratio Explained | FundersAI Learn',
    description:
      'The P/E ratio formula, sector context, PEG ratio, earnings yield, and the traps that make a low P/E look cheaper than it is.',
    url: 'https://www.fundersai.co.in/learn/pe-ratio',
  },
};

const FAQS = [
  {
    q: 'What is a good P/E ratio?',
    a: 'There is no universally good P/E. It only means something relative to a company\'s own history, its sector peers, and its expected earnings growth. A P/E of 30 can be cheap for a company growing earnings 30% a year, and a P/E of 12 can be expensive for a company whose earnings are shrinking. Read it as a comparison, never as a pass/fail score.',
  },
  {
    q: 'Should I buy stocks with a low P/E ratio?',
    a: 'A low P/E is a starting point for research, not a buy signal. It frequently reflects a real problem the market has already priced in: falling earnings, high debt, governance concerns, or a structurally declining industry. This is why value investors pair a low P/E with balance-sheet and cash-flow checks before acting.',
  },
  {
    q: 'What does a high P/E ratio mean?',
    a: 'A high P/E means the market is paying more for each rupee of current earnings. That is justified when earnings are expected to grow quickly, and unjustified when growth stalls. High-P/E stocks are more sensitive to disappointment because much of their price already reflects future growth that has not yet arrived.',
  },
  {
    q: 'What is the difference between trailing and forward P/E?',
    a: 'Trailing P/E uses the last twelve months (TTM) of reported earnings, so it is based on facts. Forward P/E uses projected earnings for the next twelve months, so it is based on estimates that may be revised or wrong. Trailing is verifiable; forward is more relevant to future returns but far less certain.',
  },
  {
    q: 'Can you use a P/E ratio for mutual funds?',
    a: 'Not directly. A mutual fund is a portfolio of many companies, so it has no single earnings figure. What is quoted instead is the weighted average P/E of its holdings, which tells you whether the portfolio leans toward expensive or inexpensive stocks. Because schemes disclose holdings only monthly, any fund P/E is a point-in-time approximation of the underlying basket.',
  },
];

const SECTOR_ROWS: Array<[string, string, string]> = [
  ['Fast-moving consumer goods', 'Higher', 'Stable, predictable demand and pricing power let the market pay up for certainty.'],
  ['Information technology', 'Higher', 'Asset-light models, high cash conversion, and export-linked earnings growth.'],
  ['Financial services / banking', 'Moderate', 'Earnings are driven by net interest margins and credit cycles rather than a growth premium.'],
  ['Automobiles', 'Moderate', 'Cyclical demand; P/E swings sharply across the cycle.'],
  ['Metals, mining, cement', 'Lower', 'Commodity prices drive earnings, so profits are cyclical and less predictable.'],
  ['Public-sector undertakings', 'Lower', 'Slower growth expectations and policy influence keep the multiple compressed.'],
];

export default function PERatioPage() {
  return (
    <>
      <ArticleJsonLd
        title="P/E Ratio Explained: Formula, PEG, and How to Use It in Indian Stocks"
        description="What the Price-to-Earnings ratio measures, why high and low P/E differ by sector, how the PEG ratio and earnings yield complete the picture, and the limits of using P/E."
        slug="pe-ratio"
        faqs={FAQS}
      />
      <article className="prose prose-invert prose-slate max-w-none">
      <div className="mb-8">
        <Link href="/learn" className="text-[#00FF9D] hover:underline text-sm font-medium">
          &larr; Back to Learning Hub
        </Link>
      </div>

      <h1 className="text-3xl md:text-4xl font-serif font-semibold tracking-tight text-white mb-6">
        P/E Ratio Explained
      </h1>

      <div className="text-slate-300 space-y-6 leading-relaxed">
        <p>
          The <strong>Price-to-Earnings (P/E) ratio</strong> is the most widely quoted valuation metric in
          equity investing. It answers one narrow but useful question: for every ₹1 of profit a company
          currently earns, how many rupees is the market willing to pay?
        </p>
        <p>
          That single number becomes genuinely useful only once you know what it is built from, what
          it is being compared against, and where it misleads. This guide covers all three.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">How is the P/E ratio calculated?</h2>
        <p>The formula is simple:</p>
        <div className="bg-white/[0.04] p-4 rounded-lg border border-white/10 font-mono text-center text-[#b3ffdb]">
          P/E Ratio = Market Price per Share ÷ Earnings per Share (EPS)
        </div>
        <p>
          The same number can be written the other way up, which is often more intuitive: it is the
          market capitalisation divided by total net profit.
        </p>
        <p>
          <strong>Worked example.</strong> A company trades at ₹500 per share and earned ₹25 per share
          over the last twelve months. Its P/E is 500 ÷ 25 = <strong>20</strong>. Equivalently, the
          market is paying ₹20 for each ₹1 of annual profit.
        </p>
        <p>
          The reciprocal of the P/E is the <strong>earnings yield</strong> — here, 25 ÷ 500 = 5%. That
          framing is helpful because it puts a stock on the same footing as a bond or a fixed deposit:
          a 5% earnings yield means the company currently earns 5% of its market price each year, before
          any growth and before considering how much of that profit is returned to shareholders.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Trailing vs forward P/E</h2>
        <p>
          Two P/E figures are quoted for the same company, and confusing them is one of the most common
          errors in valuation.
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Trailing P/E (TTM):</strong> uses the last twelve months of <em>reported</em> earnings.
            It is backward-looking but verifiable, because it rests on audited figures.
          </li>
          <li>
            <strong>Forward P/E:</strong> uses <em>projected</em> earnings for the next twelve months.
            It is forward-looking and more relevant to future returns, but it depends on estimates that
            analysts revise — sometimes by a lot, and usually after the price has already moved.
          </li>
        </ul>
        <p>
          When a forward P/E is much lower than the trailing P/E, the market expects a sharp earnings
          increase. That expectation is the entire investment case, and it can fail. When the two are
          close, growth is expected to be steady.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">What does a high or low P/E mean?</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>High P/E:</strong> the market expects strong future earnings growth, or it is paying
            a premium for stability and quality. It can also mean the stock is simply overvalued. Growth
            companies, and companies with highly predictable revenues, generally carry higher multiples.
          </li>
          <li>
            <strong>Low P/E:</strong> the market expects little growth, or it is pricing in a specific
            risk — falling margins, high debt, governance issues, or a shrinking industry. Value investors
            screen for low P/E, but the ratio alone does not tell you whether the discount is an
            opportunity or a warning.
          </li>
        </ul>
        <p className="text-sm italic text-slate-400">
          The trap is symmetry. A high P/E is not automatically bad, and a low P/E is not automatically
          good. Each has to be explained by something else in the business.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">P/E differs by sector, and that is normal</h2>
        <p>
          Comparing the P/E of a software company to a steel manufacturer tells you almost nothing. Sectors
          earn different multiples because their earnings have different quality, predictability and growth
          profiles.
        </p>
        <div className="overflow-x-auto rounded-lg border border-white/10">
          <table className="w-full text-sm">
            <caption className="text-left p-3 text-xs text-slate-400">
              Typical P/E positioning by sector. Indicative only — individual companies vary widely, and
              no figure here is a recommendation.
            </caption>
            <thead className="bg-white/[0.04]">
              <tr>
                <th scope="col" className="text-left p-3 font-semibold text-white">Sector</th>
                <th scope="col" className="text-left p-3 font-semibold text-white">Typical P/E</th>
                <th scope="col" className="text-left p-3 font-semibold text-white">Why</th>
              </tr>
            </thead>
            <tbody>
              {SECTOR_ROWS.map(([sector, level, why]) => (
                <tr key={sector} className="border-t border-white/10">
                  <th scope="row" className="text-left p-3 font-medium text-white">{sector}</th>
                  <td className="p-3">{level}</td>
                  <td className="p-3 text-slate-400">{why}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">The PEG ratio: adding growth to the picture</h2>
        <p>
          Because a bare P/E ignores growth, the <strong>PEG ratio</strong> divides it by the expected
          annual earnings growth rate:
        </p>
        <div className="bg-white/[0.04] p-4 rounded-lg border border-white/10 font-mono text-center text-[#b3ffdb]">
          PEG = P/E ÷ Expected Annual Earnings Growth (%)
        </div>
        <p>
          <strong>Worked example.</strong> Company A has a P/E of 30 and expected growth of 25% a year:
          PEG = 30 ÷ 25 = 1.2. Company B has a P/E of 15 and expected growth of 8%: PEG = 15 ÷ 8 = 1.88.
          On P/E alone, B looks cheaper. On PEG, A looks cheaper, because you are paying less per unit of
          expected growth.
        </p>
        <p>
          As a rough convention, a PEG near 1 is treated as fairly valued, below 1 as potentially
          undervalued relative to growth, and above 1 as paying a premium. Treat this with caution: the
          denominator is a forecast, so a PEG is only as good as the growth estimate inside it.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Context is everything</h2>
        <p>A P/E should never be read in isolation. Always compare it against:</p>
        <ol className="list-decimal pl-6 space-y-2">
          <li>
            <strong>Sector peers.</strong> A software company will naturally trade at a higher P/E than a
            cement producer. Compare like with like.
          </li>
          <li>
            <strong>The company&apos;s own history.</strong> Compare today&apos;s P/E with its 3-year and
            5-year average. A stock at 20 may be expensive if it has traded at 12 for years, and cheap if
            it normally trades at 35.
          </li>
          <li>
            <strong>The broader market.</strong> In a broadly expensive market, an average-looking P/E may
            still be a relative bargain — and vice versa.
          </li>
          <li>
            <strong>Earnings quality.</strong> Profits inflated by one-off gains, asset sales or accounting
            changes produce a misleadingly low P/E. Check that earnings are recurring.
          </li>
        </ol>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Where P/E misleads</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Negative or near-zero earnings.</strong> A loss-making company has no meaningful P/E at
            all; the ratio is undefined or wildly negative. Screens that rank by lowest P/E will silently
            distort in these cases.
          </li>
          <li>
            <strong>Cyclical businesses.</strong> At the top of a commodity cycle, earnings are at a peak
            and the P/E looks low — precisely when the cycle is about to turn. At the bottom, a high P/E
            can mark the best entry point. This inversion is why cyclical investors look at price-to-book
            and through-cycle margins instead.
          </li>
          <li>
            <strong>One-off distortions.</strong> A single large gain or write-down can swing the ratio for
            a year without saying anything about the underlying business.
          </li>
          <li>
            <strong>Accounting differences.</strong> Two companies reporting under different policies, or
            with different capital structures, are not directly comparable on P/E alone.
          </li>
        </ul>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">P/E inside mutual funds</h2>
        <p>
          A mutual fund has no earnings of its own, so it has no P/E. What is often quoted is the weighted
          average P/E of the stocks it holds, which is a useful character sketch: a portfolio P/E well
          above its category average suggests a growth-tilted, possibly more expensive basket, while a
          lower figure suggests a value tilt.
        </p>
        <p>
          Two caveats matter. First, schemes disclose holdings only monthly, so any portfolio P/E is a
          point-in-time approximation rather than a live figure. Second, a low portfolio P/E does not
          predict higher returns — it describes what the manager has chosen to own, not what the market
          will do next.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Frequently asked questions</h2>
        <div className="space-y-4">
          {FAQS.map((faq) => (
            <div key={faq.q} className="rounded-lg border border-white/10 bg-white/[0.02] p-5 space-y-2">
              <h3 className="text-base font-semibold text-white">{faq.q}</h3>
              <p className="text-sm text-slate-400">{faq.a}</p>
            </div>
          ))}
        </div>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Keep reading</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <Link href="/learn/alpha-beta-sharpe" className="text-[#00FF9D] hover:underline">
              Alpha, Beta and Sharpe Ratio
            </Link>{' '}
            — the risk-adjusted metrics that P/E says nothing about.
          </li>
          <li>
            <Link href="/learn/mutual-fund-comparison" className="text-[#00FF9D] hover:underline">
              How to compare mutual funds
            </Link>{' '}
            — applying valuation ideas across a whole portfolio.
          </li>
          <li>
            <Link href="/mutual-funds" className="text-[#00FF9D] hover:underline">
              Browse the fund directory
            </Link>{' '}
            — schemes with dated NAV and full-window annualised returns.
          </li>
          <li>
            <Link href="/methodology/formulas" className="text-[#00FF9D] hover:underline">
              FundersAI formulas and methodology
            </Link>{' '}
            — exactly how every published figure is calculated.
          </li>
        </ul>

        <div className="mt-12 p-6 rounded-2xl border border-[#00FF9D]/20 bg-[#00FF9D]/[0.05]">
          <h3 className="text-lg font-medium text-white mb-2">Research valuations with FundersAI</h3>
          <p className="text-sm text-slate-300 mb-4">
            Compare Indian stocks and mutual funds using deterministic metrics computed from official
            sources, with every figure traceable to its origin.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/dashboard" className="inline-flex items-center justify-center rounded-lg bg-[#00FF9D] px-6 py-2.5 text-sm font-semibold text-black hover:bg-[#00FF9D]/90 transition">
              Open the dashboard
            </Link>
            <Link href="/mutual-funds" className="inline-flex items-center justify-center rounded-lg border border-[#00FF9D]/30 px-6 py-2.5 text-sm font-semibold text-[#00FF9D] hover:bg-[#00FF9D]/10 transition">
              Browse funds
            </Link>
          </div>
        </div>

        <p className="text-xs text-slate-500 pt-6 border-t border-white/10">
          Research only. This article is educational and is not personalized investment advice, a
          recommendation, or a valuation opinion on any specific security. Examples are illustrative and
          use hypothetical figures. Past performance does not guarantee future results.
        </p>
      </div>
    </article>
    </>
  );
}
