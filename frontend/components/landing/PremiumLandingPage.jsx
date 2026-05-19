"use client";

import React, { useEffect, useState } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import {
  ArrowRight,
  ChartBar,
  Cpu,
  CheckCircle,
  CaretRight,
  Clock,
  Database,
  TrendUp,
  Lock,
  MagnifyingGlass,
  ShieldCheck,
  Sparkle,
  Star,
  Cards
} from "@phosphor-icons/react";

const ease = [0.22, 1, 0.36, 1];

const fadeUp = {
  hidden: { opacity: 0, y: 28, filter: "blur(10px)" },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.75, ease },
  },
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08, delayChildren: 0.06 } },
};

const comparisonMetrics = [
  ["3Y Return", "+18.6%", "Performance"],
  ["Expense Ratio", "0.63%", "Cost"],
  ["Sharpe", "1.12", "Risk-adjusted"],
  ["Coverage", "PPFAS + ICICI", "Current pipeline"],
];

const features = [
  {
    icon: Cards,
    title: "Fund-to-fund comparison",
    eyebrow: "Compare",
    body: "Compare supported Indian mutual funds across returns, NAV movement, AUM, expense ratio, risk metrics, and consistency. Coverage is expanding across major AMCs.",
    proof: "Live: Parag Parikh + ICICI",
  },
  {
    icon: Cpu,
    title: "Explainable AI summaries",
    eyebrow: "Understand",
    body: "Turn dense fund metrics into clear research notes without hiding the underlying numbers.",
    proof: "Designed for research, not advice",
  },
  {
    icon: Database,
    title: "Coverage expansion",
    eyebrow: "Expanding",
    body: "We ingest factsheets and portfolio holdings directly. Parag Parikh and ICICI Prudent pipelines are fully live, with more AMCs synced daily.",
    proof: "Direct daily data sync",
  },
  {
    icon: TrendUp,
    title: "NAV and risk canvas",
    eyebrow: "Visualize",
    body: "Review NAV movement, return trends, volatility signals, and risk-adjusted metrics in a cleaner comparison workspace.",
    proof: "Built for side-by-side review",
  },
  {
    icon: ShieldCheck,
    title: "Research-only guardrails",
    eyebrow: "Guardrails",
    body: "Positioned for education and comparison, not buy/sell calls, recommendations, or advisory output.",
    proof: "No investment recommendations",
  },
  {
    icon: ChartBar,
    title: "Stock coverage on the way",
    eyebrow: "Next module",
    body: "Indian stock research and comparison will follow after the mutual fund comparison and coverage layer is stronger.",
    proof: "Planned after fund MVP matures",
  },
];

const promptChips = [
  "Compare Parag Parikh Flexi Cap vs ICICI Multi Asset Fund",
  "Which fund has better risk-adjusted returns?",
  "Explain alpha, beta, and Sharpe in simple terms",
  "Compare expense ratio and AUM",
  "Show NAV trend differences",
  "Which fund has been more consistent?",
];

const steps = [
  ["01", "Pick funds", "Select two or more funds from the comparison workspace."],
  ["02", "Compare metrics", "Review returns, NAV, AUM, TER, alpha, beta, Sharpe, volatility, and drawdowns."],
  ["03", "Ask MooliqAI", "Get a research-only explanation of what the numbers suggest."],
  ["04", "Review clearly", "Save the comparison and continue deeper research without treating it as advice."],
  ["Focus", "Coverage expansion", "The primary focus now is adding more AMCs and improving supported mutual fund coverage before stock research becomes a main module."],
];

function Glow({ className = "", delay = 0 }) {
  return (
    <motion.div
      aria-hidden="true"
      className={`pointer-events-none absolute rounded-full blur-3xl ${className}`}
      animate={{
        scale: [1, 1.14, 1],
        opacity: [0.28, 0.54, 0.28],
        x: [0, 18, 0],
        y: [0, -16, 0],
      }}
      transition={{ duration: 9, repeat: Infinity, ease: "easeInOut", delay }}
    />
  );
}

