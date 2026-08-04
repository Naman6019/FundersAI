import Link from 'next/link';

export const metadata = {
  title: 'Understanding Alpha, Beta, and Sharpe Ratio | FundersAI Learn',
  description: 'A guide to risk metrics for mutual funds and what they mean for your portfolio.',
};

export default function RiskMetricsPage() {
  return (
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
          When evaluating a mutual fund, returns only tell half the story. The other half is the risk taken to achieve those returns. These three metrics—Alpha, Beta, and Sharpe Ratio—are the holy trinity of risk-adjusted performance.
        </p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Alpha: The Value Added</h2>
        <p>
          <strong>Alpha</strong> measures how much a fund has outperformed (or underperformed) its benchmark index, given its risk level. 
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li>A positive Alpha (e.g., +2.0) means the fund manager generated 2% more return than expected for the level of risk taken.</li>
          <li>A negative Alpha means the fund underperformed its benchmark.</li>
        </ul>
        <p className="text-sm italic text-slate-400">If you are paying a high expense ratio for an actively managed fund, you want to see a consistently positive Alpha.</p>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Beta: The Volatility</h2>
        <p>
          <strong>Beta</strong> measures the volatility or systematic risk of a fund compared to the overall market (which always has a Beta of 1.0).
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Beta &gt; 1:</strong> The fund is more volatile than the market. If the market goes up 10%, a fund with a Beta of 1.2 is expected to go up 12% (but also fall 12% if the market drops).</li>
          <li><strong>Beta &lt; 1:</strong> The fund is less volatile than the market. Defensive funds typically have a Beta below 1.</li>
        </ul>

        <h2 className="text-2xl font-medium text-white mt-8 mb-4">Sharpe Ratio: Risk-Adjusted Return</h2>
        <p>
          The <strong>Sharpe Ratio</strong> tells you how much excess return you are receiving for the extra volatility you endure by holding a riskier asset.
        </p>
        <p>
          A higher Sharpe Ratio is always better. When comparing two funds in the same category, the one with the higher Sharpe Ratio has historically provided better returns for the same amount of risk, or the same returns with less risk.
        </p>

        <div className="mt-12 p-6 rounded-2xl border border-[#00FF9D]/20 bg-[#00FF9D]/[0.05]">
          <h3 className="text-lg font-medium text-white mb-2">View Risk Metrics Instantly</h3>
          <p className="text-sm text-slate-300 mb-4">
            FundersAI calculates and displays these risk metrics for mutual funds directly in the analysis canvas.
          </p>
          <Link href="/dashboard" className="inline-flex items-center justify-center rounded-lg bg-[#00FF9D] px-6 py-2.5 text-sm font-semibold text-black hover:bg-[#00FF9D]/90 transition">
            Start Researching
          </Link>
        </div>
      </div>
    </article>
  );
}
