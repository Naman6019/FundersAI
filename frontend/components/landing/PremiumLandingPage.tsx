'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  Bot,
  CandlestickChart,
  CheckCircle2,
  Clock3,
  Database,
  FolderKanban,
  GitCompareArrows,
  LineChart,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

type TickerItem = {
  symbol: string;
  name: string;
  price: number | null;
  change_pct: number | null;
  date: string | null;
};

type Props = {
  tickerItems: TickerItem[];
};

const featureCards = [
  {
    title: 'Stock Analysis',
    body: 'Analyze HDFC Bank fundamentals, valuation, and performance.',
    icon: CandlestickChart,
  },
  {
    title: 'Stock Comparison',
    body: 'Compare TCS vs Infosys across key financial metrics.',
    icon: GitCompareArrows,
  },
  {
    title: 'Mutual Fund Comparison',
    body: 'Compare returns, NAV movement, alpha, beta, Sharpe, AUM, and expense ratio.',
    icon: LineChart,
  },
  {
    title: 'AI Research Assistant',
    body: 'Ask natural-language questions and get structured explanations.',
    icon: Bot,
  },
  {
    title: 'Data Freshness',
    body: 'See when stock, NAV, and fundamental data was last updated.',
    icon: Clock3,
  },
  {
    title: 'Research Workspace',
    body: 'Save, compare, and review research without jumping across tools.',
    icon: FolderKanban,
  },
];

const workflowSteps = [
  {
    title: 'Search',
    body: 'Choose a stock, mutual fund, or comparison.',
  },
  {
    title: 'Validate',
    body: 'MarketMind checks structured datasets and available metrics.',
  },
  {
    title: 'Interpret',
    body: 'AI explains the numbers in beginner-friendly language.',
  },
  {
    title: 'Review',
    body: 'Compare, summarize, and continue your research.',
  },
];

const promptExamples = [
  'Compare HDFC Bank vs ICICI Bank',
  'Analyze TCS fundamentals',
  'Compare Parag Parikh Flexi Cap vs Quant Flexi Cap',
  'Find funds with lower expense ratios',
  'Explain Sharpe ratio in this comparison',
  'Show top differences between two stocks',
];

const marketTag = (change: number | null) => {
  if (change === null || Number.isNaN(change)) return 'neutral';
  return change >= 0 ? 'up' : 'down';
};

const formatPct = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