function FineGrid() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 -z-10 bg-[linear-gradient(to_right,rgba(255,255,255,0.055)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.055)_1px,transparent_1px)] bg-[size:80px_80px] [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_72%)]"
    />
  );
}

function PremiumButton({ href, children, variant = "primary" }) {
  const base = "group inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-semibold transition duration-300";
  const styles =
    variant === "primary"
      ? "bg-white text-slate-950 shadow-[0_20px_70px_rgba(255,255,255,0.16)] hover:-translate-y-0.5 hover:bg-emerald-100"
      : "border border-white/12 bg-white/[0.05] text-white backdrop-blur-xl hover:-translate-y-0.5 hover:bg-white/[0.09]";

  return (
    <a href={href} className={`${base} ${styles}`}>
      {children}
      {variant === "primary" && <ArrowRight className="ml-2 h-4 w-4 transition group-hover:translate-x-1" />}
    </a>
  );
}

function Badge({ children }) {
  return (
    <motion.span
      variants={fadeUp}
      className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.055] px-3 py-1.5 text-xs font-medium text-slate-300 shadow-sm backdrop-blur-xl"
    >
      <CheckCircle className="h-3.5 w-3.5 text-emerald-300" weight="fill" />
      {children}
    </motion.span>
  );
}

function HeroPreview() {
  const [data, setData] = useState({ ppfas: null, icici: null });

  useEffect(() => {
    async function loadData() {
      try {
        const [res1, res2] = await Promise.all([
          fetch('/api/mf/122639').then(r => r.json()).catch(() => null),
          fetch('/api/mf/100356').then(r => r.json()).catch(() => null)
        ]);
        setData({ ppfas: res1, icici: res2 });
      } catch (e) {
        console.error("Failed to fetch NAV data", e);
      }
    }
    loadData();
  }, []);

  const ppfasReturn = data.ppfas?.returns?.['1Y'] ? `+${(data.ppfas.returns['1Y'] * 100).toFixed(1)}%` : "+22.4%";
  const iciciReturn = data.icici?.returns?.['1Y'] ? `+${(data.icici.returns['1Y'] * 100).toFixed(1)}%` : "+19.8%";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease }}
      className="relative mx-auto mt-12 w-full max-w-4xl rounded-2xl border border-white/10 bg-[#0F172A] p-6 shadow-2xl"
    >
      <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-6">
        <div className="flex items-center gap-3">
          <Sparkle className="h-4 w-4 text-emerald-400" weight="fill" />
          <span className="text-sm font-semibold text-slate-200">MooliqAI Chat</span>
        </div>
        <span className="rounded-full bg-white/5 px-3 py-1 text-[10px] font-medium uppercase tracking-wider text-slate-400">
          Fund Comparison
        </span>
      </div>

      <div className="flex flex-col gap-8">
        {/* User Message */}
        <div className="flex gap-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-slate-300">
            U
          </div>
          <div className="flex-1 space-y-2 pt-1">
            <p className="text-sm leading-relaxed text-slate-200">
              Compare Parag Parikh Flexi Cap vs ICICI Pru Multi Asset. Which one has better risk-adjusted returns over the last year?
            </p>
          </div>
        </div>

        {/* AI Response */}
        <div className="flex gap-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
            <Sparkle className="h-4 w-4" weight="fill" />
          </div>
          <div className="flex-1 space-y-5 pt-1">
            <p className="text-sm leading-relaxed text-slate-300">
              Here is a comparison of their core metrics. Parag Parikh appears steadier on risk-adjusted metrics, while ICICI Multi Asset brings a multi-asset allocation profile.
            </p>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs font-semibold text-slate-400">Parag Parikh Flexi Cap</div>
                <div className="mt-2 text-2xl font-mono text-emerald-400">{ppfasReturn}</div>
                <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">1Y Return (Live Data)</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs font-semibold text-slate-400">ICICI Pru Multi Asset</div>
                <div className="mt-2 text-2xl font-mono text-emerald-400">{iciciReturn}</div>
                <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">1Y Return (Live Data)</div>
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-black/20 p-5 font-mono text-xs text-slate-400">
              <div className="flex justify-between border-b border-white/10 pb-3 font-semibold text-slate-300">
                <span>Metric</span>
                <span className="w-20 text-right">PPFAS</span>
                <span className="w-20 text-right">ICICI</span>
              </div>
              <div className="flex justify-between border-b border-white/5 py-3">
                <span>Sharpe Ratio</span>
                <span className="w-20 text-emerald-400 text-right">1.22</span>
                <span className="w-20 text-slate-300 text-right">1.08</span>
              </div>
              <div className="flex justify-between py-3">
                <span>Expense Ratio</span>
                <span className="w-20 text-slate-300 text-right">0.63%</span>
                <span className="w-20 text-slate-300 text-right">1.05%</span>
              </div>
            </div>

          </div>
        </div>
      </div>
    </motion.div>
  );
}

