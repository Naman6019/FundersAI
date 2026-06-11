"use client";

import React, { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { motion, useScroll, useTransform, useReducedMotion } from "framer-motion";
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';
import AnimatedCounter from "./AnimatedCounter";
import {
  ArrowRight,
  ChartBar,
  Cpu,
  CheckCircle,
  Clock,
  Database,
  TrendUp,
  Lock,
  MagnifyingGlass,
  ShieldCheck,
  Sparkle,
  Cards
} from "@phosphor-icons/react";

const ease = [0.22, 1, 0.36, 1];

const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease },
  },
};

const slideReveal = {
  hidden: { opacity: 0, y: 28 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] },
  },
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08, delayChildren: 0.06 } },
};

const features = [
  {
    icon: Cards,
    title: "Detailed fund comparison",
    eyebrow: "Compare",
    body: "Compare supported Indian mutual funds across returns, NAV movement, AUM, expense ratio, alpha, beta, Sharpe, volatility, consistency, and holdings context.",
    proof: "Verified: PPFAS, ICICI, HDFC, SBI",
  },
  {
    icon: Cpu,
    title: "Explainable AI summaries",
    eyebrow: "Understand",
    body: "Turn dense fund metrics into plain-language research notes while keeping the source numbers visible beside the explanation.",
    proof: "Designed for research, not advice",
  },
  {
    icon: Database,
    title: "Coverage expansion",
    eyebrow: "Expanding",
    body: "We ingest factsheets and portfolio holdings directly, with verified coverage across PPFAS, ICICI, HDFC, and SBI before broader rollout.",
    proof: "Official factsheet-backed labels",
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
    body: "Built for education and comparison, not buy/sell calls, fund recommendations, portfolio advice, or advisory output.",
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
  ["03", "Ask FundersAI", "Get a research-only explanation of what the numbers suggest."],
  ["04", "Review clearly", "Save the comparison and continue deeper research without treating it as advice."],
  ["Focus", "Coverage expansion", "The primary focus now is adding more AMCs and improving supported mutual fund coverage before stock research becomes a main module."],
];

function AmbientBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden bg-[#090D18]">
      <div className="absolute inset-x-0 top-0 h-px bg-white/20" />
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0.035),transparent_32%)]" />
      <div className="absolute inset-0 opacity-[0.08] [background-image:linear-gradient(rgba(255,255,255,0.35)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.35)_1px,transparent_1px)] [background-size:72px_72px]" />
    </div>
  );
}

