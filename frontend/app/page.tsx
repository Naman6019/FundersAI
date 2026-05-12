import Link from "next/link";
import LandingPromptBox from "@/components/landing/LandingPromptBox";
import LandingThemeToggle from "@/components/landing/LandingThemeToggle";

export const revalidate = 60;

type TickerItem = {
  symbol: string;
  name: string;
  price: number | null;
  change_pct: number | null;
  date: string | null;
};

const trustItems = [
  { icon: "verified", label: "NSE/BSE linked datasets" },
  { icon: "schedule", label: "Timestamped refresh signals" },
  { icon: "analytics", label: "Metric-level stock + fund coverage" },
  { icon: "robot_2", label: "AI explanations grounded in numbers" },
];

const signalCards = [
  {
    icon: "dataset",
    title: "Authentic Source Layer",
    body: "Price, fundamentals, and fund metrics come from tracked market-source pipelines with visible freshness context.",
  },
  {
    icon: "model_training",
    title: "AI Research Copilot",
    body: "Ask plain-English questions and get structured answers connected to actual symbol and scheme data.",
  },
  {
    icon: "compare_arrows",
    title: "Analysis Workspace",
    body: "Move from chat to side-by-side comparisons for returns, risk, valuation, and trend interpretation.",
  },
];

const processSteps = [
  {
    number: "01",
    title: "Select",
    body: "Pick stocks or funds and open a unified research canvas.",
  },
  {
    number: "02",
    title: "Validate",
    body: "Check freshness, source badges, and metric alignment before conclusions.",
  },
  {
    number: "03",
    title: "Interpret",
    body: "Use AI to explain outliers, risk shifts, and fundamental changes with context.",
  },
  {
    number: "04",
    title: "Decide",
    body: "Export a cleaner research narrative, not trading noise.",
  },
];

const formatChange = (value: number | null) => {
  if (value === null || value === undefined) return "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
};

const tickerUrl = () => {
  const base =
    process.env.NODE_ENV === "development"
      ? "http://127.0.0.1:8000"
      : process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL;

  return base ? `${base}/api/quant/stocks/nifty50/ticker` : null;
};

const getTickerItems = async (): Promise<TickerItem[]> => {
  const url = tickerUrl();
  if (!url) return [];

  try {
    const response = await fetch(url, {
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(6000),
    });
    if (!response.ok) return [];
    const data = await response.json();
    return Array.isArray(data.items) ? data.items : [];
  } catch {
    return [];
  }
};

export default async function LandingPage() {
  const tickerItems = await getTickerItems();
  const tickerGroup = tickerItems.length > 0 ? tickerItems : [];

  return (
    <div className="landing-page">
      <header className="landing-nav">
        <div className="landing-nav-inner">
          <Link href="/" className="landing-brand" aria-label="MarketMind home">
            <span>M</span>
            MarketMind
          </Link>
          <nav className="landing-links" aria-label="Primary">
            <a href="#signals">Signals</a>
            <a href="#process">Research Loop</a>
            <a href="#disclaimer">Disclaimer</a>
          </nav>
          <div className="landing-nav-actions">
            <LandingThemeToggle />
            <Link href="/dashboard" className="landing-small-cta">
              Open Platform
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="landing-hero">
          <div className="landing-hero-copy">
            <p className="landing-kicker">AI + market-verified intelligence</p>
            <h1>Research with proof, not hype.</h1>
            <p>
              MarketMind blends AI reasoning with authentic Indian market datasets so your analysis
              stays explainable, traceable, and usable.
            </p>
            <div className="landing-actions">
              <Link href="/dashboard" className="landing-primary-action">
                Start Research
              </Link>
              <a href="#signals" className="landing-secondary-action">
                Explore Signals
              </a>
            </div>
          </div>

          <div className="landing-proof-grid" aria-label="MarketMind research proof points">
            {trustItems.map((item) => (
              <article className="landing-proof-card" key={item.label}>
                <span className="material-symbols-outlined">{item.icon}</span>
                <p>{item.label}</p>
              </article>
            ))}
          </div>

          <div className="landing-chat-stage" aria-label="Try MarketMind">
            <LandingPromptBox />

            <section className="landing-market-strip" aria-label="Nifty 50 stock changes">
              <div className="landing-market-strip-label">
                <span className="material-symbols-outlined">candlestick_chart</span>
                Nifty 50 snapshot
              </div>
              <div className="landing-market-strip-window">
                {tickerItems.length === 0 ? (
                  <div className="landing-market-strip-message">Current Nifty 50 changes unavailable.</div>
                ) : (
                  <div className="landing-market-strip-track">
                    {[0, 1].map((groupIndex) => (
                      <div
                        className="landing-market-strip-group"
                        key={groupIndex}
                        aria-hidden={groupIndex === 1}
                      >
                        {tickerGroup.map((item) => {
                          const isPositive = (item.change_pct ?? 0) >= 0;
                          return (
                            <span
                              className="landing-market-tick"
                              key={`${item.symbol}-${groupIndex}`}
                              title={item.name}
                            >
                              <span>{item.symbol}</span>
                              <strong className={isPositive ? "positive" : "negative"}>
                                {formatChange(item.change_pct)}
                              </strong>
                            </span>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </div>
        </section>

        <section id="signals" className="landing-signals">
          <div className="landing-section-heading">
            <p className="landing-kicker">Research Signals</p>
            <h2>Built for evidence-led analysis</h2>
          </div>
          <div className="landing-feature-grid">
            {signalCards.map((feature) => (
              <article className="landing-feature-card" key={feature.title}>
                <span className="material-symbols-outlined">{feature.icon}</span>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="process" className="landing-workflow">
          {processSteps.map((step) => (
            <article className="landing-workflow-step" key={step.number}>
              <span>{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </article>
          ))}
        </section>

        <section id="disclaimer" className="landing-disclaimer">
          <span className="material-symbols-outlined">gpp_good</span>
          <p>
            <strong>Regulatory Disclaimer:</strong> MarketMind is an educational research platform.
            It is not a SEBI-registered investment advisor, and output is not investment advice.
          </p>
        </section>

        <section className="landing-final-cta">
          <h2>Turn raw market data into clear research decisions.</h2>
          <p>Open your AI-assisted workspace and analyze with better structure.</p>
          <Link href="/dashboard" className="landing-primary-action">
            Open MarketMind
          </Link>
        </section>
      </main>

      <footer className="landing-footer">
        <div>
          <strong>MarketMind</strong>
          <p>AI-assisted analysis for Indian equities and mutual funds.</p>
        </div>
        <p>© 2026 MarketMind Research. Data-informed by design.</p>
      </footer>
    </div>
  );
}