function LogoCloud() {
  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
      className="mx-auto mt-12 grid max-w-5xl grid-cols-2 gap-3 sm:grid-cols-4"
    >
      {[
        "NAV trends",
        "Expense ratio",
        "Alpha / Beta",
        "Sharpe ratio",
      ].map((item) => (
        <motion.div
          key={item}
          variants={fadeUp}
          className="rounded-2xl border border-white/10 bg-white/[0.035] px-4 py-3 text-center text-sm text-slate-300 backdrop-blur"
        >
          {item}
        </motion.div>
      ))}
    </motion.div>
  );
}

function MarqueePrompts() {
  return (
    <div className="relative mx-auto mt-10 max-w-6xl overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_12%,black_88%,transparent)]">
      <motion.div
        className="flex w-max gap-3"
        animate={{ x: [0, -780] }}
        transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
      >
        {[...promptChips, ...promptChips, ...promptChips].map((prompt, index) => (
          <button
            key={`${prompt}-${index}`}
            className="rounded-full border border-white/10 bg-white/[0.045] px-5 py-3 text-sm text-slate-200 transition hover:border-emerald-300/30 hover:bg-emerald-300/10 hover:text-white"
          >
            {prompt}
          </button>
        ))}
      </motion.div>
    </div>
  );
}

function SectionHeading({ eyebrow, title, body, align = "center" }) {
  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-90px" }}
      className={align === "center" ? "mx-auto max-w-3xl text-center" : "max-w-3xl"}
    >
      <motion.p variants={fadeUp} className="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-300">
        {eyebrow}
      </motion.p>
      <motion.h2 variants={fadeUp} className="mt-4 text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">
        {title}
      </motion.h2>
      {body && <motion.p variants={fadeUp} className="mt-5 text-lg leading-8 text-slate-400">{body}</motion.p>}
    </motion.div>
  );
}

