import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Methodology | FundersAI',
  description:
    'How FundersAI sources data, calculates metrics, handles missing fields, and separates deterministic analysis from AI-generated summaries. Full transparency on data freshness, formulas, and abstention conditions.',
};

// Section anchor helper
function Section({
  id,
  number,
  title,
  children,
}: {
  id: string;
  number: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <div className="flex items-baseline gap-3 mb-4">
        <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#00FF9D]/70 shrink-0">
          {number}
        </span>
        <h2 className="text-xl font-bold text-white">{title}</h2>
      </div>
      <div className="space-y-4 text-sm leading-7 text-[#aebed6]">{children}</div>
    </section>
  );
}

function Formula({ label, formula }: { label: string; formula: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[#00FF9D]/60 mb-1">{label}</p>
      <code className="text-sm font-mono text-[#b8d3ff]">{formula}</code>
    </div>
  );
}

function Tag({ children, color = 'green' }: { children: React.ReactNode; color?: 'green' | 'blue' | 'amber' }) {
  const colors = {
    green: 'bg-[#00FF9D]/10 text-[#00FF9D] border-[#00FF9D]/20',
    blue: 'bg-[#66a3ff]/10 text-[#66a3ff] border-[#66a3ff]/20',
    amber: 'bg-amber-400/10 text-amber-300 border-amber-400/20',
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${colors[color]}`}>
      {children}
    </span>
  );
}

const toc = [
  { id: 'data-sources', label: 'Data sources' },
  { id: 'update-frequency', label: 'Update frequency' },
  { id: 'metric-formulas', label: 'Metric formulas' },
  { id: 'plan-option-handling', label: 'Plan & option handling' },
  { id: 'fund-name-resolution', label: 'Fund name resolution' },
  { id: 'benchmark-mapping', label: 'Benchmark mapping' },
  { id: 'stale-missing-fields', label: 'Stale & missing fields' },
  { id: 'ai-vs-deterministic', label: 'AI vs deterministic' },
  { id: 'abstention', label: 'When FundersAI refuses' },
  { id: 'source-links', label: 'Official source links' },
];

export default function MethodologyPage() {
  return (
    <main className="min-h-dvh bg-[#070b12] text-[#dce8fa]">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#070b12]/90 backdrop-blur-md sticky top-0 z-30">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/" className="text-sm font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
            ← FundersAI
          </Link>
          <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#00FF9D]/60">Methodology</span>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:grid lg:grid-cols-[220px_1fr] lg:gap-16">
        {/* Sidebar TOC — sticky on desktop */}
        <aside className="hidden lg:block">
          <div className="sticky top-28">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#7183a0] mb-4">On this page</p>
            <nav className="space-y-1">
              {toc.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className="block text-sm text-[#7183a0] hover:text-white transition-colors py-1"
                >
                  {item.label}
                </a>
              ))}
            </nav>
          </div>
        </aside>

        {/* Content */}
        <article className="space-y-14">
          {/* Hero */}
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#00FF9D]/70 mb-3">
              How it works
            </p>
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl mb-5">Methodology</h1>
            <p className="text-base leading-7 text-[#aebed6] max-w-2xl">
              FundersAI combines deterministic metrics from official sources with AI-generated plain-English
              summaries. This page documents exactly how data is sourced, how each metric is calculated, and where
              the system refuses to answer.
            </p>
            <p className="mt-3 text-sm text-[#7183a0]">Last updated: July 2026</p>
          </div>

          {/* 1. Data sources */}
          <Section id="data-sources" number="01" title="Data sources">
            <p>
              Every field in FundersAI traces to an official or regulated source. No synthetic data, no scraped
              estimates, no AI-imputed values in the metrics layer.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-3 pr-6 font-semibold text-white">Data type</th>
                    <th className="text-left py-3 pr-6 font-semibold text-white">Primary source</th>
                    <th className="text-left py-3 font-semibold text-white">Fallback</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {[
                    ['NAV history', 'MFapi (AMFI-sourced)', 'NSE direct feed'],
                    ['AUM', 'AMFI monthly disclosure', '—'],
                    ['Expense ratio (TER)', 'Official AMC factsheet', 'AMFI reported TER'],
                    ['Portfolio holdings', 'AMC monthly disclosure (PDF/XLSX)', '—'],
                    ['Risk metrics', 'Calculated from NAV history', '—'],
                    ['Benchmark returns', 'NSE / BSE index feeds', '—'],
                    ['Fund manager details', 'AMC factsheet', 'AMFI SEBI filing'],
                    ['Scheme information', 'AMFI master data', 'AMC website SID'],
                  ].map(([type, primary, fallback]) => (
                    <tr key={type}>
                      <td className="py-3 pr-6 text-white font-medium">{type}</td>
                      <td className="py-3 pr-6 text-[#aebed6]">{primary}</td>
                      <td className="py-3 text-[#7183a0]">{fallback}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              Official AMC documents (factsheets, portfolio disclosures, SID/SAI) are downloaded from AMC websites,
              stored in Cloudflare R2, parsed, and indexed. Document URLs and publication dates are preserved so
              every claim can be traced back to the source PDF.
            </p>
          </Section>

          {/* 2. Update frequency */}
          <Section id="update-frequency" number="02" title="Update frequency">
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                {
                  label: 'NAV',
                  freq: 'Daily',
                  color: 'green' as const,
                  detail: 'Updated each business day after AMFI publishes the day\'s NAV, typically by 11 PM IST.',
                },
                {
                  label: 'Portfolio holdings',
                  freq: 'Monthly',
                  color: 'blue' as const,
                  detail: 'SEBI mandates disclosure within 10 business days of month-end. FundersAI fetches and indexes new filings as they appear.',
                },
                {
                  label: 'Factsheets & SID',
                  freq: 'Event-driven',
                  color: 'amber' as const,
                  detail: 'Acquired when AMCs publish updated documents — after fund manager changes, strategy updates, or NFO events.',
                },
              ].map((item) => (
                <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
                  <Tag color={item.color}>{item.freq}</Tag>
                  <p className="mt-3 font-semibold text-white">{item.label}</p>
                  <p className="mt-2 text-xs leading-6 text-[#7183a0]">{item.detail}</p>
                </div>
              ))}
            </div>
            <p>
              Every field exposes its last-updated timestamp. When data has not refreshed within the expected
              window, FundersAI marks the field as <Tag color="amber">STALE</Tag> and surfaces the gap instead of
              presenting outdated numbers as current.
            </p>
          </Section>

          {/* 3. Metric formulas */}
          <Section id="metric-formulas" number="03" title="How metrics are calculated">
            <p>
              All quantitative metrics are calculated deterministically from raw NAV history. No AI model is
              involved in producing these numbers.
            </p>

            <div className="space-y-3">
              <Formula
                label="CAGR (Compounded Annual Growth Rate)"
                formula="CAGR = (NAV_end / NAV_start) ^ (1 / years) − 1"
              />
              <Formula
                label="Rolling return (n-year window)"
                formula="For each date d: rolling_return[d] = CAGR(NAV[d − n·365], NAV[d])"
              />
              <Formula
                label="Standard deviation (annualised)"
                formula="σ_annual = σ_daily × √252   where σ_daily = std(daily log returns)"
              />
              <Formula
                label="Sharpe ratio"
                formula="Sharpe = (R_portfolio − R_f) / σ_annual   (R_f = 6.5% p.a. proxy)"
              />
              <Formula
                label="Sortino ratio"
                formula="Sortino = (R_portfolio − R_f) / σ_downside   where σ_downside uses only negative daily returns"
              />
              <Formula
                label="Maximum drawdown"
                formula="MaxDD = min over all (t1 < t2) of (NAV[t2] − NAV[t1]) / NAV[t1]"
              />
              <Formula
                label="SIP return (XIRR)"
                formula="Solve: Σ C_i / (1 + r)^(t_i / 365) = 0   where C_i are monthly SIP cash flows"
              />
            </div>

            <p>
              The risk-free rate proxy is fixed at 6.5% per annum for Sharpe and Sortino calculations. When fewer
              than 252 NAV data points are available for the requested window, the metric is marked{' '}
              <Tag color="amber">PARTIAL</Tag> and the available sample size is disclosed.
            </p>
          </Section>

          {/* 4. Plan & option handling */}
          <Section id="plan-option-handling" number="04" title="Plan & option handling">
            <p>
              Each AMFI scheme code maps to exactly one plan–option combination. FundersAI treats these as
              separate instruments and never mixes returns across plan types.
            </p>
            <div className="grid sm:grid-cols-2 gap-4">
              {[
                ['Direct vs Regular', 'Direct plans have no distributor commission baked in. FundersAI defaults to Direct when both exist. Regular plan data is accessible but labelled clearly.'],
                ['Growth vs IDCW', 'Growth option reinvests all returns into NAV. IDCW (dividend) plans distribute periodically. Returns are only compared within the same option type.'],
              ].map(([title, body]) => (
                <div key={title as string} className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
                  <p className="font-semibold text-white mb-2">{title}</p>
                  <p className="text-xs leading-6 text-[#7183a0]">{body}</p>
                </div>
              ))}
            </div>
          </Section>

          {/* 5. Fund name resolution */}
          <Section id="fund-name-resolution" number="05" title="Fund name resolution">
            <p>
              AMFI assigns a numeric scheme code to every registered scheme. FundersAI maps colloquial fund names
              (e.g., &ldquo;PPFAS Flexi Cap&rdquo;) to their AMFI scheme codes through a normalised name registry.
            </p>
            <p>
              When a query matches multiple scheme codes (e.g., Direct Growth vs Regular Growth), the resolver
              surfaces the ambiguity and asks the user to confirm the intended instrument before fetching data.
              Resolver confidence scores are always visible in the response.
            </p>
            <p>
              If the resolver cannot confidently match a fund name, it returns an explicit{' '}
              <Tag color="amber">UNRESOLVED</Tag> status rather than guessing.
            </p>
          </Section>

          {/* 6. Benchmark mapping */}
          <Section id="benchmark-mapping" number="06" title="Benchmark mapping">
            <p>
              SEBI mandates that each fund declare a primary benchmark. FundersAI reads the declared benchmark from
              the factsheet and uses that index for alpha and relative-performance calculations.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-3 pr-6 font-semibold text-white">Category</th>
                    <th className="text-left py-3 font-semibold text-white">Typical benchmark</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {[
                    ['Large Cap', 'Nifty 100 TRI'],
                    ['Mid Cap', 'Nifty Midcap 150 TRI'],
                    ['Small Cap', 'Nifty Smallcap 250 TRI'],
                    ['Flexi Cap', 'BSE 500 TRI'],
                    ['ELSS', 'Nifty 500 TRI'],
                    ['Debt – Short Duration', 'CRISIL Short Duration Debt Index'],
                    ['Index Fund (Nifty 50)', 'Nifty 50 TRI'],
                  ].map(([cat, bench]) => (
                    <tr key={cat}>
                      <td className="py-3 pr-6 text-white">{cat}</td>
                      <td className="py-3 text-[#aebed6]">{bench}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              TRI (Total Return Index) variants are used wherever available since they include dividend
              reinvestment, making comparisons fair against Growth-option NAVs.
            </p>
          </Section>

          {/* 7. Stale & missing fields */}
          <Section id="stale-missing-fields" number="07" title="Stale & missing field handling">
            <p>
              FundersAI distinguishes between fields that are absent and fields that are present but outdated.
              Neither is hidden from the user.
            </p>
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                {
                  tag: 'FRESH',
                  color: 'green' as const,
                  desc: 'Data updated within the expected refresh window for its category.',
                },
                {
                  tag: 'STALE',
                  color: 'amber' as const,
                  desc: 'Data exists but has not refreshed within the expected window. Shown with last-updated timestamp.',
                },
                {
                  tag: 'MISSING',
                  color: 'amber' as const,
                  desc: 'Field is unavailable from any source. The response explicitly flags the gap before drawing conclusions.',
                },
              ].map((item) => (
                <div key={item.tag} className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
                  <Tag color={item.color}>{item.tag}</Tag>
                  <p className="mt-3 text-xs leading-6 text-[#7183a0]">{item.desc}</p>
                </div>
              ))}
            </div>
            <p>
              When a field required for a calculation is missing, the metric is omitted rather than estimated.
              Missing-field warnings appear directly adjacent to the answer, not buried in footnotes.
            </p>
          </Section>

          {/* 8. AI vs deterministic */}
          <Section id="ai-vs-deterministic" number="08" title="What AI generates vs deterministic">
            <p>
              The boundary is explicit and consistent across every response.
            </p>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="rounded-xl border border-[#00FF9D]/20 bg-[#00FF9D]/[0.04] p-5">
                <Tag color="green">Deterministic</Tag>
                <ul className="mt-4 space-y-1.5 text-xs leading-6 text-[#aebed6]">
                  <li>All quantitative metrics (CAGR, Sharpe, drawdown, SIP XIRR)</li>
                  <li>NAV history and return series</li>
                  <li>AUM, expense ratio, benchmark</li>
                  <li>Portfolio holdings and sector weights</li>
                  <li>Freshness and staleness labels</li>
                  <li>Missing-field warnings</li>
                  <li>Source citations and document links</li>
                </ul>
              </div>
              <div className="rounded-xl border border-[#66a3ff]/20 bg-[#66a3ff]/[0.04] p-5">
                <Tag color="blue">AI-generated</Tag>
                <ul className="mt-4 space-y-1.5 text-xs leading-6 text-[#aebed6]">
                  <li>Plain-English summary of what the deterministic metrics show</li>
                  <li>Contextual explanation of why a metric differs from peers</li>
                  <li>Synthesis of evidence from multiple official documents</li>
                </ul>
                <p className="mt-4 text-xs text-[#7183a0]">
                  AI summaries are always grounded in the deterministic data fetched in the same request. The LLM
                  does not have access to training-time fund data — it writes about the numbers FundersAI just
                  calculated.
                </p>
              </div>
            </div>
          </Section>

          {/* 9. Abstention */}
          <Section id="abstention" number="09" title="When FundersAI refuses to answer">
            <p>
              FundersAI is designed to abstain when the conditions for a reliable answer are not met. Abstention
              is not a failure — it is the correct output.
            </p>
            <div className="space-y-3">
              {[
                ['Insufficient evidence', 'A fund research question is abstained on when retrieved document chunks do not meet the minimum quality threshold. The threshold and retrieval score are disclosed.'],
                ['Missing required fields', 'A metric comparison is refused when a field required for a fair comparison is absent on one side and no verified substitute exists.'],
                ['Investment-advice guardrail', 'Any query that requests a buy, sell, or hold recommendation is declined. FundersAI returns the relevant metrics and evidence but explicitly does not convert them into an actionable call.'],
                ['Unresolved fund identity', 'If the name resolution step cannot confidently identify the queried instrument, FundersAI surfaces the ambiguity and asks for clarification rather than guessing.'],
                ['Stale data beyond threshold', 'If the most recent data point for a key field is more than the defined staleness threshold for its category, conclusions drawn from that field are qualified or withheld.'],
              ].map(([title, body]) => (
                <div key={title as string} className="rounded-xl border border-white/8 bg-white/[0.02] px-5 py-4">
                  <p className="font-semibold text-white mb-1.5">{title}</p>
                  <p className="text-xs leading-6 text-[#7183a0]">{body}</p>
                </div>
              ))}
            </div>
          </Section>

          {/* 10. Source links */}
          <Section id="source-links" number="10" title="Official source links">
            <p>
              FundersAI reads from regulated, public sources. Below are the primary portals used.
            </p>
            <div className="grid sm:grid-cols-2 gap-3">
              {[
                { label: 'AMFI India', desc: 'Master scheme data, NAV history, AUM disclosures', url: 'https://www.amfiindia.com' },
                { label: 'MFapi', desc: 'Machine-readable NAV API (AMFI-sourced)', url: 'https://www.mfapi.in' },
                { label: 'NSE India', desc: 'Index feeds, equity prices, benchmark data', url: 'https://www.nseindia.com' },
                { label: 'BSE India', desc: 'BSE index data, listed fund information', url: 'https://www.bseindia.com' },
                { label: 'SEBI', desc: 'Regulatory filings, mutual fund guidelines', url: 'https://www.sebi.gov.in' },
                { label: 'RBI', desc: 'Risk-free rate reference (repo rate)', url: 'https://www.rbi.org.in' },
              ].map((item) => (
                <a
                  key={item.label}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex flex-col rounded-xl border border-white/10 bg-white/[0.02] px-4 py-4 transition hover:border-white/20 hover:bg-white/[0.04]"
                >
                  <span className="font-semibold text-white text-sm">{item.label}</span>
                  <span className="mt-1 text-xs text-[#7183a0]">{item.desc}</span>
                  <span className="mt-2 text-[10px] text-[#82aff6]">{item.url}</span>
                </a>
              ))}
            </div>
          </Section>

          {/* Footer note */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] px-5 py-5 text-sm text-[#7183a0]">
            <p>
              <span className="font-semibold text-white">Research only. </span>
              FundersAI provides data, metrics, and evidence to help you research mutual funds. Nothing on this
              platform constitutes personalised investment advice, a securities recommendation, or a financial
              product offer. Always verify data with official sources and consult a qualified financial adviser
              before making investment decisions.
            </p>
          </div>

          <div className="flex flex-wrap gap-4 border-t border-white/10 pt-6 text-sm">
            <Link href="/" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
              ← Back to home
            </Link>
            <Link href="/dashboard" className="font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors">
              Open workspace
            </Link>
          </div>
        </article>
      </div>
    </main>
  );
}
