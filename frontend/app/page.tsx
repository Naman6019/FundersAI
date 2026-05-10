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
  { icon: "bar_chart_4_bars", label: "BSE & NSE Data", warning: false },
  { icon: "trending_up", label: "Direct Mutual Funds", warning: false },
  { icon: "shield", label: "Research Only", warning: true },
  { icon: "chat_bubble", label: "AI-Assisted Analysis", warning: false },
];

const features = [
  {
    icon: "chat_bubble",
    title: "AI Research Assistant",
    body: "Ask market questions in plain English and get answers tied back to structured stock and fund data.",
  },
  {
    icon: "compare_arrows",
    title: "Side-by-Side Equities",
    body: "Compare stocks across price, returns, ratios, risk metrics, and available fundamentals.",
  },
  {
    icon: "trending_up",
    title: "Mutual Fund Metrics",
    body: "Review AUM, expense ratio, benchmark context, rolling returns, Alpha, Beta, and Sharpe ratio.",
  },
  {
    icon: "monitoring",
    title: "Standardized Financials",
    body: "Keep research focused on aligned metrics instead of scattered screenshots and PDF notes.",
  },
  {
    icon: "menu_book",
    title: "Concept Explanations",
    body: "Ask what a financial metric means and how it matters for the asset you are researching.",
  },
  {
    icon: "layers",
    title: "Research Workspaces",
    body: "Move from a chat answer into comparison views when the query needs structured tables or charts.",
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
            <a href="#features">Features</a>
            <a href="#workflow">Workflow</a>
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
            <h1>Research Indian equities and mutual funds with clarity</h1>
            <p>
              Compare stocks, analyze mutual fund metrics, and ask context-aware questions in one
              research workspace.
            </p>
            <div className="landing-actions">
              <Link href="/dashboard" className="landing-primary-action">
                Start researching
              </Link>
              <a href="#features" className="landing-secondary-action">
                View features
              </a>
            </div>
          </div>

          <div className="landing-chat-stage" aria-label="Try MarketMind">
            <LandingPromptBox />

            <section className="landing-market-strip" aria-label="Nifty 50 stock changes">
              <div className="landing-market-strip-label">
                <span className="material-symbols-outlined">candlestick_chart</span>
                Nifty 50
              </div>
              <div className="landing-market-strip-window">
                {tickerItems.length === 0 ? (
                  <div className="landing-market-strip-message">
                    Current Nifty 50 changes unavailable.
                  </div>
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

        <section className="landing-trust-strip" aria-label="MarketMind trust markers">
          {trustItems.map((item) => (
            <span className="landing-trust-pill" key={item.label}>
              <span className={`material-symbols-outlined ${item.warning ? "warning" : ""}`}>
                {item.icon}
              </span>
              {item.label}
            </span>
          ))}
        </section>

        <section id="workflow" className="landing-problem">
          <h2>The problem with retail market tools</h2>
          <p>
            Most platforms optimize for trading. MarketMind keeps the workspace focused on research,
            structured comparisons, and plain-English explanations.
          </p>
        </section>

        <section id="features" className="landing-features">
          <div className="landing-section-heading">
            <h2>Core capabilities</h2>
            <p>Structured data presentation combined with contextual AI.</p>
          </div>

          <div className="landing-feature-grid">
            {features.map((feature) => (
              <article className="landing-feature-card" key={feature.title}>
                <span className="material-symbols-outlined">{feature.icon}</span>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-workflow">
          {[
            ["1", "Search & Select", "Input stock tickers or mutual fund names."],
            ["2", "Compare Metrics", "Review aligned fundamentals, charts, and risk ratios."],
            ["3", "Ask Questions", "Use chat to explain variances and clarify financial terms."],
          ].map(([step, title, body]) => (
            <article className="landing-workflow-step" key={step}>
              <span>{step}</span>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </section>

        <section id="disclaimer" className="landing-disclaimer">
          <span className="material-symbols-outlined">shield</span>
          <p>
            <strong>Regulatory Disclaimer:</strong> MarketMind is an educational and research
            platform. It is not a SEBI-registered investment advisor, and its output is not
            investment advice.
          </p>
        </section>

        <section className="landing-final-cta">
          <h2>Make market research less intimidating.</h2>
          <p>Create a workspace to analyze Indian equities and mutual funds logically.</p>
          <Link href="/dashboard" className="landing-primary-action">
            Open MarketMind
          </Link>
        </section>
      </main>

      <footer className="landing-footer">
        <div>
          <strong>MarketMind</strong>
          <p>AI-assisted research for Indian stocks and mutual funds.</p>
        </div>
        <p>© 2026 MarketMind Research. Built for structured data, not trading.</p>
      </footer>
    </div>
  );
}