const formatPrice = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function PremiumLandingPage({ tickerItems }: Props) {
  const liveItems = tickerItems.filter((item) => typeof item.change_pct === 'number');
  const sortedByMove = [...liveItems].sort((a, b) => (b.change_pct ?? -999) - (a.change_pct ?? -999));
  const topGainers = sortedByMove.slice(0, 4);
  const topLosers = [...sortedByMove].reverse().slice(0, 4);
  const latestTimestamp = tickerItems.find((item) => item.date)?.date ?? null;
  const snapshotFallback = tickerItems.length === 0;
  const shellClass = 'mx-auto w-full max-w-screen-2xl px-4 sm:px-6 lg:px-10';

  return (
    <div className="relative min-h-screen overflow-x-clip bg-[#050a14] text-[#eaf0ff]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_8%,rgba(70,123,224,0.24),transparent_35%),radial-gradient(circle_at_84%_4%,rgba(50,196,152,0.16),transparent_30%),linear-gradient(to_bottom,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(to_right,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[length:auto,auto,42px_42px,42px_42px]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(5,10,20,0.12),rgba(5,10,20,0.86))]" />

      <header className="sticky top-0 z-50 px-4 py-3 sm:px-6">
        <div className={`${shellClass} flex h-16 items-center justify-between rounded-2xl border border-white/10 bg-[#081122]/75 px-4 shadow-[0_14px_40px_rgba(0,0,0,0.36)] backdrop-blur-xl sm:px-6`}>
          <Link href="/" className="flex items-center gap-2.5 text-sm font-semibold text-white" aria-label="MarketMind home">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-[linear-gradient(145deg,#72a9ff,#3f70d2)] font-bold text-white shadow-[0_10px_20px_rgba(49,109,216,0.5)]">M</span>
            <span className="text-lg leading-none">MarketMind</span>
          </Link>
          <nav className="hidden items-center gap-8 text-sm text-[#9eb3da] md:flex" aria-label="Primary">
            <a href="#features" className="transition hover:text-white">Features</a>
            <a href="#how-it-works" className="transition hover:text-white">How it works</a>
            <a href="#data" className="transition hover:text-white">Data</a>
            <a href="#disclaimer" className="transition hover:text-white">Disclaimer</a>
          </nav>
          <Link href="/dashboard" className="rounded-lg border border-[#3c5c90] bg-[#152845] px-4 py-2 text-sm font-semibold text-[#deebff] transition hover:bg-[#1c3153]">
            Open Dashboard
          </Link>
        </div>
      </header>

      <main className={`${shellClass} relative z-10 pb-16 pt-6 sm:pb-24`}>
        <section className="grid items-center gap-12 pb-16 pt-8 xl:grid-cols-[1.04fr_0.96fr] xl:pb-22 xl:pt-14">
          <motion.div initial="hidden" animate="show" variants={fadeUp} transition={{ duration: 0.5 }}>
            <span className="inline-flex items-center gap-2 rounded-full border border-[#38588a] bg-[#12213c]/85 px-3 py-1 text-xs font-semibold text-[#d8e6ff]">
              <Sparkles size={14} />
              Research with proof, not hype.
            </span>
            <h1 className="mt-6 max-w-[16ch] text-[clamp(2.1rem,5vw,4.5rem)] font-bold leading-[1.03] tracking-[-0.02em] text-white">
              AI-powered research for Indian stocks and mutual funds.
            </h1>
            <p className="mt-5 max-w-[56ch] text-[1.06rem] leading-8 text-[#b5c9eb]">
              Analyze stocks, compare mutual funds, check data-backed metrics, and get explainable AI summaries in one workspace.
            </p>
            <p className="mt-2.5 text-sm text-[#90a7d0]">
              MarketMind turns scattered Indian market data into explainable research.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/dashboard" className="inline-flex items-center gap-2 rounded-lg bg-[#4a83eb] px-5 py-3 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(74,131,235,0.38)] transition hover:-translate-y-0.5 hover:bg-[#3b70d2]">
                Start Free Research
                <ArrowRight size={16} />
              </Link>
              <Link
                href="/dashboard?query=Compare%20Parag%20Parikh%20Flexi%20Cap%20vs%20Quant%20Flexi%20Cap&asset_type=mutual_fund"
                className="inline-flex items-center gap-2 rounded-lg border border-[#3a5886] bg-[#101f37]/70 px-5 py-3 text-sm font-semibold text-[#dfebff] transition hover:-translate-y-0.5 hover:bg-[#182c4a]"
              >
                Try Sample Analysis
              </Link>
            </div>

            <div className="mt-8 grid max-w-2xl gap-2.5 text-xs sm:grid-cols-2">
              {[
                'Indian equities + mutual funds',
                'Data-backed AI summaries',
                'Freshness timestamps',
                'Research-only platform',
              ].map((badge) => (
                <div key={badge} className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5 text-[#c8d9fa]">
                  {badge}
                </div>
              ))}
            </div>
          </motion.div>

          <motion.aside
            initial="hidden"
            animate="show"
            variants={fadeUp}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="rounded-3xl border border-white/15 bg-[linear-gradient(150deg,rgba(24,40,70,0.9),rgba(12,21,36,0.95))] p-4 shadow-[0_26px_70px_rgba(0,0,0,0.48)] xl:justify-self-end xl:w-full xl:max-w-4xl"
            aria-label="MarketMind product preview"
          >
            <div className="mb-4 flex items-center gap-2 border-b border-white/10 pb-3 text-xs text-[#adc3eb]">
              <span className="h-2.5 w-2.5 rounded-full bg-[#f87171]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#fbbf24]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#34d399]" />
              <span className="ml-2">MarketMind Research Workspace</span>
            </div>
            <div className="grid gap-3 lg:grid-cols-[1fr_1.08fr_0.82fr]">
              <div className="rounded-2xl border border-white/10 bg-[#0c172c]/90 p-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-[#8aa8dc]">AI Research Chat</p>
                <div className="mt-2 space-y-2 text-xs text-[#dde8ff]">
                  <div className="rounded-lg bg-[#18325d]/85 p-2.5">Compare ICICI Multi Asset Fund and Parag Flexi Cap.</div>
                  <div className="rounded-lg border border-[#32518a] bg-[#12233f] p-2.5">Cost advantage with ICICI. Return and risk edges are mixed.</div>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-[#0c172c]/90 p-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-[#8aa8dc]">Comparison Table</p>
                <div className="mt-2 overflow-hidden rounded-lg border border-white/10 text-xs">
                  <div className="grid grid-cols-3 bg-[#152846] px-2 py-1.5 font-semibold text-[#dce9ff]">
                    <span>Metric</span>
                    <span>ICICI</span>
                    <span>Parag</span>
                  </div>
                  <div className="grid grid-cols-3 border-t border-white/10 px-2 py-1.5 text-[#bbcdf0]">
                    <span>Returns (3Y)</span>
                    <span>16.1%</span>
                    <span>16.0%</span>
                  </div>
                  <div className="grid grid-cols-3 border-t border-white/10 px-2 py-1.5 text-[#bbcdf0]">
                    <span>Expense Ratio</span>
                    <span>0.82%</span>
                    <span>1.42%</span>
                  </div>
                  <div className="grid grid-cols-3 border-t border-white/10 px-2 py-1.5 text-[#bbcdf0]">
                    <span>Volatility</span>
                    <span>12.7</span>
                    <span>11.9</span>
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-[11px]">
                  <div className="rounded-lg border border-[#33558c] bg-[#142445] px-2 py-1.5 text-[#d1e0fb]">Sharpe 1.18</div>
                  <div className="rounded-lg border border-[#2a6a60] bg-[#12322d] px-2 py-1.5 text-[#b4f3e8]">Fresh 2026-05-16</div>
                </div>
              </div>

              <div className="space-y-3 rounded-2xl border border-white/10 bg-[#0c172c]/90 p-3">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.2em] text-[#8aa8dc]">Data Freshness</p>
                  <p className="mt-1 text-xs text-[#d5e4ff]">Stocks: 16 May, 8:08 PM</p>
                  <p className="text-xs text-[#d5e4ff]">NAV: 16 May, 7:44 PM</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-[0.2em] text-[#8aa8dc]">Mini NAV Trend</p>
                  <svg viewBox="0 0 220 80" className="mt-1 h-16 w-full">
                    <polyline
                      fill="none"
                      stroke="#6ca7ff"
                      strokeWidth="2.6"
                      points="0,62 26,58 52,54 78,46 104,42 130,38 156,34 182,26 208,18"
                    />
                  </svg>
                </div>
                <p className="rounded-lg border border-amber-200/25 bg-amber-100/10 px-2 py-1.5 text-[11px] text-amber-100">
                  Research-only, not investment advice.
                </p>
              </div>
            </div>
          </motion.aside>
        </section>

        <section id="preview" className="pb-16 md:pb-22">
          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.2 }}
            variants={fadeUp}
            transition={{ duration: 0.45 }}
            className="rounded-3xl border border-white/10 bg-[linear-gradient(145deg,rgba(16,28,48,0.82),rgba(11,20,34,0.9))] p-6 sm:p-8"
          >
            <p className="text-xs uppercase tracking-[0.2em] text-[#90afdf]">Product Preview</p>
            <h2 className="mt-2 text-[clamp(1.75rem,3vw,2.4rem)] font-semibold text-white">A serious research terminal, simplified.</h2>
            <p className="mt-3 max-w-3xl text-[1rem] leading-8 text-[#aec3e8]">
              One workspace for AI research chat, financial comparisons, structured metrics, freshness visibility, and context-rich summaries for Indian stocks and mutual funds.
            </p>
          </motion.div>
        </section>

        <section id="features" className="pb-16 md:pb-22">
          <div className="mb-7">
            <p className="text-xs uppercase tracking-[0.2em] text-[#90afdf]">What You Can Do</p>
            <h2 className="mt-2 text-[clamp(1.85rem,3vw,2.6rem)] font-semibold text-white">Built for practical research workflows</h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {featureCards.map((item, idx) => {
              const Icon = item.icon;
              return (
                <motion.article
                  key={item.title}
                  initial="hidden"
                  whileInView="show"
                  viewport={{ once: true, amount: 0.2 }}
                  variants={fadeUp}
                  transition={{ duration: 0.38, delay: idx * 0.05 }}
                  className="group rounded-2xl border border-white/10 bg-[linear-gradient(155deg,rgba(17,28,48,0.84),rgba(9,15,29,0.85))] p-5 transition hover:-translate-y-1 hover:border-[#4a75ba] hover:shadow-[0_18px_40px_rgba(13,25,46,0.45)]"
                >
                  <div className="inline-flex rounded-lg border border-[#3b5e95] bg-[#152544] p-2.5 text-[#b7ccf3]">
                    <Icon size={17} />
                  </div>
                  <h3 className="mt-3 text-xl font-semibold text-white">{item.title}</h3>
                  <p className="mt-2 text-[0.96rem] leading-7 text-[#aac0e4]">{item.body}</p>
                </motion.article>
              );
            })}
          </div>
        </section>

        <section id="data" className="pb-16 md:pb-22">
          <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[#90afdf]">Live Market/Data Snapshot</p>
              <h2 className="mt-2 text-[clamp(1.85rem,3vw,2.6rem)] font-semibold text-white">Nifty 50 Snapshot</h2>
            </div>
            <div className="rounded-lg border border-[#345381] bg-[#12213b]/70 px-3 py-2 text-xs text-[#d2e0fb]">
              Last updated: {latestTimestamp ?? 'Not available'}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr_1fr]">
            <div className="rounded-2xl border border-white/10 bg-[linear-gradient(155deg,rgba(17,29,50,0.84),rgba(9,15,29,0.82))] p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-[#8ca9da]">Market Pulse</p>
              {snapshotFallback ? (
                <p className="mt-4 text-sm text-[#b5c8ea]">
                  Market snapshot is temporarily unavailable.
                  {/* TODO: connect this fallback card to a dedicated market snapshot API payload when available. */}
                </p>
              ) : (
                <div className="mt-3 space-y-2.5">
                  {tickerItems.slice(0, 6).map((item) => (
                    <div key={item.symbol} className="flex items-center justify-between rounded-lg border border-white/10 bg-[#0f1a30]/65 px-3 py-2 text-sm">
                      <div>
                        <p className="font-semibold text-white">{item.symbol}</p>
                        <p className="text-xs text-[#8ea5cd]">{item.name}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-[#dbe8ff]">{formatPrice(item.price)}</p>
                        <p className={marketTag(item.change_pct) === 'up' ? 'text-[#34d399]' : marketTag(item.change_pct) === 'down' ? 'text-[#fb7185]' : 'text-[#9fb4d8]'}>
                          {formatPct(item.change_pct)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-white/10 bg-[linear-gradient(155deg,rgba(17,29,50,0.84),rgba(9,15,29,0.82))] p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-[#8ca9da]">Top Gainers</p>
              <div className="mt-3 space-y-2">
                {topGainers.length === 0 ? (
                  <p className="text-sm text-[#b5c8ea]">No gainers available.</p>
                ) : (
                  topGainers.map((item) => (
                    <div key={item.symbol} className="flex items-center justify-between rounded-lg border border-emerald-300/20 bg-emerald-300/10 px-3 py-2 text-sm">
                      <span className="font-medium text-[#dcfff2]">{item.symbol}</span>
                      <span className="font-semibold text-[#34d399]">{formatPct(item.change_pct)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[linear-gradient(155deg,rgba(17,29,50,0.84),rgba(9,15,29,0.82))] p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-[#8ca9da]">Top Losers</p>
              <div className="mt-3 space-y-2">
                {topLosers.length === 0 ? (
                  <p className="text-sm text-[#b5c8ea]">No losers available.</p>
                ) : (
                  topLosers.map((item) => (
                    <div key={item.symbol} className="flex items-center justify-between rounded-lg border border-rose-300/20 bg-rose-300/10 px-3 py-2 text-sm">
                      <span className="font-medium text-[#ffe0e6]">{item.symbol}</span>
                      <span className="font-semibold text-[#fb7185]">{formatPct(item.change_pct)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="pb-16 md:pb-22">
          <div className="mb-7">
            <p className="text-xs uppercase tracking-[0.2em] text-[#90afdf]">How MarketMind Works</p>
            <h2 className="mt-2 text-[clamp(1.85rem,3vw,2.6rem)] font-semibold text-white">From query to explainable research in four steps</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {workflowSteps.map((step, index) => (
              <motion.article
                key={step.title}
                initial="hidden"
                whileInView="show"
                viewport={{ once: true, amount: 0.2 }}
                variants={fadeUp}
                transition={{ duration: 0.38, delay: index * 0.05 }}
                className="rounded-2xl border border-white/10 bg-[linear-gradient(155deg,rgba(17,28,48,0.84),rgba(9,15,29,0.85))] p-5"
              >
                <p className="text-xs font-semibold tracking-[0.18em] text-[#8ca9da]">Step {index + 1}</p>
                <h3 className="mt-2 text-xl font-semibold text-white">{step.title}</h3>
                <p className="mt-2 text-[0.95rem] leading-7 text-[#adbfdf]">{step.body}</p>
              </motion.article>
            ))}
          </div>
        </section>

        <section className="pb-16 md:pb-22">
          <div className="rounded-3xl border border-white/10 bg-[linear-gradient(155deg,rgba(15,28,52,0.9),rgba(9,16,30,0.9))] p-6 sm:p-8">
            <h2 className="text-[clamp(1.85rem,3vw,2.6rem)] font-semibold text-white">Built for research, not hype.</h2>
            <div className="mt-5 grid gap-3.5 sm:grid-cols-2">
              {[
                'Structured financial metrics',
                'Timestamped data freshness',
                'AI explanations grounded in numbers',
                'Mutual fund and stock comparison support',
                'Beginner-friendly summaries',
                'No buy/sell recommendations',
                'Research-only disclaimer',
              ].map((point) => (
                <div key={point} className="flex items-start gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-3 text-sm text-[#d5e4ff]">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-[#67d3a7]" />
                  <span>{point}</span>
                </div>
              ))}
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-[#345381] bg-[#0f1d35]/80 p-4">
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-[#8ea8d7]">
                  <Database size={14} />
                  Data Coverage
                </div>
                <p className="mt-2 text-sm text-[#d5e4ff]">Indian equities, indices, and mutual fund datasets.</p>
              </div>
              <div className="rounded-xl border border-[#345381] bg-[#0f1d35]/80 p-4">
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-[#8ea8d7]">
                  <Clock3 size={14} />
                  Freshness Signals
                </div>
                <p className="mt-2 text-sm text-[#d5e4ff]">Visible update timestamps to support quality checks.</p>
              </div>
              <div className="rounded-xl border border-[#345381] bg-[#0f1d35]/80 p-4">
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-[#8ea8d7]">
                  <ShieldCheck size={14} />
                  Research Guardrails
                </div>
                <p className="mt-2 text-sm text-[#d5e4ff]">No advisory calls, only explainable research context.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="pb-16 md:pb-22">
          <div className="mb-7">
            <p className="text-xs uppercase tracking-[0.2em] text-[#90afdf]">AI Research Examples</p>
            <h2 className="mt-2 text-[clamp(1.85rem,3vw,2.6rem)] font-semibold text-white">Sample prompts for faster analysis</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {promptExamples.map((prompt) => (
              <Link
                key={prompt}
                href={`/dashboard?query=${encodeURIComponent(prompt)}`}
                className="rounded-xl border border-white/10 bg-[linear-gradient(155deg,rgba(17,29,50,0.84),rgba(9,15,29,0.84))] px-4 py-3 text-sm text-[#d6e5fe] transition hover:-translate-y-0.5 hover:border-[#4f77b9] hover:bg-[#132344]"
              >
                “{prompt}”
              </Link>
            ))}
          </div>
        </section>

        <section id="disclaimer" className="pb-16">
          <div className="rounded-2xl border border-amber-300/30 bg-amber-100/10 px-5 py-4 text-sm leading-7 text-[#f8e8b8]">
            MarketMind is for research and education only. It does not provide financial advice, investment recommendations, or buy/sell calls. Always verify data independently before making financial decisions.
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-[linear-gradient(150deg,rgba(26,48,88,0.9),rgba(10,17,32,0.95))] px-5 py-10 text-center sm:px-8 sm:py-12">
          <h2 className="text-[clamp(1.85rem,3vw,2.5rem)] font-semibold text-white">
            Start researching Indian stocks and mutual funds with explainable AI.
          </h2>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <Link href="/dashboard" className="inline-flex items-center gap-2 rounded-lg bg-[#4a83eb] px-5 py-3 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(74,131,235,0.38)] transition hover:-translate-y-0.5 hover:bg-[#3b70d2]">
              Open Dashboard
            </Link>
            <Link
              href="/dashboard?query=Compare%20ICICI%20Multi%20Asset%20Fund%20and%20Parag%20Flexi%20Cap&asset_type=mutual_fund"
              className="inline-flex items-center gap-2 rounded-lg border border-[#4568a4] bg-[#132444] px-5 py-3 text-sm font-semibold text-[#dce9ff] transition hover:-translate-y-0.5 hover:bg-[#1b2f56]"
            >
              Try Sample Analysis
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
