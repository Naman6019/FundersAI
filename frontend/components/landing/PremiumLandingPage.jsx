"use client";

import React, { useEffect, useState } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Database,
  LineChart,
  Lock,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  TrendingUp,
  WalletCards,
} from "lucide-react";

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
    icon: WalletCards,
    title: "Fund-to-fund comparison",
    eyebrow: "Compare",
    body: "Compare supported Indian mutual funds across returns, NAV movement, AUM, expense ratio, risk metrics, and consistency. Coverage is expanding across major AMCs.",
    proof: "Current pipeline: Parag Parikh + ICICI",
  },
  {
    icon: BrainCircuit,
    title: "Explainable AI summaries",
    eyebrow: "Understand",
    body: "Turn dense fund metrics into clear research notes without hiding the underlying numbers.",
    proof: "Designed for research, not advice",
  },
  {
    icon: Database,
    title: "Coverage expansion",
    eyebrow: "Expanding",
    body: "The current focus is expanding fund coverage across major AMCs before the broader public launch.",
    proof: "Major AMC coverage is the priority now",
  },
  {
    icon: LineChart,
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
    icon: BarChart3,
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
      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" />
      {children}
    </motion.span>
  );
}

function HeroPreview() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 42, scale: 0.96, rotateX: 7 }}
      animate={{ opacity: 1, y: 0, scale: 1, rotateX: 0 }}
      transition={{ duration: 0.95, ease, delay: 0.25 }}
      className="relative mx-auto mt-16 max-w-6xl rounded-[2.25rem] border border-white/12 bg-white/[0.06] p-2 shadow-[0_50px_160px_rgba(0,0,0,0.45)] backdrop-blur-2xl"
    >
      <div className="absolute inset-x-10 -top-px h-px bg-gradient-to-r from-transparent via-white/70 to-transparent" />
      <div className="overflow-hidden rounded-[1.9rem] border border-white/10 bg-[#07111f]">
        <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.035] px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-red-400/80" />
            <span className="h-3 w-3 rounded-full bg-yellow-300/80" />
            <span className="h-3 w-3 rounded-full bg-emerald-300/80" />
          </div>
          <div className="hidden rounded-full border border-white/10 bg-black/20 px-4 py-1.5 text-xs text-slate-400 sm:block">
            mooliq.com/fund-comparison
          </div>
          <div className="text-xs text-emerald-300">NAV updated today</div>
        </div>

        <div className="grid gap-4 p-4 lg:grid-cols-[0.85fr_1.45fr_0.9fr]">
          <motion.div
            initial={{ opacity: 0, x: -18 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease }}
            className="rounded-[1.5rem] border border-white/10 bg-white/[0.045] p-5"
          >
            <div className="mb-5 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <Sparkles className="h-4 w-4 text-emerald-300" />
                MooliqAI
              </div>
              <span className="rounded-full bg-emerald-300/10 px-2.5 py-1 text-[11px] text-emerald-200">Research only</span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="rounded-2xl bg-white/[0.06] p-3 text-slate-300">
                Compare these funds for long-term consistency.
              </div>
              <div className="rounded-2xl border border-emerald-300/20 bg-emerald-300/[0.07] p-3 leading-6 text-slate-200">
                Parag Parikh appears steadier on risk-adjusted metrics, while ICICI Multi Asset brings a multi-asset allocation profile that needs review across equity, debt, and commodity exposure.
              </div>
              <div className="rounded-2xl bg-amber-300/[0.07] p-3 text-xs leading-5 text-amber-100/80">
                This is not investment advice. Verify data independently.
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 22 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease, delay: 0.1 }}
            className="rounded-[1.5rem] border border-white/10 bg-white/[0.045] p-5"
          >
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-white">Fund comparison canvas</p>
                <p className="mt-1 text-xs text-slate-400">Parag Parikh Flexi Cap vs ICICI Multi Asset Fund</p>
              </div>
              <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-300">Side-by-side</span>
            </div>

            <div className="grid gap-3 sm:grid-cols-4">
              {comparisonMetrics.map(([label, value, helper], index) => (
                <motion.div
                  key={label}
                  initial={{ opacity: 0, y: 14 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.48, ease, delay: 0.18 + index * 0.06 }}
                  whileHover={{ y: -5 }}
                  className="rounded-2xl border border-white/10 bg-slate-950/45 p-3"
                >
                  <p className="text-[11px] text-slate-500">{label}</p>
                  <p className="mt-2 text-lg font-semibold text-white">{value}</p>
                  <p className="mt-1 text-[11px] text-slate-500">{helper}</p>
                </motion.div>
              ))}
            </div>

            <div className="mt-5 rounded-2xl border border-white/10 bg-[linear-gradient(180deg,rgba(16,185,129,0.12),rgba(2,6,23,0.12))] p-4">
              <svg viewBox="0 0 560 150" className="h-44 w-full overflow-visible">
                <motion.path
                  d="M0 116 C52 86 92 102 140 74 C192 42 232 74 282 50 C340 22 388 48 438 26 C492 2 524 26 560 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="4"
                  className="text-emerald-300"
                  initial={{ pathLength: 0, opacity: 0 }}
                  whileInView={{ pathLength: 1, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 1.7, ease, delay: 0.3 }}
                />
                <motion.path
                  d="M0 126 C58 112 96 98 145 104 C198 110 236 72 285 88 C340 106 384 58 438 70 C492 82 520 42 560 52"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  className="text-sky-300/80"
                  initial={{ pathLength: 0, opacity: 0 }}
                  whileInView={{ pathLength: 1, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 1.85, ease, delay: 0.48 }}
                />
              </svg>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 18 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease, delay: 0.16 }}
            className="rounded-[1.5rem] border border-white/10 bg-white/[0.045] p-5"
          >
            <p className="text-sm font-semibold text-white">Data health</p>
            <div className="mt-4 space-y-3">
              {[
                ["MF NAV", "Fresh"],
                ["AUM / TER", "Synced"],
                ["Risk metrics", "Ready"],
                ["Factsheets", "Indexed"],
              ].map(([label, value], index) => (
                <motion.div
                  key={label}
                  initial={{ opacity: 0, x: 12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.42, delay: 0.24 + index * 0.07 }}
                  className="flex items-center justify-between rounded-2xl border border-white/8 bg-slate-950/35 px-3 py-3 text-xs"
                >
                  <span className="text-slate-400">{label}</span>
                  <span className="text-emerald-300">{value}</span>
                </motion.div>
              ))}
            </div>
            <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.035] p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Next module</p>
              <p className="mt-2 font-semibold text-white">Stock research</p>
              <p className="mt-2 text-xs leading-5 text-slate-400">Stock coverage is on the way. Mutual fund comparison stays the current MVP.</p>
            </div>
          </motion.div>
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
              className={`rounded-full border px-4 py-2 text-xs font-medium transition-all duration-300 ${
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
              className={`h-2.5 rounded-full transition-all duration-300 ${
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
            <Sparkles className="h-3.5 w-3.5 text-emerald-300" />
            MooliqAI explains the difference
          </div>
        </div>

        <div className="overflow-hidden rounded-[1.5rem] border border-white/10">
          {rows.map(([metric, ppfas, icici], index) => (
            <motion.div
              key={metric}
              variants={fadeUp}
              className={`grid gap-0 text-sm sm:grid-cols-[0.8fr_1fr_1fr] ${index !== rows.length - 1 ? "border-b border-white/10" : ""}`}
            >
              <div className="bg-white/[0.035] px-4 py-3 font-medium text-slate-300">{metric}</div>
              <div className="border-t border-white/10 px-4 py-3 text-slate-200 sm:border-l sm:border-t-0">{ppfas}</div>
              <div className="border-t border-white/10 px-4 py-3 text-slate-200 sm:border-l sm:border-t-0">{icici}</div>
            </motion.div>
          ))}
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
    <main className="min-h-screen overflow-hidden scroll-smooth bg-[#05070f] text-white">
      <motion.div
        aria-hidden="true"
        className="fixed left-0 top-0 z-50 h-1 bg-gradient-to-r from-emerald-300 via-sky-300 to-violet-300"
        style={{ scaleX: scrollYProgress, transformOrigin: "0%" }}
      />

      <section className="relative isolate min-h-screen overflow-hidden">
        <Glow className="left-[-8rem] top-[-8rem] h-96 w-96 bg-emerald-400/20" />
        <Glow className="right-[-10rem] top-24 h-[30rem] w-[30rem] bg-sky-400/16" delay={1.1} />
        <Glow className="bottom-10 left-1/3 h-80 w-80 bg-violet-400/10" delay={2.4} />
        <motion.div style={{ y: heroGridY }}>
          <FineGrid />
        </motion.div>

        <motion.nav
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease }}
          className="sticky top-4 z-40 mx-auto max-w-7xl px-5 py-5 sm:px-8 lg:px-10"
        >
          <div className="flex items-center justify-between rounded-full border border-white/10 bg-[#090d18]/70 px-3 py-2 shadow-2xl shadow-black/25 backdrop-blur-2xl sm:px-4">
            <a href="#" className="flex items-center gap-3" aria-label="Mooliq home">
              <motion.div
                whileHover={{ rotate: -8, scale: 1.08 }}
                className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white text-slate-950"
              >
                <TrendingUp className="h-5 w-5" />
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

        <div className="mx-auto max-w-7xl px-5 pb-24 pt-14 sm:px-8 sm:pt-24 lg:px-10">
          <motion.div variants={stagger} initial="hidden" animate="visible" style={{ y: heroTextY }} className="mx-auto max-w-5xl text-center">
            <motion.div variants={fadeUp} className="mb-6 flex justify-center">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-sm text-slate-300 shadow-sm backdrop-blur-xl">
                <Star className="h-4 w-4 fill-emerald-300 text-emerald-300" />
                Mutual fund comparison MVP
              </span>
            </motion.div>
            <motion.h1 variants={fadeUp} className="text-balance text-5xl font-semibold tracking-[-0.055em] text-white sm:text-7xl lg:text-8xl">
              Compare Indian mutual funds with calm, explainable AI.
            </motion.h1>
            <motion.p variants={fadeUp} className="mx-auto mt-7 max-w-3xl text-pretty text-lg leading-8 text-slate-300 sm:text-xl">
              Mooliq helps you compare funds across NAV, returns, expense ratio, AUM, alpha, beta, Sharpe ratio, and risk signals. The live pipeline starts with Parag Parikh and ICICI funds, with major AMC coverage planned before full launch.
            </motion.p>
            <motion.div variants={fadeUp} className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <PremiumButton href="/dashboard">Try MooliqAI</PremiumButton>
              <PremiumButton href="/login" variant="secondary">Login</PremiumButton>
            </motion.div>
            <motion.div variants={stagger} className="mt-8 flex flex-wrap justify-center gap-2">
              <Badge>NAV + returns</Badge>
              <Badge>Expense ratio + AUM</Badge>
              <Badge>Alpha / Beta / Sharpe</Badge>
              <Badge>Research-only</Badge>
              <Badge>Stock coverage on the way</Badge>
            </motion.div>
          </motion.div>

          <HeroPreview />
          <LogoCloud />

          <motion.div
            initial={{ opacity: 0, y: 18, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.7, ease, delay: 0.55 }}
            className="mx-auto mt-10 max-w-3xl rounded-full border border-sky-300/20 bg-sky-300/[0.07] px-5 py-3 text-center text-sm text-sky-100/90 backdrop-blur-xl"
          >
            <span className="inline-flex items-center justify-center gap-2">
              <Clock3 className="h-4 w-4 text-sky-300" />
              Stock coverage is on the way. Mooliq currently focuses on mutual fund comparison first, starting with the live Parag Parikh and ICICI pipeline.
            </span>
          </motion.div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-10">
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

      <section id="compare" className="mx-auto max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
          eyebrow="MVP focus"
          title="Make the page sell one thing first: fund comparison."
          body="The page should feel intentionally focused. Every major section should guide the visitor toward comparing mutual funds, while clearly stating that major AMC coverage and stock coverage are on the way."
        />
        <FundPairCard />
      </section>

      <section id="features" className="mx-auto max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
          <SectionHeading
            align="left"
            eyebrow="Capabilities"
            title="A guided capability showcase, not a wall of cards."
            body="The cards auto-advance in a defined order when the user reaches this section. Users can also select a dot or card label to view a specific capability."
          />
          <FeatureCarousel />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 30, filter: "blur(10px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.8, ease }}
          className="relative overflow-hidden rounded-[2.5rem] border border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.14),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(16,185,129,0.12),transparent_34%),rgba(255,255,255,0.045)] p-6 sm:p-10"
        >
          <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-300">Fund snapshot</p>
              <h2 className="mt-4 text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">Fund data should feel comparable, not scattered.</h2>
              <p className="mt-5 text-lg leading-8 text-slate-400">Show the user what matters first: NAV freshness, expense ratio, AUM, returns, and risk flags. Avoid stock-first content until that module is ready.</p>
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

      <section id="how" className="mx-auto max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
          eyebrow="Workflow"
          title="From fund factsheets to explainable comparison."
          body="A premium landing page should make the workflow obvious before users click anything."
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
          className="mt-5 rounded-[2rem] border border-sky-300/20 bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.14),transparent_35%),rgba(255,255,255,0.04)] p-6 sm:p-8"
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

      <section className="mx-auto max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
          eyebrow="Research examples"
          title="Make the first action obvious."
          body="Use polished prompt chips to show the actual use cases your MVP supports."
        />
        <MarqueePrompts />
      </section>

      <section id="trust" className="mx-auto max-w-7xl px-5 py-24 sm:px-8 lg:px-10">
        <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <SectionHeading
            align="left"
            eyebrow="Trust layer"
            title="Research-only by design."
            body="Finance products need a stronger trust layer than normal SaaS pages. Keep the guardrails visible but elegant."
          />
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} className="grid gap-4 sm:grid-cols-2">
            {[
              [Lock, "No advisory language", "Avoids buy/sell calls, portfolio advice, and recommendation phrasing."],
              [Search, "Metric visibility", "Keeps source metrics visible beside the AI explanation."],
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

      <section id="disclaimer" className="mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:px-10">
        <div className="rounded-[2rem] border border-amber-300/20 bg-amber-300/[0.055] p-6 text-center sm:p-8">
          <h2 className="text-2xl font-semibold text-white">Research-only disclaimer</h2>
          <p className="mx-auto mt-4 max-w-4xl leading-8 text-amber-50/80">
            Mooliq is for research and education only. It does not provide financial advice, investment recommendations, portfolio management, or buy/sell calls. Current coverage is limited while the pipeline expands across major AMCs. Always verify data independently before making financial decisions.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-24 pt-12 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 28, filter: "blur(10px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.75, ease }}
          className="relative overflow-hidden rounded-[2.75rem] border border-white/10 bg-white/[0.055] p-8 text-center shadow-2xl shadow-black/20 sm:p-16"
        >
          <Glow className="left-1/2 top-0 h-80 w-80 -translate-x-1/2 bg-emerald-400/20" />
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
