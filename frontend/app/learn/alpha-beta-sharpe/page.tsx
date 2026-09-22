import type { Metadata } from 'next';
import Link from 'next/link';
import { ArticleJsonLd } from '@/components/seo/JsonLd';

export const metadata: Metadata = {
  title: 'Alpha, Beta and Sharpe Ratio Explained for Mutual Funds | FundersAI',
  description:
    'How Alpha, Beta and the Sharpe Ratio measure risk-adjusted mutual fund performance, how each is calculated, what the numbers mean in practice, and why they mislead when read alone or over short windows.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/learn/alpha-beta-sharpe',
  },
  openGraph: {
    title: 'Understanding Alpha, Beta, and Sharpe Ratio | FundersAI Learn',
    description:
      'The risk metrics that returns alone cannot tell you — how alpha, beta, Sharpe and standard deviation are calculated and where they break down.',
    url: 'https://www.fundersai.co.in/learn/alpha-beta-sharpe',
  },
};

const FAQS = [
  {
    q: 'What is a good Sharpe ratio for a mutual fund?',
    a: 'Higher is better, but the number is only meaningful against peers in the same category and over the same period. As a rough convention, above 1 is usually considered good in Indian equity funds, above 2 is strong, and negative means the fund underperformed the risk-free rate. A Sharpe of 1.5 in a small-cap fund is not comparable to 1.5 in a large-cap fund, because their risk profiles differ fundamentally.',
  },
  {
    q: 'What does a beta of less than 1 mean?',
    a: 'It means the fund has historically moved less than its benchmark. A beta of 0.7 suggests that when the index moved 10%, the fund tended to move about 7% in the same direction. Defensive and hybrid funds typically sit below 1. Lower beta means less market risk, but it does not automatically mean better returns.',
  },
  {
    q: 'Can a fund have positive alpha and still be a poor choice?',
    a: 'Yes. Positive alpha computed over a short window is heavily influenced by luck and by the specific benchmark chosen. A fund can also show positive alpha while carrying much higher volatility, meaning the extra return came from taking substantially more risk rather than from manager skill. Alpha should always be read alongside beta, standard deviation and the fund\'s expense ratio.',
  },
  {
    q: 'What is the difference between Sharpe and Sortino ratio?',
    a: 'The Sharpe ratio divides excess return by total volatility, so it penalises both upside and downside swings equally. The Sortino ratio divides excess return by downside deviation only, so it penalises only losses. If two funds have identical returns but one has wild upward swings, Sharpe will penalise it and Sortino will not. Sortino is often considered more intuitive for investors because upside volatility is not a problem to be avoided.',
  },
  {
    q: 'Why does my fund show different alpha and beta on different sites?',
    a: 'Almost always because of three choices: the period measured, the benchmark used, and the frequency of return observations (daily, weekly or monthly). Alpha and beta are regression outputs, so changing any one of these changes the result. FundersAI publishes its method version alongside every figure so a value can be reproduced and compared honestly.',
  },
];

const METRIC_ROWS: Array<[string, string, string]> = [
  ['Alpha', 'Excess return over the benchmark after adjusting for risk taken', 'Measures whether the manager added value beyond the index'],
  ['Beta', 'Sensitivity of the fund\'s returns to benchmark movements', 'Measures how much market risk the fund carries'],
  ['Standard deviation', 'How widely returns vary around their average', 'Measures total volatility, upside and downside together'],
  ['Sharpe ratio', 'Excess return per unit of total volatility', 'The all-in risk-adjusted return measure'],
  ['Sortino ratio', 'Excess return per unit of downside volatility only', 'Risk-adjusted return that ignores upside swings'],
];

