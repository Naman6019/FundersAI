"use client";

/* eslint-disable @next/next/no-img-element */
import { useEffect, useState } from "react";
import {
  ArrowRight,
  BarChart2,
  Bell,
  Brain,
  CheckCircle2,
  ChevronRight,
  Database,
  ExternalLink,
  LayoutPanelLeft,
  Menu,
  RefreshCw,
  Shield,
  SlidersHorizontal,
  Sparkles,
  TrendingUp,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import styles from "./page.module.css";

const logoUrl = "/logo-vertical.png";

const funds = [
  { name: "PPFAS Flexi Cap", oneY: "+22.45%", ter: "0.65%", risk: "MOD" },
  { name: "HDFC Mid Cap Opp.", oneY: "+31.20%", ter: "0.98%", risk: "HIGH" },
  { name: "SBI Small Cap Fund", oneY: "+18.90%", ter: "1.12%", risk: "V.HI" },
  { name: "ICICI Pru Bal. Adv.", oneY: "+14.30%", ter: "0.88%", risk: "MOD" },
  { name: "Mirae Large Cap", oneY: "+16.75%", ter: "0.52%", risk: "M-L" },
];

const insights = [
  "PPFAS Flexi Cap achieves a Sharpe ratio of 1.82 with low TER, creating a compounding advantage over longer horizons.",
  "HDFC Mid Cap shows elevated alpha against its benchmark with higher beta, suitable for long horizon research.",
  "SBI Small Cap carries high volatility but has shown consistent outperformance across the small-cap universe.",
  "ICICI Balanced Advantage dynamically shifts equity and debt allocation for better downside protection.",
  "Mirae Large Cap has a low expense ratio and steady market-like beta, useful for core large-cap comparison.",
];

const features = [
  {
    icon: SlidersHorizontal,
    label: "01 - Screener",
    title: "Advanced Screener",
    desc: "Filter mutual funds and stocks by TER, AUM, alpha, beta, Sharpe ratio, and rolling returns.",
    tags: ["TER Filter", "Alpha/Beta", "Rolling Returns", "AUM Range"],
    cta: "Launch Screener",
    wide: false,
  },
  {
    icon: Bell,
    label: "02 - Alerts",
    title: "Automated Watchlist Alerts",
    desc: "Monitor disclosures, manager changes, and expense ratio updates across your tracked universe.",
    tags: ["Disclosure Alerts", "Manager Change", "TER Updates"],
    cta: "Set Up Alerts",
    wide: false,
  },
  {
    icon: LayoutPanelLeft,
    label: "03 - Comparison",
    title: "Side-by-Side Canvas",
    desc: "Overlay NAV performance and compare asset allocations across timeframes to spot overlap quickly.",
    tags: ["NAV Overlay", "Allocation Diff", "Portfolio Overlap", "Custom Timeframes"],
    cta: "Open Canvas",
    wide: true,
  },
];

const metricDefs = [
  {
    key: "sharpe",
    label: "Sharpe Ratio",
    min: 0.3,
    max: 3,
    step: 0.01,
    value: 1.22,
    format: (v: number) => v.toFixed(2),
    explain: (v: number) => {
      if (v < 0.7) return ["Poor", "#ff6b6b", `A Sharpe ratio of ${v.toFixed(2)} suggests weak returns for the risk taken.`];
      if (v < 1.2) return ["Below Average", "#ffd166", `A Sharpe ratio of ${v.toFixed(2)} is positive, but risk-adjusted efficiency is limited.`];
      if (v < 1.7) return ["Good", "#66a3ff", `A Sharpe ratio of ${v.toFixed(2)} is strong for active fund research and suggests efficient risk use.`];
      return ["Excellent", "#007acc", `A Sharpe ratio of ${v.toFixed(2)} is unusually strong and should be checked over rolling periods.`];
    },
  },
  {
    key: "alpha",
    label: "Alpha (1Y, %)",
    min: -5,
    max: 15,
    step: 0.1,
    value: 4.2,
    format: (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`,
    explain: (v: number) => {
      if (v < 0) return ["Negative Alpha", "#ff6b6b", `Alpha of ${v.toFixed(1)}% means the fund underperformed its benchmark after risk adjustment.`];
      if (v < 2) return ["Marginal", "#ffd166", `Alpha of +${v.toFixed(1)}% is modest after accounting for active management costs.`];
      if (v < 6) return ["Strong", "#66a3ff", `Alpha of +${v.toFixed(1)}% is meaningful and worth validating over 3Y and 5Y windows.`];
      return ["Very High", "#007acc", `Alpha of +${v.toFixed(1)}% is high and may compress as fund size grows.`];
    },
  },
  {
    key: "beta",
    label: "Beta",
    min: 0.3,
    max: 1.8,
    step: 0.01,
    value: 0.92,
    format: (v: number) => v.toFixed(2),
    explain: (v: number) => {
      if (v < 0.7) return ["Defensive", "#66a3ff", `Beta of ${v.toFixed(2)} means the fund moves less than the market.`];
      if (v < 1.05) return ["Market-Like", "#66a3ff", `Beta of ${v.toFixed(2)} indicates movement close to the benchmark.`];
      if (v < 1.3) return ["Moderate Aggression", "#ffd166", `Beta of ${v.toFixed(2)} amplifies market moves and needs higher risk tolerance.`];
      return ["High Aggression", "#ff6b6b", `Beta of ${v.toFixed(2)} strongly amplifies market movement.`];
    },
  },
];

const providers = [
  ["PPFAS", "PPFAS AMC", "2h ago"],
  ["ICICI", "ICICI Prudential", "2h ago"],
  ["HDFC", "HDFC Mutual Fund", "3h ago"],
  ["SBI", "SBI Mutual Fund", "2h ago"],
  ["KOTAK", "Kotak Mahindra AMC", "4h ago"],
  ["NIPPON", "Nippon India AMC", "2h ago"],
  ["AXIS", "Axis Mutual Fund", "3h ago"],
  ["DSP", "DSP Mutual Fund", "5h ago"],
  ["MIRAE", "Mirae Asset AMC", "2h ago"],
  ["QUANT", "Quant AMC", "6h ago"],
  ["UTI", "UTI Mutual Fund", "3h ago"],
  ["AMFI", "AMFI", "2h ago"],
];

const logs = [
  ["14:32:01", "Ingesting PPFAS factsheet - November edition", "ok"],
  ["14:31:58", "HDFC Mid Cap TER updated to 0.98%", "ok"],
  ["14:31:45", "NAV batch complete - 4,832 schemes processed", "ok"],
  ["14:30:12", "SEBI MF data portal sync initiated", "ok"],
  ["14:29:55", "AMFI disclosure parsed for SBI Small Cap", "ok"],
  ["14:28:30", "Kotak manager change detected - watchlist flagged", "alert"],
];

export default function EmergentReplicaPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeRow, setActiveRow] = useState(0);
  const [activeLog, setActiveLog] = useState(0);
  const [metricIndex, setMetricIndex] = useState(0);
  const [metricValues, setMetricValues] = useState(metricDefs.map((metric) => metric.value));

  useEffect(() => {
    const rowTimer = window.setInterval(() => setActiveRow((row) => (row + 1) % funds.length), 2800);
    const logTimer = window.setInterval(() => setActiveLog((log) => (log + 1) % logs.length), 3000);
    return () => {
      window.clearInterval(rowTimer);
      window.clearInterval(logTimer);
    };
  }, []);

  const metric = metricDefs[metricIndex];
  const metricValue = metricValues[metricIndex];
  const [level, levelColor, explanation] = metric.explain(metricValue);

  return (
    <main className={styles.page}>
      <nav className={styles.nav}>
        <div className={styles.navInner}>
          <a className={styles.logo} href="#top" aria-label="FundersAI home">
            <span className={styles.logoMark}>
              <img src={logoUrl} alt="" />
            </span>
            <span>FundersAI</span>
          </a>

          <div className={styles.navLinks}>
            {["Features", "Mutual Funds", "Stocks", "Data Sources"].map((link) => (
              <a key={link} href={`#${link.toLowerCase().replaceAll(" ", "-")}`}>
                {link}
                {link === "Stocks" ? <span className={styles.badge}>Preview</span> : null}
              </a>
            ))}
          </div>

          <div className={styles.navActions}>
            <button className={styles.ghostButton}>Sign In</button>
            <button className={styles.primaryButton}>
              Start Researching <ArrowRight size={15} />
            </button>
          </div>

          <button className={styles.menuButton} onClick={() => setMenuOpen((open) => !open)} aria-label="Toggle menu">
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {menuOpen ? (
          <div className={styles.mobileMenu}>
            {["Features", "Mutual Funds", "Stocks", "Data Sources"].map((link) => (
              <a key={link} href={`#${link.toLowerCase().replaceAll(" ", "-")}`} onClick={() => setMenuOpen(false)}>
                {link}
              </a>
            ))}
          </div>
        ) : null}
      </nav>

      <section id="top" className={`${styles.section} ${styles.hero}`}>
        <div className={styles.shell}>
          <div className={styles.heroGrid}>
            <motion.div initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55 }}>
              <p className={styles.overline}>Institutional Research Platform</p>
              <h1>
                Institutional-Grade
                <br />
                Market Research. <span>Explained by AI.</span>
              </h1>
              <p className={styles.heroCopy}>
                Filter, compare, and track mutual funds with deterministic metrics, then let intent-aware AI synthesize the insights.
              </p>
              <div className={styles.ctaRow}>
                <a className={styles.primaryButtonLarge} href="#mutual-funds">
                  Explore Mutual Funds <ArrowRight size={16} />
                </a>
                <a className={styles.secondaryButton} href="#features">
                  View Example Comparison
                </a>
              </div>
              <div className={styles.statRow}>
                <span>
                  <TrendingUp size={14} /> 15,000+ Funds Tracked
                </span>
                <span>
                  <Shield size={14} /> Zero Advisory Bias
                </span>
                <span>
                  <Sparkles size={14} /> AI-Powered Explanations
                </span>
              </div>
            </motion.div>

            <motion.div className={styles.terminalCard} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.7, delay: 0.2 }}>
              <div className={styles.terminalHeader}>
                <i className={styles.redDot} />
                <i className={styles.yellowDot} />
                <i className={styles.greenDot} />
                <span>FundersAI Research Terminal</span>
                <strong>
                  <i className={styles.statusDot} /> LIVE
                </strong>
              </div>
              <div className={styles.fundTableHead}>
                <span>Fund</span>
                <span>1Y Ret</span>
                <span>TER</span>
                <span>Risk</span>
              </div>
              {funds.map((fund, index) => (
                <div key={fund.name} className={`${styles.fundRow} ${index === activeRow ? styles.activeFund : ""}`}>
                  <span>{fund.name}</span>
                  <strong>{fund.oneY}</strong>
                  <span>{fund.ter}</span>
                  <span>{fund.risk}</span>
                </div>
              ))}
              <div className={styles.insightBox}>
                <p>
                  <Sparkles size={12} /> FundersAI Insight
                </p>
                <AnimatePresence mode="wait">
                  <motion.span key={activeRow} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}>
                    {insights[activeRow]}
                  </motion.span>
                </AnimatePresence>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      <section id="features" className={styles.sectionAlt}>
        <div className={styles.shell}>
          <SectionHeading overline="Core Research Tools" title="Every tool built for deterministic research" body="No black-box recommendations. Every metric is traceable, every filter is explainable." />
          <div className={styles.featuresGrid}>
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <motion.article key={feature.title} className={`${styles.featureCard} ${feature.wide ? styles.featureWide : ""}`} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
                  <div className={styles.featureText}>
                    <p className={styles.featureLabel}>
                      <span>
                        <Icon size={22} />
                      </span>
                      {feature.label}
                    </p>
                    <h3>{feature.title}</h3>
                    <p>{feature.desc}</p>
                    <div className={styles.tagRow}>
                      {feature.tags.map((tag) => (
                        <span className={styles.badge} key={tag}>
                          {tag}
                        </span>
                      ))}
                    </div>
                    <button className={styles.linkButton}>
                      {feature.cta} <ChevronRight size={14} />
                    </button>
                  </div>
                  {feature.wide ? <ComparisonMini /> : null}
                </motion.article>
              );
            })}
          </div>
        </div>
      </section>

      <section id="mutual-funds" className={styles.section}>
        <div className={styles.shell}>
          <SectionHeading center overline="Explainable AI" title="AI that explains data, not hallucinates it" body="Every explanation is grounded in deterministic metrics. Adjust any metric and watch the AI explain what it means." />
          <div className={styles.aiGrid}>
            <div className={styles.panel}>
              <div className={styles.metricTabs}>
                {metricDefs.map((item, index) => (
                  <button key={item.key} className={index === metricIndex ? styles.selectedTab : ""} onClick={() => setMetricIndex(index)}>
                    {item.label.split(" ")[0]}
                  </button>
                ))}
              </div>
              <div className={styles.metricValue}>
                <span>{metric.label}</span>
                <strong style={{ color: levelColor, textShadow: `0 0 20px ${levelColor}66` }}>{metric.format(metricValue)}</strong>
                <em style={{ color: levelColor, borderColor: `${levelColor}66`, background: `${levelColor}18` }}>{level}</em>
              </div>
              <input
                className={styles.range}
                type="range"
                min={metric.min}
                max={metric.max}
                step={metric.step}
                value={metricValue}
                onChange={(event) => {
                  const next = [...metricValues];
                  next[metricIndex] = Number(event.target.value);
                  setMetricValues(next);
                }}
              />
              <div className={styles.rangeLabels}>
                <span>{metric.format(metric.min)}</span>
                <span>{metric.format(metric.max)}</span>
              </div>
            </div>

            <div className={styles.panel}>
              <div className={styles.aiHeader}>
                <span>
                  <Brain size={18} />
                </span>
                <div>
                  <strong>FundersAI Explanation Engine</strong>
                  <p>Deterministic - No Hallucination - Source-Grounded</p>
                </div>
                <em>
                  <Sparkles size={11} /> AI
                </em>
              </div>
              <AnimatePresence mode="wait">
                <motion.div key={`${metric.key}-${metricValue}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                  <p className={styles.metricLine}>
                    <BarChart2 size={14} /> Metric: {metric.label} - Value: {metric.format(metricValue)}
                  </p>
                  <p className={styles.explanation}>{explanation}</p>
                  <div className={styles.contextBox}>
                    <strong>Research Context</strong>
                    <p>This interpretation is for research only. It does not provide investment advice or portfolio allocation recommendations.</p>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>
      </section>

      <section id="data-sources" className={styles.sectionAlt}>
        <div className={styles.shell}>
          <div className={styles.dataHeading}>
            <SectionHeading overline="Data Ingestion" title="Direct from source. No intermediary bias." />
            <div className={styles.freshness}>
              <i className={styles.statusDot} /> Data Freshness: Updated 2 hours ago <RefreshCw size={12} />
            </div>
          </div>
          <div className={styles.dataGrid}>
            <div>
              <p className={styles.dataCopy}>
                FundersAI directly ingests AMC factsheets, SEBI filings, and AMFI disclosures from major Indian fund houses.
              </p>
              <div className={styles.providerGrid}>
                {providers.map(([code, name, sync]) => (
                  <div className={styles.providerCard} key={code}>
                    <p>
                      <strong>{code}</strong>
                      <CheckCircle2 size={11} />
                    </p>
                    <span>{name}</span>
                    <em>sync: {sync}</em>
                  </div>
                ))}
              </div>
            </div>
            <div className={styles.logPanel}>
              <div className={styles.logHead}>
                <Database size={13} /> data_pipeline.log <i className={styles.statusDot} /> RUNNING
              </div>
              {logs.map(([time, message, status], index) => (
                <p key={`${time}-${message}`} className={index === activeLog ? styles.activeLog : ""}>
                  <span>{time}</span>
                  <strong>{status === "alert" ? "! " : "ok "}</strong>
                  {message}
                </p>
              ))}
              <div className={styles.promptLine}>$ _ <span>Awaiting next batch...</span></div>
            </div>
          </div>
        </div>
      </section>

      <footer id="stocks" className={styles.footer}>
        <div className={styles.shell}>
          <div className={styles.footerGrid}>
            <div>
              <a className={styles.logo} href="#top">
                <span className={styles.logoMark}>
                  <img src={logoUrl} alt="" />
                </span>
                <span>FundersAI</span>
              </a>
              <p>Institutional-grade research tools for Indian mutual funds and stocks. Research first, always.</p>
            </div>
            {["Product", "Legal", "Regulatory"].map((group) => (
              <div key={group}>
                <h4>{group}</h4>
                {["Mutual Fund Screener", "Stock Research", "Features Overview", "Data Sources"].map((item) => (
                  <a key={item} href="#top">
                    {item} {group !== "Product" ? <ExternalLink size={10} /> : null}
                  </a>
                ))}
              </div>
            ))}
          </div>
          <div className={styles.footerBottom}>
            <span>2024 FundersAI. Research platform preview.</span>
            <span>v2.0.0 - India</span>
          </div>
        </div>
      </footer>
    </main>
  );
}

function SectionHeading({ overline, title, body, center = false }: { overline: string; title: string; body?: string; center?: boolean }) {
  return (
    <div className={`${styles.sectionHeading} ${center ? styles.center : ""}`}>
      <p className={styles.overline}>{overline}</p>
      <h2>{title}</h2>
      {body ? <p>{body}</p> : null}
    </div>
  );
}

function ComparisonMini() {
  return (
    <div className={styles.comparisonMini}>
      <p>NAV Performance Overlay</p>
      <div>
        {[
          ["PPFAS Flexi", "+22.45%"],
          ["HDFC Mid Cap", "+31.20%"],
          ["SBI Small", "+18.90%"],
          ["Mirae Large", "+16.75%"],
        ].map(([name, value]) => (
          <span key={name}>
            <small>{name}</small>
            <strong>{value}</strong>
            <em>1Y Return</em>
          </span>
        ))}
      </div>
      <p>Portfolio overlap: 12.3% - No significant overlap detected</p>
    </div>
  );
}