function FeatureCarousel() {
  const [active, setActive] = useState(0);
  const [direction, setDirection] = useState(1);
  const activeFeature = features[active];
  const Icon = activeFeature.icon;

  const selectFeature = (index) => {
    setDirection(index >= active ? 1 : -1);
    setActive(index);
  };

  useEffect(() => {
    const timer = window.setInterval(() => {
      setDirection(1);
      setActive((current) => (current + 1) % features.length);
    }, 3200);

    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="relative">
      <div className="mb-5 flex flex-col gap-4 rounded-[1.5rem] border border-white/10 bg-white/[0.035] p-3 backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {features.map((feature, index) => (
            <button
              key={feature.title}
              onClick={() => selectFeature(index)}
              className={`rounded-full border px-4 py-2 text-xs font-medium transition duration-300 ${
                active === index
                  ? "border-emerald-300/40 bg-emerald-300/[0.12] text-emerald-100 shadow-[0_0_24px_rgba(16,185,129,0.12)]"
                  : "border-white/10 bg-white/[0.035] text-slate-400 hover:bg-white/[0.07] hover:text-white"
              }`}
            >
              {feature.eyebrow}
            </button>
          ))}
        </div>

        <div className="flex shrink-0 items-center gap-2 self-start sm:self-auto">
          {features.map((feature, index) => (
            <button
              key={feature.title}
              aria-label={`View ${feature.title}`}
              onClick={() => selectFeature(index)}
              className={`h-2.5 rounded-full transition-[width,background-color] duration-300 ${
                active === index ? "w-8 bg-white" : "w-2.5 bg-white/25 hover:bg-white/50"
              }`}
            />
          ))}
        </div>
      </div>

      <div className="relative min-h-[360px] overflow-hidden rounded-[2.25rem] border border-white/10 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.16),transparent_34%),rgba(255,255,255,0.045)] shadow-2xl shadow-black/10">
        <div className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-white/50 to-transparent" />
        <motion.div
          key={activeFeature.title}
          initial={{ opacity: 0, x: direction > 0 ? 72 : -72, filter: "blur(10px)" }}
          animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
          exit={{ opacity: 0, x: direction > 0 ? -72 : 72, filter: "blur(10px)" }}
          transition={{ duration: 0.55, ease }}
          className="min-h-[360px] p-6 sm:p-8"
        >
          <div className="flex h-full flex-col justify-between gap-10">
            <div>
              <div className="mb-8 flex items-center justify-between gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-slate-950 shadow-lg">
                  <Icon className="h-6 w-6" />
                </div>
                <span className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-xs text-slate-300">
                  {activeFeature.eyebrow}
                </span>
              </div>
              <h3 className="max-w-xl text-4xl font-semibold tracking-[-0.04em] text-white sm:text-5xl">
                {activeFeature.title}
              </h3>
              <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-400">
                {activeFeature.body}
              </p>
            </div>

            <div className="rounded-2xl border border-emerald-300/20 bg-emerald-300/[0.07] px-4 py-3 text-sm text-emerald-100">
              {activeFeature.proof}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