export default function RiskMetricsPage() {
  return (
    <>
      <ArticleJsonLd
        title="Alpha, Beta and Sharpe Ratio Explained for Mutual Funds"
        description="How Alpha, Beta and the Sharpe Ratio measure risk-adjusted mutual fund performance, how each is calculated, what the numbers mean, and why they mislead when read alone."
        slug="alpha-beta-sharpe"
        faqs={FAQS}
      />
      <article className="prose prose-invert prose-slate max-w-none">
      <div className="mb-8">
        <Link href="/learn" className="text-[#00FF9D] hover:underline text-sm font-medium">
          &larr; Back to Learning Hub
        </Link>
      </div>

      <h1 className="text-3xl md:text-4xl font-serif font-semibold tracking-tight text-white mb-6">
        Understanding Alpha, Beta, and Sharpe Ratio
      </h1>

      <div className="text-slate-300 space-y-6 leading-relaxed">
        <p>
          Returns tell only half the story of a mutual fund. The other half is the risk taken to earn
          them. Two funds can deliver 15% CAGR, but if one did it with half the volatility, they are very
          different products — and you should not be indifferent between them.
        </p>
        <p>
          <strong>Alpha</strong>, <strong>Beta</strong> and the <strong>Sharpe ratio</strong> are the
          standard vocabulary for that difference. Each isolates a different part of the question, and
          each one misleads if you read it alone.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">The metrics at a glance</h2>
        <div className="overflow-x-auto rounded-lg border border-white/10">
          <table className="w-full text-sm">
            <caption className="text-left p-3 text-xs text-slate-400">
              A summary of the standard risk-adjusted performance metrics. Each answers a different question.
            </caption>
            <thead className="bg-white/[0.04]">
              <tr>
                <th scope="col" className="text-left p-3 font-semibold text-white">Metric</th>
                <th scope="col" className="text-left p-3 font-semibold text-white">What it measures</th>
                <th scope="col" className="text-left p-3 font-semibold text-white">Question it answers</th>
              </tr>
            </thead>
            <tbody>
              {METRIC_ROWS.map(([metric, measures, answers]) => (
                <tr key={metric} className="border-t border-white/10">
                  <th scope="row" className="text-left p-3 font-medium text-white">{metric}</th>
                  <td className="p-3 text-slate-400">{measures}</td>
                  <td className="p-3 text-slate-400">{answers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Beta: how much the fund moves with the market</h2>
        <p>
          <strong>Beta</strong> measures how sensitive the fund is to movements in its benchmark. The
          benchmark itself always has a beta of 1.0 by definition, since it is the reference point.
        </p>
        <div className="bg-white/[0.04] p-4 rounded-lg border border-white/10 font-mono text-center text-[#b3ffdb]">
          Beta = Covariance(Fund, Benchmark) ÷ Variance(Benchmark)
        </div>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Beta &gt; 1:</strong> the fund is more volatile than the market. If the benchmark rises
            10%, a fund with a beta of 1.2 has historically tended to rise about 12% — and to fall about
            12% when the benchmark falls 10%.
          </li>
          <li>
            <strong>Beta = 1:</strong> the fund has historically moved broadly in line with its benchmark.
          </li>
          <li>
            <strong>Beta &lt; 1:</strong> the fund is less volatile than the market. Defensive and hybrid
            funds typically sit below 1.
          </li>
        </ul>
        <p>
          One important limit: beta only captures <em>systematic</em> risk — the part of the movement that
          follows the market. A fund can have a low beta and still be risky, if it carries heavy
          concentrated bets in a single sector or a few stocks. Beta does not see that.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Alpha: return added beyond the risk taken</h2>
        <p>
          <strong>Alpha</strong> measures the return a fund generated above what its beta would predict.
          In effect, it separates the return you got from simply being exposed to the market from the
          return the manager added on top.
        </p>
        <div className="bg-white/[0.04] p-4 rounded-lg border border-white/10 font-mono text-center text-[#b3ffdb]">
          Alpha = Fund Return − [ Risk-Free Rate + Beta × (Benchmark Return − Risk-Free Rate) ]
        </div>
        <p>
          <strong>Worked example.</strong> Suppose the risk-free rate is 6%, the benchmark returned 12%,
          and the fund has a beta of 1.1. The return the fund would be expected to deliver, given its
          market exposure, is 6% + 1.1 × (12% − 6%) = 12.6%. If the fund actually returned 15%, its alpha
          is 15% − 12.6% = <strong>+2.4%</strong>. The manager added 2.4 percentage points beyond what the
          risk exposure alone would explain.
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Positive alpha:</strong> the manager generated more return than the risk level
            implied.
          </li>
          <li>
            <strong>Negative alpha:</strong> the fund underperformed what its market exposure would
            predict. This is the case that matters most for an actively managed fund, because you are
            paying an expense ratio for it.
          </li>
        </ul>
        <p className="text-sm italic text-slate-400">
          If you are paying a higher expense ratio for active management, persistently positive alpha is
          the justification. Persistently negative alpha means you are paying more for less.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Standard deviation: the raw volatility</h2>
        <p>
          Standard deviation measures how widely the fund&apos;s returns have varied around their own
          average. A fund that returns 13% every single year has a standard deviation near zero. A fund
          that returned +45% one year and −20% the next can have the same average but a far higher
          standard deviation.
        </p>
        <p>
          It is the input the Sharpe ratio is built on, and it is quoted as an annualised percentage. It
          captures both upside and downside swings — which is simultaneously its strength and the reason
          the Sortino ratio exists.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Sharpe Ratio: return per unit of risk</h2>
        <p>
          The <strong>Sharpe ratio</strong> is the most widely used single measure of risk-adjusted
          performance. It divides the return earned above the risk-free rate by the volatility endured to
          earn it:
        </p>
        <div className="bg-white/[0.04] p-4 rounded-lg border border-white/10 font-mono text-center text-[#b3ffdb]">
          Sharpe Ratio = (Fund Return − Risk-Free Rate) ÷ Standard Deviation
        </div>
        <p>
          <strong>Worked example.</strong> Fund A returns 18% with a standard deviation of 12%. Fund B
          returns 14% with a standard deviation of 6%. With a 6% risk-free rate:
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li>Fund A: (18 − 6) ÷ 12 = <strong>1.0</strong></li>
          <li>Fund B: (14 − 6) ÷ 6 = <strong>1.33</strong></li>
        </ul>
        <p>
          Fund A earned more in absolute terms, but Fund B produced more return for every unit of risk
          taken. If you can borrow at the risk-free rate, a higher Sharpe is the more efficient
          allocation — which is exactly what the ratio is designed to reveal.
        </p>
        <p>
          As a rough convention, below 1 indicates the fund earned little over the risk-free rate for its
          volatility, above 1 is generally considered good, above 2 is strong, and a negative value means
          the fund underperformed the risk-free rate outright.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Sortino: the same idea, downside only</h2>
        <p>
          The Sharpe ratio penalises upside and downside volatility equally, which many investors find
          counter-intuitive: a fund that repeatedly surprised to the upside is treated as &ldquo;riskier&rdquo;.
        </p>
        <p>
          The <strong>Sortino ratio</strong> corrects this by dividing excess return by{' '}
          <em>downside deviation</em> only — the volatility of returns below a target, usually the
          risk-free rate. Everything above the target is ignored. For a fund with strong positive skew,
          Sortino will read higher than Sharpe; for one with heavy losses, it reads lower.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Where these metrics mislead</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>The benchmark choice changes everything.</strong> Alpha and beta are both regression
            outputs against a benchmark. Measure a flexi-cap fund against the Nifty 50 instead of the
            BSE 500 TRI and you will get a different alpha for the same performance. A &ldquo;positive
            alpha&rdquo; claim is meaningless without knowing the index behind it.
          </li>
          <li>
            <strong>Short windows are noise.</strong> Over one year, alpha and beta are dominated by
            which sectors happened to rally. Three and five-year windows are far more informative, and
            even those can reflect a single favourable regime.
          </li>
          <li>
            <strong>Beta hides concentration risk.</strong> A fund with a low beta that holds 40% in
            three stocks is not low-risk; it carries risk the market model does not capture.
          </li>
          <li>
            <strong>Sharpe assumes normal returns.</strong> Indian equity returns are not normally
            distributed — crashes are sharper and rarer than the bell curve predicts, which makes Sharpe
            understate tail risk.
          </li>
          <li>
            <strong>Risk-free rate matters.</strong> The Sharpe ratio is sensitive to the rate used. If
            one source uses a 91-day treasury bill and another uses a fixed 6%, their Sharpes will differ
            for the identical fund. FundersAI stores the rate used per calculation so the figure stays
            reproducible.
          </li>
          <li>
            <strong>None of this predicts the future.</strong> Every one of these metrics is
            backward-looking by construction. They describe the road already travelled.
          </li>
        </ul>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Reading them together</h2>
        <p>
          The metrics only become useful as a set. A fund with high beta, high return and a low Sharpe
          simply took more risk and was paid for it. A fund with low beta, moderate return and a high
          Sharpe delivered efficiency. A fund with positive alpha but very high standard deviation added
          value through concentrated bets rather than steady skill.
        </p>
        <p>
          Used together, they answer the question that matters: was the return worth the risk, and would
          you have been able to hold the fund through the drawdown it required?
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
            <Link href="/learn/pe-ratio" className="text-[#00FF9D] hover:underline">
              P/E Ratio Explained
            </Link>{' '}
            — the valuation metric that says nothing about risk.
          </li>
          <li>
            <Link href="/learn/large-cap-vs-flexi-cap" className="text-[#00FF9D] hover:underline">
              Large Cap vs Flexi Cap
            </Link>{' '}
            — how mandate changes the risk profile you are measuring.
          </li>
          <li>
            <Link href="/methodology/formulas" className="text-[#00FF9D] hover:underline">
              FundersAI formulas and methodology
            </Link>{' '}
            — the exact formulas, risk-free rate and method version behind every published figure.
          </li>
          <li>
            <Link href="/tools/portfolio-overlap" className="text-[#00FF9D] hover:underline">
              Portfolio overlap tool
            </Link>{' '}
            — the concentration risk that beta cannot see.
          </li>
        </ul>

        <div className="mt-12 p-6 rounded-2xl border border-[#00FF9D]/20 bg-[#00FF9D]/[0.05]">
          <h3 className="text-lg font-medium text-white mb-2">View risk metrics with FundersAI</h3>
          <p className="text-sm text-slate-300 mb-4">
            FundersAI computes returns, volatility, drawdown, Sharpe, alpha and beta with a published
            method version, so every figure can be traced and reproduced.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/dashboard" className="inline-flex items-center justify-center rounded-lg bg-[#00FF9D] px-6 py-2.5 text-sm font-semibold text-black hover:bg-[#00FF9D]/90 transition">
              Start researching
            </Link>
            <Link href="/mutual-funds" className="inline-flex items-center justify-center rounded-lg border border-[#00FF9D]/30 px-6 py-2.5 text-sm font-semibold text-[#00FF9D] hover:bg-[#00FF9D]/10 transition">
              Browse funds
            </Link>
          </div>
        </div>

        <p className="text-xs text-slate-500 pt-6 border-t border-white/10">
          Research only. This article is educational and is not personalized investment advice or a
          recommendation. Worked examples use hypothetical figures for illustration. Past performance does
          not guarantee future results.
        </p>
      </div>
    </article>
    </>
  );
}