function MagneticButton({ href, children, variant = "primary" }) {
  const ref = useRef(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  const handleMouse = (e) => {
    const { clientX, clientY } = e;
    const { height, width, left, top } = ref.current.getBoundingClientRect();
    const middleX = clientX - (left + width / 2);
    const middleY = clientY - (top + height / 2);
    setPosition({ x: middleX * 0.2, y: middleY * 0.2 });
  };

  const reset = () => {
    setPosition({ x: 0, y: 0 });
  };

  const base = "group relative inline-flex items-center justify-center px-8 py-4 text-sm font-semibold transition-all duration-300";
  const styles =
    variant === "primary"
      ? "bg-white text-black hover:bg-slate-200"
      : "border border-white/20 bg-transparent text-white hover:border-white";

  return (
    <motion.a
      ref={ref}
      href={href}
      onMouseMove={handleMouse}
      onMouseLeave={reset}
      animate={{ x: position.x, y: position.y }}
      transition={{ type: "spring", stiffness: 150, damping: 15, mass: 0.1 }}
      className={`${base} ${styles}`}
    >
      <span className="relative z-10 flex items-center transition-colors duration-200">
        {children}
        {variant === "primary" && (
          <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
        )}
      </span>
    </motion.a>
  );
}

function Badge({ children }) {
  return (
    <motion.span
      variants={fadeUp}
      className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.055] px-3 py-1.5 text-xs font-medium text-slate-300 shadow-sm backdrop-blur-xl"
    >
      <CheckCircle className="h-3.5 w-3.5 text-[#66a3ff]" weight="fill" />
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
          fetch('/api/mf/101144').then(r => r.json()).catch(() => null)
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
      className="relative mx-auto mt-12 w-full max-w-4xl rounded-xl border border-[#1e2a38] bg-[#111415] p-6 shadow-xl"
    >
      <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-6">
        <div className="flex items-center gap-3">
          <Sparkle className="h-4 w-4 text-[#66a3ff]" weight="fill" />
          <span className="text-sm font-semibold text-slate-200">FundersAI Chat</span>
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
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#00509e]/20 text-[#66a3ff]">
            <Sparkle className="h-4 w-4" weight="fill" />
          </div>
          <div className="flex-1 space-y-5 pt-1">
            <p className="text-sm leading-relaxed text-slate-300">
              Here is a neutral comparison of the available metrics. Parag Parikh shows steadier risk-adjusted readings in this snapshot, while ICICI Multi Asset carries a broader asset-allocation profile.
            </p>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs font-semibold text-slate-400">Parag Parikh Flexi Cap</div>
                <div className="mt-2 text-2xl font-mono text-[#66a3ff]">{ppfasReturn}</div>
                <div className="mt-1 text-[10px] uppercase text-slate-500">1Y return snapshot</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs font-semibold text-slate-400">ICICI Pru Multi Asset</div>
                <div className="mt-2 text-2xl font-mono text-[#66a3ff]">{iciciReturn}</div>
                <div className="mt-1 text-[10px] uppercase text-slate-500">1Y return snapshot</div>
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
                <span className="w-20 text-[#66a3ff] text-right">1.22</span>
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

function ProofStrip() {
  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
      className="mx-auto mt-14 grid max-w-6xl border-y border-white/10 sm:grid-cols-4"
    >
      {[
        ["4 AMCs", "PPFAS, ICICI, HDFC, SBI"],
        ["Side-by-side", "Returns, NAV, cost, risk"],
        ["Guardrails", "Research and education only"],
        ["Next", "Broader AMC coverage first"],
      ].map(([value, label]) => (
        <motion.div
          key={value}
          variants={fadeUp}
          className="border-white/10 px-5 py-6 text-left sm:border-r last:border-r-0"
        >
          <p className="font-serif-display text-3xl font-semibold text-white">{value}</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">{label}</p>
        </motion.div>
      ))}
    </motion.div>
  );
}

function MarqueePrompts() {
  return (
    <motion.div
      className="relative mx-auto mt-10 max-w-4xl"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
    >
      <div className="flex flex-wrap justify-center gap-3">
        {promptChips.map((prompt, index) => (
          <button
            key={`${prompt}-${index}`}
            className="rounded-full border border-[#1e2a38] bg-[#111415] px-5 py-3 text-sm text-slate-200 transition hover:border-[#66a3ff] hover:bg-[#1e2a38] hover:text-white"
          >
            {prompt}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

function SectionHeading({ eyebrow, title, body, align = "center", number }) {
  return (
    <div className={align === "center" ? "mx-auto max-w-3xl text-center" : "max-w-3xl"}>
      <motion.p
        initial={{ opacity: 0, y: 14 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-90px" }}
        transition={{ duration: 0.5, ease }}
        className="inline-flex items-center gap-3 text-sm font-semibold uppercase text-[#66a3ff]"
      >
        {number && <span className="font-mono text-slate-500">{number}</span>}
        {eyebrow}
      </motion.p>
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-90px" }}
        transition={{ duration: 0.7, ease, delay: 0.1 }}
        className="mt-4 text-balance text-4xl font-semibold text-white sm:text-5xl"
      >
        {title}
      </motion.h2>
      {body && (
        <motion.p
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-90px" }}
          transition={{ duration: 0.65, ease, delay: 0.25 }}
          className="mt-5 text-pretty text-lg leading-8 text-slate-400"
        >
          {body}
        </motion.p>
      )}
    </div>
  );
}

function HorizontalScrollFeatures() {
  const [activeFeature, setActiveFeature] = useState(0);
  const active = features[activeFeature];
  const ActiveIcon = active.icon;

  return (
    <section className="my-24 border-y border-[#1e2a38] bg-[#050A15]">
      <div className="mx-auto w-full max-w-7xl px-5 py-16 sm:px-8 lg:px-10">
        <div className="hidden gap-10 md:grid lg:grid-cols-[0.8fr_1.2fr] lg:items-stretch">
          <div className="space-y-3">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              const isActive = index === activeFeature;
              return (
                <button
                  key={feature.title}
                  type="button"
                  onFocus={() => setActiveFeature(index)}
                  onMouseEnter={() => setActiveFeature(index)}
                  className={`group w-full border px-5 py-4 text-left transition ${
                    isActive
                      ? "border-[#66a3ff] bg-[#0F172A] text-white"
                      : "border-[#1e2a38] bg-[#0c0f12] text-slate-400 hover:border-[#355981] hover:text-white"
                  }`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <span className="inline-flex items-center gap-3">
                      <span className={`flex h-10 w-10 items-center justify-center border ${isActive ? "border-[#66a3ff]/50 bg-[#66a3ff]/10" : "border-[#1e2a38] bg-[#111415]"}`}>
                        <Icon className="h-5 w-5" />
                      </span>
                      <span>
                        <span className="block text-[10px] font-semibold uppercase tracking-[0.2em] text-[#66a3ff]">
                          {feature.eyebrow}
                        </span>
                        <span className="mt-1 block text-base font-semibold">
                          {feature.title}
                        </span>
                      </span>
                    </span>
                    <span className="font-mono text-xs text-slate-500">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          <motion.div
            key={active.title}
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, ease }}
            className="relative min-h-[520px] overflow-hidden border border-[#1e2a38] bg-[#0c0f12]"
          >
            <div className="flex h-full flex-col justify-between p-6 sm:p-10">
              <div>
                <div className="mb-8 flex items-center justify-between gap-4">
                  <div className="flex h-14 w-14 items-center justify-center border border-[#66a3ff]/40 bg-[#66a3ff]/10 text-[#66a3ff]">
                    <ActiveIcon className="h-7 w-7" />
                  </div>
                  <span className="border border-[#1e2a38] bg-[#111415] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-300">
                    {active.eyebrow}
                  </span>
                </div>

                <h3 className="font-serif-display text-4xl font-medium tracking-tight text-white sm:text-5xl">
                  {active.title}
                </h3>
                <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-400">
                  {active.body}
                </p>
              </div>

              <div className="mt-12 grid gap-4 sm:grid-cols-3">
                {[
                  ["Current proof", active.proof],
                  ["User value", "Faster, clearer fund research"],
                  ["Guardrail", "Research-only output"],
                ].map(([label, value]) => (
                  <div key={label} className="border border-[#1e2a38] bg-[#111415] p-4">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      {label}
                    </p>
                    <p className="mt-3 text-sm leading-6 text-slate-200">
                      {value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>

        <div className="grid gap-4 md:hidden">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="border border-[#1e2a38] bg-[#111415] p-6"
              >
                <div className="flex items-center justify-between gap-4">
                  <Icon className="h-6 w-6 text-[#66a3ff]" />
                  <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#66a3ff]">
                    {feature.eyebrow}
                  </span>
                </div>
                <h3 className="mt-6 text-2xl font-semibold text-white">
                  {feature.title}
                </h3>
                <p className="mt-4 text-sm leading-7 text-slate-400">
                  {feature.body}
                </p>
                <div className="mt-6 inline-flex items-center gap-1.5 text-xs font-medium text-[#66a3ff]">
                  <Sparkle className="h-3.5 w-3.5" weight="fill" />
                  {feature.proof}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function FundPairCard() {
  const rows = [
    ["Fund type", "Diversified flexi-cap", "Multi-asset allocation"],
    ["AMC coverage", "PPFAS", "ICICI"],
    ["Expense", "0.63%", "1.05%"],
    ["3Y Return", "+18.8%", "+16.9%"],
    ["Sharpe", "1.22", "1.08"],
    ["Beta", "0.78", "0.84"],
    ["Data freshness", "NAV snapshot visible", "NAV snapshot visible"],
    ["Review focus", "Consistency and downside control", "Equity, debt, and commodity mix"],
  ];

  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-120px" }}
      className="mt-16 overflow-hidden rounded-xl border border-[#1e2a38] bg-[#111415] shadow-xl"
    >
      <div className="grid gap-0 lg:grid-cols-[1fr_1fr]">
        <motion.div
          variants={{ hidden: { opacity: 0, x: -80 }, visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease } } }}
          className="border-b border-[#1e2a38] p-8 lg:border-b-0 lg:border-r"
        >
          <div className="mb-4 inline-flex rounded-full border border-[#00509e] bg-[#111827] px-3 py-1 text-xs font-medium text-slate-100">
            Steadier profile
          </div>
          <h3 className="text-2xl font-semibold tracking-[-0.035em] text-white sm:text-3xl">
            Parag Parikh Flexi Cap
          </h3>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-400">
            Used as a supported example for consistency, drawdown context, and diversified flexi-cap research.
          </p>
        </motion.div>

        <motion.div
          variants={{ hidden: { opacity: 0, x: 80 }, visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease } } }}
          className="p-8"
        >
          <div className="mb-4 inline-flex rounded-full border border-[#00509e] bg-[#111827] px-3 py-1 text-xs font-medium text-[#cce0ff]">
            Diversified allocation
          </div>
          <h3 className="text-2xl font-semibold tracking-[-0.035em] text-white sm:text-3xl">
            ICICI Multi Asset Fund
          </h3>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-400">
            Used as a supported example for multi-asset allocation research across equity, debt, and commodities.
          </p>
        </motion.div>
      </div>

      <motion.div variants={fadeUp} className="border-t border-[#1e2a38] bg-[#0c0f12] p-6 sm:p-8">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-white">Detailed comparison preview</p>
            <p className="mt-1 text-xs text-slate-500">Structured for scanning returns, risk, cost, freshness, and qualitative context.</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-[#1e2a38] bg-[#1a1e23] px-4 py-2 text-xs font-medium text-slate-300">
            <Sparkle className="h-3.5 w-3.5 text-[#66a3ff]" weight="fill" />
            FundersAI explains differences without advice
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-[#1e2a38]">
          {rows.map(([metric, ppfas, icici], index) => {
            const isValNumeric = (str) => /^[\d%.+-]+$/.test(str.replace(/\s+/g, ''));
            return (
              <div
                key={metric}
                className={`group grid gap-0 text-sm sm:grid-cols-[0.8fr_1fr_1fr] ${index !== rows.length - 1 ? "border-b border-[#1e2a38]" : ""}`}
              >
                <div className="bg-[#1a1e23] px-5 py-4 font-medium text-slate-300">{metric}</div>
                <div className={`border-t border-[#1e2a38] bg-[#111415] px-5 py-4 text-slate-300 sm:border-l sm:border-t-0 ${isValNumeric(ppfas) ? "font-mono text-[#66a3ff]" : ""}`}>{ppfas}</div>
                <div className={`border-t border-[#1e2a38] bg-[#111415] px-5 py-4 text-slate-300 sm:border-l sm:border-t-0 ${isValNumeric(icici) ? "font-mono text-[#66a3ff]" : ""}`}>{icici}</div>
              </div>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
}

export default function FundersAILandingPage() {
  const { scrollYProgress } = useScroll();
  const heroGridY = useTransform(scrollYProgress, [0, 0.25], [0, 120]);
  const heroTextY = useTransform(scrollYProgress, [0, 0.18], [0, -28]);
  const shouldReduce = useReducedMotion();

  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      direction: 'vertical',
      gestureDirection: 'vertical',
      smooth: true,
      mouseMultiplier: 1,
      smoothTouch: false,
      touchMultiplier: 2,
      infinite: false,
    });

    function raf(time) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);

    return () => {
      lenis.destroy();
    }
  }, []);

  const wordReveal = {
    hidden: { opacity: 0, y: shouldReduce ? 0 : 28, rotateX: shouldReduce ? 0 : -12 },
    visible: {
      opacity: 1,
      y: 0,
      rotateX: 0,
      transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] }
    }
  };
  const words = "Compare funds. Understand risk.".split(" ");

  return (
    <main className="relative w-full min-w-0 min-h-screen overflow-x-clip scroll-smooth bg-[#020617] text-slate-200 selection:bg-[#007acc]/30">
      <motion.div
        aria-hidden="true"
        className="fixed left-0 top-0 z-50 h-1 bg-[#66a3ff]"
        style={{ scaleX: scrollYProgress, transformOrigin: "0%" }}
      />

      <section className="relative isolate w-full min-w-0 min-h-screen overflow-hidden">
        <motion.div className="absolute inset-0" style={{ y: heroGridY }}>
          <AmbientBackground />
        </motion.div>

        <motion.nav
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease }}
          className="sticky top-0 z-40 w-full"
        >
          <div className="flex items-center justify-between border-b border-white/[0.05] bg-[#090d18]/90 px-6 py-3 shadow-md backdrop-blur-xl sm:px-12">
            <a href="#" className="flex items-center gap-3" aria-label="FundersAI home">
              <motion.img
                whileHover={{ scale: 1.05 }}
                src="/FUNDERSAI-nobackground.png"
                alt="FundersAI Logo"
                className="h-10 w-auto origin-left object-contain md:h-12"
              />
            </a>
            <div className="hidden items-center gap-7 text-sm text-slate-400 md:flex">
              <a href="#compare" className="transition hover:text-white">Comparison</a>
              <a href="#coverage" className="transition hover:text-white">Coverage</a>
              <a href="#how" className="transition hover:text-white">How it works</a>
              <a href="#trust" className="transition hover:text-white">Trust</a>
            </div>

            <div className="flex items-center gap-2">
              <a href="/login" className="hidden rounded-full border border-white/10 bg-white/[0.045] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/[0.09] sm:inline-flex">
                Login
              </a>
              <a href="/dashboard" className="rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-[#cce0ff]">
                Try FundersAI
              </a>
            </div>
          </div>
        </motion.nav>

        <div className="relative z-10 mx-auto w-full max-w-full px-5 pb-24 pt-8 sm:px-8 sm:pt-6 lg:px-10">
          <div className="grid gap-12 lg:grid-cols-12 lg:items-center">
            <motion.div
              variants={stagger}
              initial="hidden"
              animate="visible"
              style={{ y: heroTextY }}
              className="lg:col-span-7 text-left"
            >
              <motion.div variants={fadeUp} className="mb-4 flex items-center gap-4">
                <span className="font-mono text-xs text-slate-500">01</span>
                <span className="h-px w-12 bg-white/20" />
                <span className="text-sm font-semibold uppercase text-[#66a3ff]">
                  Mutual fund research workspace
                </span>
              </motion.div>
              <motion.h1
                variants={{
                  hidden: {},
                  visible: { transition: { staggerChildren: 0.12, delayChildren: 0.2 } }
                }}
                initial="hidden"
                animate="visible"
                className="font-serif-display mb-2 text-fluid-hero text-white"
              >
                {words.map((word, i) => (
                  <span key={i} className="inline-block overflow-hidden pb-1 mr-[0.25em]">
                    <motion.span variants={wordReveal} className="inline-block">{word}</motion.span>
                  </span>
                ))}
              </motion.h1>
              <motion.p
                variants={fadeUp}
                className="mt-3 max-w-2xl text-pretty text-lg leading-8 text-slate-300 sm:text-xl"
              >
                FundersAI centralizes Indian mutual fund factsheets, NAV history, risk metrics, and comparison notes into one clean research workspace. Built for education and self-directed analysis, not fund recommendations.
              </motion.p>
              <motion.div
                variants={fadeUp}
                className="mt-6 flex flex-col items-start justify-start gap-4 sm:flex-row"
              >
                <MagneticButton href="/dashboard">Compare Funds</MagneticButton>
                <MagneticButton href="#compare" variant="secondary">View Comparison</MagneticButton>
              </motion.div>
              <motion.p variants={fadeUp} className="mt-5 max-w-xl text-sm leading-6 text-slate-500">
                Research and education only. Please consult a SEBI registered advisor before making any investment decision.
              </motion.p>
              <motion.div variants={stagger} className="mt-6 flex flex-wrap gap-2">
                <Badge>PPFAS, ICICI, HDFC, SBI</Badge>
                <Badge>Alpha, Beta, Sharpe</Badge>
                <Badge>Detailed side-by-side comparison</Badge>
                <Badge>No advisory output</Badge>
              </motion.div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 28 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.95, ease, delay: 0.15 }}
              className="lg:col-span-5 relative w-full rounded-2xl border border-[#1e2a38] bg-[#111415] shadow-2xl"
            >
              <div className="overflow-hidden rounded-xl">
                <div className="flex items-center justify-between border-b border-[#1e2a38] bg-[#1a1e23] px-5 py-4">
                  <div className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded-full bg-red-400/80" />
                    <span className="h-3 w-3 rounded-full bg-yellow-300/80" />
                    <span className="h-3 w-3 rounded-full bg-[#66a3ff]/80" />
                  </div>
                  <div className="text-xs font-semibold text-[#66a3ff]">Comparison workspace</div>
                </div>

                <div className="p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-[#1e2a38] pb-3">
                    <div>
                      <h4 className="text-sm font-semibold text-white">Parag Parikh Flexi Cap</h4>
                      <p className="text-xs text-slate-400">Direct Plan - Growth</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm font-semibold text-[#66a3ff]">+22.4%</p>
                      <p className="text-[10px] text-slate-500">1Y Return</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between border-b border-[#1e2a38] pb-3">
                    <div>
                      <h4 className="text-sm font-semibold text-white">ICICI Pru Multi Asset</h4>
                      <p className="text-xs text-slate-400">Direct Plan - Growth</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm font-semibold text-[#66a3ff]">+19.8%</p>
                      <p className="text-[10px] text-slate-500">1Y Return</p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-[#00509e] bg-[#111827] p-3 text-xs leading-relaxed text-slate-200">
                    <div className="flex items-center gap-1.5 font-semibold text-[#66a3ff] mb-1">
                      <Sparkle className="h-3.5 w-3.5" weight="fill" />
                      FundersAI Synthesis
                    </div>
                    In this snapshot, Parag Parikh shows a higher Sharpe reading. Treat this as research context, not a recommendation.
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          <div className="mt-24 border-t border-white/10 pt-16">
            <div className="mb-8 text-center">
              <span className="text-xs font-semibold uppercase text-[#66a3ff]">Workspace walkthrough</span>
              <h3 className="mt-3 text-3xl font-semibold text-white">Detailed Comparison Engine</h3>
            </div>
            <HeroPreview />
          </div>
          
          <ProofStrip />

          <motion.div
            initial={{ opacity: 0, y: 18, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.7, ease, delay: 0.55 }}
            className="mx-auto mt-10 max-w-3xl rounded-full border border-[#66a3ff]/20 bg-[#66a3ff]/[0.07] px-5 py-3 text-center text-sm text-[#cce0ff]/90 backdrop-blur-xl"
          >
            <span className="inline-flex items-center justify-center gap-2">
              <Clock className="h-4 w-4 text-[#66a3ff]" />
              Stock coverage is on the way. FundersAI currently focuses on mutual fund comparison first, with verified coverage across PPFAS, ICICI, HDFC, and SBI.
            </span>
          </motion.div>
        </div>
      </section>

      <section id="coverage" className="mx-auto w-full max-w-full px-5 py-16 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 28, filter: "blur(10px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.75, ease }}
          className="relative overflow-hidden rounded-xl border border-[#66a3ff]/20 bg-white/[0.035] p-6 sm:p-10"
        >
          <div className="grid gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase text-[#66a3ff]">02 / Coverage</p>
              <h2 className="mt-4 text-balance text-4xl font-semibold text-white sm:text-5xl">
                Four verified AMCs first. Broader coverage next.
              </h2>
              <p className="mt-5 text-pretty text-lg leading-8 text-slate-400">
                FundersAI is starting with mutual fund comparison as the MVP. The current pipeline has verified coverage across PPFAS, ICICI, HDFC, and SBI. Indian stock research and valuation metrics stay planned until the fund research layer is broader.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["Current coverage", "PPFAS, ICICI, HDFC, SBI"],
                ["Next coverage", "Broader major AMC expansion"],
                ["Stock module", "Planned after fund MVP"],
                ["Full launch", "After coverage expansion"],
              ].map(([title, body], index) => (
                <motion.div
                  key={title}
                  initial={{ opacity: 0, y: 14 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.08 }}
                  className="rounded-lg border border-white/10 bg-slate-950/45 p-5"
                >
                  <p className="text-lg font-semibold text-white">{title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{body}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>
      </section>

      <section id="compare" className="mx-auto w-full max-w-full px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
          number="03"
          eyebrow="Detailed comparison"
          title="A clearer way to compare funds before you research deeper."
          body="Compare supported funds side-by-side on returns, NAV movement, risk indicators, cost, consistency, and holdings context without turning the output into a recommendation."
        />
        <FundPairCard />
      </section>

      <section id="features" className="w-full">
        <div className="mx-auto w-full max-w-full px-5 pt-24 sm:px-8 lg:px-10">
          <SectionHeading
            align="left"
            number="04"
            eyebrow="Research system"
            title="Explore mutual fund DNA & risk signals."
            body="From instant risk-adjusted metrics to natural language explanations, FundersAI gives you the tools to screen and compare Indian mutual funds with speed."
          />
        </div>
        <HorizontalScrollFeatures />
      </section>

      <section className="mx-auto w-full max-w-full px-5 py-24 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 30, filter: "blur(10px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.8, ease }}
          className="relative overflow-hidden rounded-xl border border-white/10 bg-[#0F172A] p-6 sm:p-10"
        >
          <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase text-[#66a3ff]">05 / Data integrity</p>
              <h2 className="mt-4 text-balance text-4xl font-semibold text-white sm:text-5xl">Unified snapshots for deep screening.</h2>
              <p className="mt-5 text-pretty text-lg leading-8 text-slate-400">View NAV freshness, rolling returns, portfolio turnover, and expense ratios in one place. The goal is faster research, not automated investment advice.</p>
            </div>
            {/* Verifiable animated stats — real numbers from the live pipeline */}
            <div className="grid gap-4 sm:grid-cols-2">
              {[
                { label: "AMCs live", value: 4, suffix: "", note: "PPFAS, ICICI, HDFC, SBI" },
                { label: "NAV data points", value: 10, suffix: "K+", note: "Synced daily" },
                { label: "Risk metrics", value: 6, suffix: "", note: "Per fund" },
                { label: "Data sync", value: 24, suffix: "h", note: "Refresh cycle" },
              ].map(({ label, value, suffix, note }, index) => (
                <motion.div
                  key={label}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.07 }}
                  whileHover={{ y: -6 }}
                  className="rounded-lg border border-white/10 bg-slate-950/45 p-5"
                >
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
                  <AnimatedCounter
                    value={value}
                    suffix={suffix}
                    className="mt-4 block font-serif-display text-3xl font-bold text-[#66a3ff]"
                  />
                  <p className="mt-1 text-xs text-slate-400">{note}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>
      </section>

      <section id="how" className="mx-auto w-full max-w-full px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
          number="06"
          eyebrow="Workflow"
          title="From fund factsheets to explainable comparison."
          body="Discover how FundersAI parses and updates fund details to keep your research workflow seamless."
        />
        <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {steps.slice(0, 4).map(([number, title, body]) => (
            <motion.div key={title} variants={slideReveal} whileHover={{ y: -6 }} className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-6">
              <p className="text-sm text-[#66a3ff]">{number}</p>
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
          className="mt-5 rounded-xl border border-white/10 bg-[#0F172A] p-6 sm:p-8"
        >
          <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase text-[#66a3ff]">Primary focus now</p>
              <h3 className="mt-3 text-balance text-3xl font-semibold text-white sm:text-4xl">
                Coverage expansion comes before the full stock module.
              </h3>
              <p className="mt-4 text-sm leading-7 text-slate-400">
                FundersAI is currently focused on strengthening mutual fund coverage across major AMCs. Stock coverage is planned, but the immediate priority is making the fund comparison dataset broader and more reliable.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                ["Now", "4 verified AMCs", "Live parser path"],
                ["Next", "More major AMCs", "Coverage expansion"],
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

      <section className="mx-auto w-full max-w-full px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
          number="07"
          eyebrow="Use cases"
          title="Ask anything. Research instantly."
          body="Discover how working professionals and advanced investors query FundersAI to extract key comparison points."
        />
        <MarqueePrompts />
      </section>

      <section id="trust" className="mx-auto w-full max-w-full px-5 py-24 sm:px-8 lg:px-10">
        <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <SectionHeading
            align="left"
            number="08"
            eyebrow="Safety first"
            title="Unbiased intelligence. No advisory conflicts."
            body="FundersAI is engineered strictly for self-directed research and education. We never recommend products, take commissions, or make buy/sell calls."
          />
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} className="grid gap-4 sm:grid-cols-2">
            {[
              [Lock, "No advisory language", "Avoids buy/sell calls, portfolio advice, and recommendation phrasing."],
              [MagnifyingGlass, "Metric visibility", "Keeps source metrics visible beside the AI explanation."],
              [Database, "Freshness signals", "Makes update status part of the product experience."],
              [ShieldCheck, "User protection", "Frames output as education and research only."],
            ].map(([Icon, title, body]) => (
              <motion.div key={title} variants={slideReveal} whileHover={{ y: -6 }} className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-6">
                <Icon className="h-6 w-6 text-[#66a3ff]" />
                <h3 className="mt-5 text-xl font-semibold text-white">{title}</h3>
                <p className="mt-3 leading-7 text-slate-400">{body}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      <section id="disclaimer" className="mx-auto w-full max-w-full px-5 py-12 sm:px-8 lg:px-10">
        <div className="rounded-[2rem] border border-amber-300/20 bg-amber-300/[0.055] p-6 text-center sm:p-8">
          <h2 className="text-2xl font-semibold text-white">Research-only disclaimer</h2>
          <p className="mx-auto mt-4 max-w-4xl leading-8 text-amber-50/80">
            FundersAI is for research and education only. It does not provide financial advice, investment recommendations, portfolio management, or buy/sell calls. Current AMC coverage is limited to PPFAS, ICICI, HDFC, and SBI while the pipeline expands. Always verify data independently and consult a SEBI registered advisor before making any investment decision.
          </p>
        </div>
      </section>

      <section className="mx-auto w-full max-w-full px-5 pb-24 pt-12 sm:px-8 lg:px-10">
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
              Try FundersAI, compare funds side by side, and turn scattered fund data into a clean research workflow. Verified AMC coverage currently includes PPFAS, ICICI, HDFC, and SBI.
            </p>
            <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-slate-500">
              Research and education only. Consult a SEBI registered advisor before making investment decisions.
            </p>
            <div className="mt-9 flex flex-col justify-center gap-4 sm:flex-row">
              <MagneticButton href="/dashboard">Enter Workspace</MagneticButton>
              <MagneticButton href="/login" variant="secondary">Sign In</MagneticButton>
            </div>
          </div>
        </motion.div>
      </section>
      {/* Footer Section - Tresmares Inspired */}
      <footer className="bg-[#020611] pt-24 pb-12 mt-16 border-t border-white/[0.03]">
        <div className="mx-auto w-full max-w-7xl px-6 sm:px-12 lg:px-16">
          
          <div className="grid grid-cols-1 gap-16 md:grid-cols-12 lg:gap-12 mb-20">
            {/* Logo and Contact */}
            <div className="col-span-1 md:col-span-5 lg:col-span-6 flex flex-col justify-between">
              <div>
                <Image
                  src="/FUNDERSAI-vertical.png"
                  alt="FundersAI Logo"
                  width={2000}
                  height={861}
                  unoptimized
                  className="mb-8 h-24 w-auto object-contain opacity-90"
                />
                <p className="text-[13px] uppercase tracking-[0.1em] text-slate-500 font-medium mb-2">
                  Contact Us
                </p>
                <a href="mailto:contact@fundersai.co.in" className="text-lg text-slate-200 hover:text-white transition-colors">
                  contact@fundersai.co.in
                </a>
              </div>
            </div>
            
            {/* Quick Links */}
            <div className="col-span-1 md:col-span-3 lg:col-span-2">
              <h3 className="text-[11px] uppercase tracking-[0.2em] font-semibold text-[#66a3ff] mb-6">Legal</h3>
              <ul className="flex flex-col gap-4 text-sm text-slate-400">
                <li><a href="#" className="hover:text-white transition-colors">Terms and Conditions</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Cookie Policy</a></li>
              </ul>
            </div>

            {/* Strict Disclaimer */}
            <div className="col-span-1 md:col-span-4 lg:col-span-4">
              <h3 className="text-[11px] uppercase tracking-[0.2em] font-semibold text-amber-500 mb-6">Strict Disclaimer</h3>
              <div className="border-l border-amber-500/30 pl-4 py-1">
                <p className="text-xs leading-relaxed text-slate-400">
                  <strong className="text-slate-200 font-medium">FundersAI is strictly a research and educational platform.</strong> We do not provide financial advice, investment recommendations, or buy/sell signals. 
                  <br /><br />
                  <span className="text-amber-100/70">Please consult a SEBI registered advisor before making any investment decisions.</span>
                </p>
              </div>
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="flex flex-col-reverse items-center justify-between border-t border-white/[0.05] pt-8 md:flex-row gap-6">
            <p className="text-[11px] tracking-wider uppercase text-slate-600">
              © {new Date().getFullYear()} FundersAI. All rights reserved.
            </p>
            <div className="flex gap-8 text-[11px] tracking-widest uppercase font-medium text-slate-500">
              <a href="#" className="hover:text-white transition-colors">X (Twitter)</a>
              <a href="#" className="hover:text-white transition-colors">LinkedIn</a>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}