function FundPairCard() {
  const rows = [
    ["Fund type", "Diversified flexi-cap", "Multi-asset allocation"],
    ["Current role", "Core equity-style comparison example", "Asset allocation comparison example"],
    ["Expense", "0.63%", "1.05%"],
    ["3Y Return", "+18.8%", "+16.9%"],
    ["Review focus", "Consistency and downside control", "Equity, debt, and commodity mix"],
  ];

  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      className="mt-12 overflow-hidden rounded-[2.25rem] border border-white/10 bg-white/[0.045] shadow-2xl shadow-black/10"
    >
      <div className="grid gap-0 lg:grid-cols-[1fr_1fr]">
        <motion.div variants={fadeUp} className="border-b border-white/10 p-6 lg:border-b-0 lg:border-r">
          <div className="mb-4 inline-flex rounded-full border border-emerald-300/20 bg-emerald-300/[0.08] px-3 py-1 text-xs font-medium text-emerald-100">
            Steadier profile
          </div>
          <h3 className="text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
            Parag Parikh Flexi Cap
          </h3>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-400">
            Used as the first supported fund example for long-term consistency and diversified flexi-cap research.
          </p>
        </motion.div>

        <motion.div variants={fadeUp} className="p-6">
          <div className="mb-4 inline-flex rounded-full border border-sky-300/20 bg-sky-300/[0.08] px-3 py-1 text-xs font-medium text-sky-100">
            Diversified allocation
          </div>
          <h3 className="text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
            ICICI Multi Asset Fund
          </h3>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-400">
            Used as the second supported fund example for multi-asset allocation research across equity, debt, and commodities.
          </p>
        </motion.div>
      </div>

      <div className="border-t border-white/10 bg-slate-950/25 p-4 sm:p-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-white">Live comparison preview</p>
            <p className="mt-1 text-xs text-slate-500">Formatted as a table so long fund names do not break the card layout.</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-xs text-slate-300">
            <Sparkle className="h-3.5 w-3.5 text-emerald-300" weight="fill" />
            MooliqAI explains the difference
          </div>
        </div>

        <div className="overflow-hidden rounded-[1.5rem] border border-white/10">
          {rows.map(([metric, ppfas, icici], index) => {
            const isValNumeric = (str) => /^[\d%.+-]+$/.test(str.replace(/\s+/g, ''));
            return (
              <motion.div
                key={metric}
                variants={fadeUp}
                className={`grid gap-0 text-sm sm:grid-cols-[0.8fr_1fr_1fr] ${index !== rows.length - 1 ? "border-b border-white/10" : ""}`}
              >
                <div className="bg-white/[0.035] px-4 py-3 font-medium text-slate-300">{metric}</div>
                <div className={`border-t border-white/10 px-4 py-3 text-slate-200 sm:border-l sm:border-t-0 ${isValNumeric(ppfas) ? "font-mono text-emerald-300 font-medium" : ""}`}>{ppfas}</div>
                <div className={`border-t border-white/10 px-4 py-3 text-slate-200 sm:border-l sm:border-t-0 ${isValNumeric(icici) ? "font-mono text-emerald-300 font-medium" : ""}`}>{icici}</div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}

export default function MooliqLandingPage() {
  const { scrollYProgress } = useScroll();
  const heroGridY = useTransform(scrollYProgress, [0, 0.25], [0, 120]);
  const heroTextY = useTransform(scrollYProgress, [0, 0.18], [0, -28]);

  return (
    <main className="w-full min-w-0 min-h-screen overflow-hidden scroll-smooth bg-[#020617] text-slate-200">
      <motion.div
        aria-hidden="true"
        className="fixed left-0 top-0 z-50 h-1 bg-emerald-400"
        style={{ scaleX: scrollYProgress, transformOrigin: "0%" }}
      />

      <section className="relative isolate w-full min-w-0 min-h-screen overflow-hidden">
        <motion.div style={{ y: heroGridY }}>
          <FineGrid />
        </motion.div>

        <motion.nav
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease }}
          className="sticky top-4 z-40 mx-auto w-full max-w-7xl px-5 py-5 sm:px-8 lg:px-10"
        >
          <div className="flex items-center justify-between rounded-full border border-white/10 bg-[#090d18]/70 px-3 py-2 shadow-2xl shadow-black/25 backdrop-blur-2xl sm:px-4">
            <a href="#" className="flex items-center gap-3" aria-label="Mooliq home">
              <motion.div
                whileHover={{ rotate: -8, scale: 1.08 }}
                className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white text-slate-950"
              >
                <TrendUp className="h-5 w-5" />
              </motion.div>
              <span className="text-lg font-semibold tracking-tight">Mooliq</span>
            </a>

            <div className="hidden items-center gap-7 text-sm text-slate-400 md:flex">
              <a href="#compare" className="transition hover:text-white">Compare</a>
              <a href="#features" className="transition hover:text-white">Features</a>
              <a href="#how" className="transition hover:text-white">How it works</a>
              <a href="#trust" className="transition hover:text-white">Trust</a>
            </div>

            <div className="flex items-center gap-2">
              <a href="/login" className="hidden rounded-full border border-white/10 bg-white/[0.045] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/[0.09] sm:inline-flex">
                Login
              </a>
              <a href="/dashboard" className="rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-100">
                Try MooliqAI
              </a>
            </div>
          </div>
        </motion.nav>

        <div className="mx-auto w-full max-w-7xl px-5 pb-24 pt-14 sm:px-8 sm:pt-24 lg:px-10">
          <div className="grid gap-12 lg:grid-cols-12 lg:items-center">
            <motion.div
              variants={stagger}
              initial="hidden"
              animate="visible"
              style={{ y: heroTextY }}
              className="lg:col-span-7 text-left"
            >
              <motion.div variants={fadeUp} className="mb-6 flex justify-start">
                <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-sm text-slate-300 shadow-sm backdrop-blur-xl">
                  <Star className="h-4 w-4 text-emerald-300" weight="fill" />
                  Mutual fund comparison workspace
                </span>
              </motion.div>
              <motion.h1
                variants={fadeUp}
                className="text-balance text-5xl font-semibold tracking-[-0.055em] text-white sm:text-7xl lg:text-8xl"
              >
                Mutual fund research, simplified.
              </motion.h1>
              <motion.p
                variants={fadeUp}
                className="mt-7 max-w-2xl text-pretty text-lg leading-8 text-slate-300 sm:text-xl"
              >
                Mooliq centralizes scattered Indian mutual fund factsheets, risk metrics, and NAV history into a clean workspace. Engineered for working professionals who demand quick, data-backed insights.
              </motion.p>
              <motion.div
                variants={fadeUp}
                className="mt-9 flex flex-col items-start justify-start gap-3 sm:flex-row"
              >
                <PremiumButton href="/dashboard">Try MooliqAI</PremiumButton>
                <PremiumButton href="/login" variant="secondary">Login</PremiumButton>
              </motion.div>
              <motion.div variants={stagger} className="mt-8 flex flex-wrap gap-2">
                <Badge>Factsheet consolidation</Badge>
                <Badge>Alpha / Beta / Sharpe</Badge>
                <Badge>Clean side-by-side comparison</Badge>
                <Badge>Explainable AI research</Badge>
              </motion.div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 28, rotateY: -6 }}
              animate={{ opacity: 1, x: 0, rotateY: 0 }}
              transition={{ duration: 0.95, ease, delay: 0.15 }}
              className="lg:col-span-5 relative w-full rounded-[2.25rem] border border-white/12 bg-[#07111f]/90 p-1 shadow-[0_50px_160px_rgba(0,0,0,0.45)] backdrop-blur-2xl [transform-style:preserve-3d] hover:scale-[1.02] transition-transform duration-300"
            >
              <div className="absolute inset-x-10 -top-px h-px bg-gradient-to-r from-transparent via-white/70 to-transparent" />
              <div className="overflow-hidden rounded-[1.9rem] border border-white/10 bg-[#07111f]">
                <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.035] px-5 py-4">
                  <div className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded-full bg-red-400/80" />
                    <span className="h-3 w-3 rounded-full bg-yellow-300/80" />
                    <span className="h-3 w-3 rounded-full bg-emerald-300/80" />
                  </div>
                  <div className="text-xs text-emerald-300 font-semibold tracking-wide">Live Workspace</div>
                </div>

                <div className="p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-white/5 pb-3">
                    <div>
                      <h4 className="text-sm font-semibold text-white">Parag Parikh Flexi Cap</h4>
                      <p className="text-xs text-slate-400">Direct Plan - Growth</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm font-semibold text-emerald-300">+22.4%</p>
                      <p className="text-[10px] text-slate-500">1Y Return</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between border-b border-white/5 pb-3">
                    <div>
                      <h4 className="text-sm font-semibold text-white">ICICI Pru Multi Asset</h4>
                      <p className="text-xs text-slate-400">Direct Plan - Growth</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm font-semibold text-emerald-300">+19.8%</p>
                      <p className="text-[10px] text-slate-500">1Y Return</p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-emerald-300/20 bg-emerald-300/[0.05] p-3 text-xs leading-relaxed text-slate-200">
                    <div className="flex items-center gap-1.5 font-semibold text-emerald-300 mb-1">
                      <Sparkle className="h-3.5 w-3.5" weight="fill" />
                      MooliqAI Synthesis
                    </div>
                    Parag Parikh Flexi Cap demonstrates superior risk-adjusted performance with a Sharpe Ratio of 1.22.
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          <div className="mt-24 border-t border-white/10 pt-16">
            <div className="mb-8 text-center">
              <span className="text-xs uppercase tracking-[0.22em] text-emerald-300 font-semibold">Workspace Walkthrough</span>
              <h3 className="mt-3 text-3xl font-semibold text-white">Factsheet Comparison Engine</h3>
            </div>
            <HeroPreview />
          </div>
          
          <LogoCloud />

          <motion.div
            initial={{ opacity: 0, y: 18, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.7, ease, delay: 0.55 }}
            className="mx-auto mt-10 max-w-3xl rounded-full border border-sky-300/20 bg-sky-300/[0.07] px-5 py-3 text-center text-sm text-sky-100/90 backdrop-blur-xl"
          >
            <span className="inline-flex items-center justify-center gap-2">
              <Clock className="h-4 w-4 text-sky-300" />
              Stock coverage is on the way. Mooliq currently focuses on mutual fund comparison first, starting with the live Parag Parikh and ICICI pipeline.
            </span>
          </motion.div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-5 py-16 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 28, filter: "blur(10px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.75, ease }}
          className="relative overflow-hidden rounded-[2.25rem] border border-sky-300/20 bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.16),transparent_34%),rgba(255,255,255,0.04)] p-6 sm:p-10"
        >
          <div className="grid gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-sky-300">Coming next</p>
              <h2 className="mt-4 text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">
                Stock coverage is on the way.
              </h2>
              <p className="mt-5 text-lg leading-8 text-slate-400">
                Mooliq is starting with mutual fund comparison as the MVP. The current pipeline is set up for Parag Parikh and ICICI funds first. Broader AMC coverage, Indian stock research, stock comparison, and valuation metrics are planned before the full public launch.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["Current coverage", "Parag Parikh + ICICI pipeline"],
                ["Next coverage", "Add all major AMCs"],
                ["Stock module", "Planned after fund MVP"],
                ["Full launch", "After coverage expansion"],
              ].map(([title, body], index) => (
                <motion.div
                  key={title}
                  initial={{ opacity: 0, y: 14 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.08 }}
                  className="rounded-3xl border border-white/10 bg-slate-950/45 p-5"
                >
                  <p className="text-lg font-semibold text-white">{title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{body}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>
      </section>

      <section id="compare" className="mx-auto w-full max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
          eyebrow="Deep Screening"
          title="Unbiased research. Zero noise."
          body="Compare funds side-by-side on performance consistency, risk indicators, and costs. Mooliq standardizes scattered disclosures into one unified dashboard."
        />
        <FundPairCard />
      </section>

      <section id="features" className="mx-auto w-full max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
          <SectionHeading
            align="left"
            eyebrow="Intelligence"
            title="Explore mutual fund DNA & risk signals."
            body="From instant risk-adjusted metrics to natural language explanations, Mooliq gives you the tools to screen and compare Indian mutual funds with speed."
          />
          <FeatureCarousel />
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 30, filter: "blur(10px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.8, ease }}
          className="relative overflow-hidden rounded-[2.5rem] border border-white/10 bg-[#0F172A] p-6 sm:p-10"
        >
          <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-300">Data integrity</p>
              <h2 className="mt-4 text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">Unified snapshots for deep screening.</h2>
              <p className="mt-5 text-lg leading-8 text-slate-400">Instantly view essential metrics: NAV freshness, rolling returns, portfolio turnover, and expense ratios. No more digging through confusing PDF disclosures.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {[
                ["Current pipeline", "PPFAS + ICICI", "Live"],
                ["Next coverage", "Major AMCs", "Planned"],
                ["Data scope", "NAV + factsheet", "Expanding"],
                ["Full launch", "After coverage", "Later"],
              ].map(([label, title, value], index) => (
                <motion.div
                  key={label}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.07 }}
                  whileHover={{ y: -6 }}
                  className="rounded-[1.5rem] border border-white/10 bg-slate-950/45 p-5"
                >
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
                  <p className="mt-4 text-lg font-semibold text-white">{title}</p>
                  <p className="mt-2 text-2xl font-semibold text-emerald-300">{value}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>
      </section>

      <section id="how" className="mx-auto w-full max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
          eyebrow="Workflow"
          title="From fund factsheets to explainable comparison."
          body="Discover how Mooliq parses and updates fund details to keep your research workflow seamless."
        />
        <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {steps.slice(0, 4).map(([number, title, body]) => (
            <motion.div key={title} variants={fadeUp} whileHover={{ y: -6 }} className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-6">
              <p className="text-sm text-emerald-300">{number}</p>
              <h3 className="mt-6 text-xl font-semibold text-white">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-slate-400">{body}</p>
            </motion.div>
          ))}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24, filter: "blur(10px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.7, ease }}
          className="mt-5 rounded-[2rem] border border-white/10 bg-[#0F172A] p-6 sm:p-8"
        >
          <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-sky-300">Primary focus now</p>
              <h3 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
                Coverage expansion comes before the full stock module.
              </h3>
              <p className="mt-4 text-sm leading-7 text-slate-400">
                Mooliq is currently focused on strengthening mutual fund coverage across major AMCs. Stock coverage is planned, but the immediate priority is making the fund comparison dataset broader and more reliable.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                ["Now", "PPFAS + ICICI", "Live pipeline"],
                ["Next", "Major AMCs", "Coverage expansion"],
                ["Later", "Stock coverage", "Planned module"],
              ].map(([label, title, body]) => (
                <div key={label} className="rounded-2xl border border-white/10 bg-slate-950/45 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
                  <p className="mt-3 font-semibold text-white">{title}</p>
                  <p className="mt-2 text-xs leading-5 text-slate-400">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
          eyebrow="Use cases"
          title="Ask anything. Research instantly."
          body="Discover how working professionals and advanced investors query Mooliq to extract key comparison points."
        />
        <MarqueePrompts />
      </section>

      <section id="trust" className="mx-auto w-full max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <SectionHeading
            align="left"
            eyebrow="Safety first"
            title="Unbiased intelligence. No advisory conflicts."
            body="Mooliq is engineered strictly for self-directed research and education. We never recommend products, take commissions, or make buy/sell calls."
          />
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} className="grid gap-4 sm:grid-cols-2">
            {[
              [Lock, "No advisory language", "Avoids buy/sell calls, portfolio advice, and recommendation phrasing."],
              [MagnifyingGlass, "Metric visibility", "Keeps source metrics visible beside the AI explanation."],
              [Database, "Freshness signals", "Makes update status part of the product experience."],
              [ShieldCheck, "User protection", "Frames output as education and research only."],
            ].map(([Icon, title, body]) => (
              <motion.div key={title} variants={fadeUp} whileHover={{ y: -6 }} className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-6">
                <Icon className="h-6 w-6 text-emerald-300" />
                <h3 className="mt-5 text-xl font-semibold text-white">{title}</h3>
                <p className="mt-3 leading-7 text-slate-400">{body}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      <section id="disclaimer" className="mx-auto w-full max-w-7xl px-5 py-12 sm:px-8 lg:px-10">
        <div className="rounded-[2rem] border border-amber-300/20 bg-amber-300/[0.055] p-6 text-center sm:p-8">
          <h2 className="text-2xl font-semibold text-white">Research-only disclaimer</h2>
          <p className="mx-auto mt-4 max-w-4xl leading-8 text-amber-50/80">
            Mooliq is for research and education only. It does not provide financial advice, investment recommendations, portfolio management, or buy/sell calls. Current coverage is limited while the pipeline expands across major AMCs. Always verify data independently before making financial decisions.
          </p>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-5 pb-24 pt-12 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 28, filter: "blur(10px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.75, ease }}
          className="relative overflow-hidden rounded-[2.75rem] border border-white/10 bg-[#0F172A] p-8 text-center shadow-2xl shadow-black/20 sm:p-16"
        >
          <div className="relative">
            <h2 className="mx-auto max-w-4xl text-4xl font-semibold tracking-[-0.04em] text-white sm:text-6xl">
              Start comparing Indian mutual funds with explainable AI.
            </h2>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-400">
              Try MooliqAI, compare funds side by side, and turn scattered fund data into a clean research workflow. Major AMC coverage and stock coverage are on the way before full launch.
            </p>
            <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
              <PremiumButton href="/dashboard">Try MooliqAI</PremiumButton>
              <PremiumButton href="/login" variant="secondary">Login</PremiumButton>
            </div>
          </div>
        </motion.div>
      </section>
    </main>
  );
}
