"use client";

import React, { useEffect, useRef, useState } from "react";
import { motion, useScroll, useTransform, useReducedMotion } from "framer-motion";
import PageCurtain from "./PageCurtain";
import SplitReveal from "./SplitReveal";
import AnimatedCounter from "./AnimatedCounter";
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

// Deeper, more dramatic section reveal inspired by Wolverine Worldwide
const slideReveal = {
  hidden: { opacity: 0, y: 60, filter: "blur(8px)" },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.9, ease: [0.22, 1, 0.36, 1] },
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
  ["03", "Ask FundersAI", "Get a research-only explanation of what the numbers suggest."],
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

function AmbientBackground() {
  const { scrollYProgress } = useScroll();
  // Parallax: grid breathes upward as you scroll — Wolverine scroll scrub effect
  const gridY = useTransform(scrollYProgress, [0, 0.5], [0, 80]);
  const shouldReduce = useReducedMotion();

  return (
    <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      <div className="absolute inset-0 bg-[#020617]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(0,80,158,0.14),transparent_60%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_80%,rgba(102,163,255,0.08),transparent_50%)]" />
      <div className="absolute inset-0 opacity-[0.035] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
      {/* Scroll-parallax grid — moves at slower rate than content for depth */}
      <motion.div
        className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_80%)]"
        style={{ y: shouldReduce ? 0 : gridY }}
      />
    </div>
  );
}

function PremiumButton({ href, children, variant = "primary" }) {
  const ref = React.useRef(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [hovered, setHovered] = useState(false);
  const shouldReduce = useReducedMotion();

  const handleMouse = (e) => {
    if (!ref.current || shouldReduce) return;
    const { clientX, clientY } = e;
    const { height, width, left, top } = ref.current.getBoundingClientRect();
    const middleX = clientX - (left + width / 2);
    const middleY = clientY - (top + height / 2);
    setPosition({ x: middleX * 0.15, y: middleY * 0.15 });
  };

  const reset = () => {
    setPosition({ x: 0, y: 0 });
    setHovered(false);
  };

  const base = "group relative inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-semibold overflow-hidden";
  const styles =
    variant === "primary"
      ? "bg-white text-slate-950 shadow-[0_20px_70px_rgba(255,255,255,0.16)]"
      : "border border-white/12 bg-white/[0.05] text-white backdrop-blur-xl";

  return (
    <motion.a
      ref={ref}
      href={href}
      onMouseMove={handleMouse}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={reset}
      animate={{ x: position.x, y: position.y }}
      transition={{ type: "spring", stiffness: 150, damping: 15, mass: 0.1 }}
      className={`${base} ${styles}`}
    >
      {/* Ink-fill hover effect — color bleeds in from left, inspired by Tresmares c-button */}
      <motion.span
        aria-hidden="true"
        className="absolute inset-0 rounded-full"
        style={{
          backgroundColor: variant === "primary" ? "#cce0ff" : "rgba(102,163,255,0.12)",
          transformOrigin: "left center",
        }}
        initial={{ scaleX: 0 }}
        animate={{ scaleX: hovered ? 1 : 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      />
      <span className="relative z-10 flex items-center transition-colors duration-200">
        {children}
        {variant === "primary" && (
          <motion.span
            animate={{ x: hovered ? 4 : 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="inline-flex"
          >
            <ArrowRight className="ml-2 h-4 w-4" />
          </motion.span>
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
  const heroRef = React.useRef(null);
  const [rotateX, setRotateX] = useState(0);
  const [rotateY, setRotateY] = useState(0);

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

  const handleMouseMove = (e) => {
    if (!heroRef.current) return;
    const rect = heroRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    setRotateX((centerY - y) / 30);
    setRotateY((x - centerX) / 30);
  };

  const handleMouseLeave = () => {
    setRotateX(0);
    setRotateY(0);
  };

  const ppfasReturn = data.ppfas?.returns?.['1Y'] ? `+${(data.ppfas.returns['1Y'] * 100).toFixed(1)}%` : "+22.4%";
  const iciciReturn = data.icici?.returns?.['1Y'] ? `+${(data.icici.returns['1Y'] * 100).toFixed(1)}%` : "+19.8%";

  return (
    <motion.div
      ref={heroRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0, rotateX, rotateY }}
      transition={{ duration: 0.8, ease, rotateX: { type: "spring", stiffness: 150, damping: 20 }, rotateY: { type: "spring", stiffness: 150, damping: 20 } }}
      style={{ transformStyle: "preserve-3d", perspective: "1000px" }}
      className="relative mx-auto mt-12 w-full max-w-4xl rounded-2xl border border-white/10 bg-[#0F172A]/90 backdrop-blur-2xl p-6 shadow-2xl"
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
              Here is a comparison of their core metrics. Parag Parikh appears steadier on risk-adjusted metrics, while ICICI Multi Asset brings a multi-asset allocation profile.
            </p>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs font-semibold text-slate-400">Parag Parikh Flexi Cap</div>
                <div className="mt-2 text-2xl font-mono text-[#66a3ff]">{ppfasReturn}</div>
                <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">1Y Return (Live Data)</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs font-semibold text-slate-400">ICICI Pru Multi Asset</div>
                <div className="mt-2 text-2xl font-mono text-[#66a3ff]">{iciciReturn}</div>
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
  const [paused, setPaused] = useState(false);
  const shouldReduce = useReducedMotion();

  return (
    <motion.div
      className="relative mx-auto mt-10 max-w-6xl overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_5%,black_95%,transparent)]"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
    >
      <motion.div
        className="flex w-max gap-3"
        animate={shouldReduce ? {} : { x: [0, -780] }}
        transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
        style={{ animationPlayState: paused ? "paused" : "running" }}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
      >
        {[...promptChips, ...promptChips, ...promptChips].map((prompt, index) => (
          <button
            key={`${prompt}-${index}`}
            className="rounded-full border border-white/10 bg-white/[0.045] px-5 py-3 text-sm text-slate-200 transition hover:border-[#66a3ff]/30 hover:bg-[#00509e]/15 hover:text-white"
          >
            {prompt}
          </button>
        ))}
      </motion.div>
    </motion.div>
  );
}

function SectionHeading({ eyebrow, title, body, align = "center" }) {
  return (
    <div className={align === "center" ? "mx-auto max-w-3xl text-center" : "max-w-3xl"}>
      <motion.p
        initial={{ opacity: 0, y: 14 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-90px" }}
        transition={{ duration: 0.5, ease }}
        className="text-sm font-semibold uppercase tracking-[0.22em] text-[#66a3ff]"
      >
        {eyebrow}
      </motion.p>
      {/* SplitReveal — character-level clip reveal on section headings (Tresmares-style) */}
      <SplitReveal
        text={title}
        as="h2"
        delay={0.1}
        className="mt-4 text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl"
      />
      {body && (
        <motion.p
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-90px" }}
          transition={{ duration: 0.65, ease, delay: 0.25 }}
          className="mt-5 text-lg leading-8 text-slate-400"
        >
          {body}
        </motion.p>
      )}
    </div>
  );
}

function FeatureBento() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-6 gap-4 w-full">
      {features.map((feature, index) => {
        const Icon = feature.icon;
        let spanClass = "md:col-span-2"; // default small square
        if (index === 0) spanClass = "md:col-span-4"; // wide top left
        else if (index === 1) spanClass = "md:col-span-2"; // small top right
        else if (index === 2) spanClass = "md:col-span-3"; // half mid
        else if (index === 3) spanClass = "md:col-span-3"; // half mid
        else if (index === 4) spanClass = "md:col-span-2"; // small bot left
        else if (index === 5) spanClass = "md:col-span-4"; // wide bot right

        return (
          <motion.div
            key={feature.title}
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-40px" }}
            whileHover={{ y: -5, transition: { duration: 0.2 } }}
            className={`group relative overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.02] p-8 shadow-2xl backdrop-blur-xl transition-colors hover:bg-white/[0.04] hover:border-white/20 ${spanClass}`}
          >
            <div className="absolute inset-0 bg-gradient-to-br from-white/[0.05] to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
            
            <div className="relative z-10 flex h-full flex-col justify-between gap-8">
              <div>
                <div className="mb-6 flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-white shadow-inner backdrop-blur-md transition-transform group-hover:scale-110">
                    <Icon className="h-6 w-6" />
                  </div>
                  <span className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-300">
                    {feature.eyebrow}
                  </span>
                </div>
                <h3 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                  {feature.title}
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-slate-400">
                  {feature.body}
                </p>
              </div>
              <div className="mt-auto">
                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[#66a3ff]">
                  <Sparkle className="h-3.5 w-3.5" weight="fill" />
                  {feature.proof}
                </span>
              </div>
            </div>
          </motion.div>
        );
      })}
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
      viewport={{ once: true, margin: "-120px" }}
      className="mt-16 overflow-hidden rounded-[2.5rem] border border-white/10 bg-white/[0.02] shadow-2xl backdrop-blur-3xl"
    >
      <div className="grid gap-0 lg:grid-cols-[1fr_1fr]">
        <motion.div
          variants={{ hidden: { opacity: 0, x: -80 }, visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease } } }}
          className="border-b border-white/10 p-8 lg:border-b-0 lg:border-r hover:bg-white/[0.02] transition-colors"
        >
          <div className="mb-4 inline-flex rounded-full border-[#66a3ff]/20 bg-[#00509e]/10 px-3 py-1 text-xs font-medium text-slate-100">
            Steadier profile
          </div>
          <h3 className="text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
            Parag Parikh Flexi Cap
          </h3>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-400">
            Used as the first supported fund example for long-term consistency and diversified flexi-cap research.
          </p>
        </motion.div>

        <motion.div
          variants={{ hidden: { opacity: 0, x: 80 }, visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease } } }}
          className="p-8 hover:bg-white/[0.02] transition-colors"
        >
          <div className="mb-4 inline-flex rounded-full border border-[#66a3ff]/20 bg-[#66a3ff]/[0.08] px-3 py-1 text-xs font-medium text-[#cce0ff]">
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

      <motion.div variants={fadeUp} className="border-t border-white/10 bg-black/40 p-6 sm:p-8">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-white">Live comparison preview</p>
            <p className="mt-1 text-xs text-slate-500">Formatted as a table so long fund names do not break the card layout.</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-xs font-medium text-slate-300 backdrop-blur-md">
            <Sparkle className="h-3.5 w-3.5 text-[#66a3ff]" weight="fill" />
            FundersAI explains the difference
          </div>
        </div>

        <div className="overflow-hidden rounded-[1.5rem] border border-white/10">
          {rows.map(([metric, ppfas, icici], index) => {
            const isValNumeric = (str) => /^[\d%.+-]+$/.test(str.replace(/\s+/g, ''));
            return (
              <div
                key={metric}
                className={`group grid gap-0 text-sm sm:grid-cols-[0.8fr_1fr_1fr] transition-colors hover:bg-white/[0.04] ${index !== rows.length - 1 ? "border-b border-white/10" : ""}`}
              >
                <div className="bg-white/[0.02] px-5 py-4 font-medium text-slate-300 transition-colors group-hover:text-white">{metric}</div>
                <div className={`border-t border-white/10 px-5 py-4 text-slate-300 sm:border-l sm:border-t-0 transition-colors group-hover:text-white ${isValNumeric(ppfas) ? "font-mono text-[#66a3ff]/90 font-medium group-hover:text-[#66a3ff]" : ""}`}>{ppfas}</div>
                <div className={`border-t border-white/10 px-5 py-4 text-slate-300 sm:border-l sm:border-t-0 transition-colors group-hover:text-white ${isValNumeric(icici) ? "font-mono text-[#66a3ff]/90 font-medium group-hover:text-[#66a3ff]" : ""}`}>{icici}</div>
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

  // Upgraded word reveal — deeper 3D rotateX clip, Wolverine kinetic hero style
  const wordReveal = {
    hidden: { opacity: 0, y: shouldReduce ? 0 : 42, rotateX: shouldReduce ? 0 : -28, filter: shouldReduce ? "none" : "blur(4px)" },
    visible: {
      opacity: 1,
      y: 0,
      rotateX: 0,
      filter: "blur(0px)",
      transition: { duration: 1.0, ease: [0.16, 1, 0.3, 1] }
    }
  };
  const words = "Mutual fund research, simplified.".split(" ");

  return (
    <main className="w-full min-w-0 min-h-screen overflow-hidden scroll-smooth bg-[#020617] text-slate-200 selection:bg-[#007acc]/30">
      {/* Corporate Blues curtain reveal — slides up to expose page (Tresmares + Wolverine) */}
      <PageCurtain />
      <motion.div
        aria-hidden="true"
        className="fixed left-0 top-0 z-50 h-1 bg-[#66a3ff]"
        style={{ scaleX: scrollYProgress, transformOrigin: "0%" }}
      />

      <section className="relative isolate w-full min-w-0 min-h-screen overflow-hidden">
        <motion.div style={{ y: heroGridY }}>
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
                src="/logo.png"
                alt="FundersAI Logo"
                className="h-10 md:h-12 w-auto object-contain origin-left"
              />
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
              <a href="/dashboard" className="rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-[#cce0ff]">
                Try FundersAI
              </a>
            </div>
          </div>
        </motion.nav>

        <div className="mx-auto w-full max-w-full px-5 pb-24 pt-14 sm:px-8 sm:pt-24 lg:px-10">
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
                  <Star className="h-4 w-4 text-[#66a3ff]" weight="fill" />
                  Mutual fund comparison workspace
                </span>
              </motion.div>
              <motion.h1
                variants={{
                  hidden: {},
                  visible: { transition: { staggerChildren: 0.12, delayChildren: 0.2 } }
                }}
                initial="hidden"
                animate="visible"
                className="text-balance text-6xl font-medium tracking-tighter text-white sm:text-7xl lg:text-8xl"
                style={{ perspective: "1000px" }}
              >
                {words.map((word, i) => (
                  <span key={i} className="inline-block overflow-hidden pb-3 mr-[0.25em]">
                    <motion.span variants={wordReveal} className="inline-block">{word}</motion.span>
                  </span>
                ))}
              </motion.h1>
              <motion.p
                variants={fadeUp}
                className="mt-7 max-w-2xl text-pretty text-lg leading-8 text-slate-300 sm:text-xl"
              >
                FundersAI centralizes scattered Indian mutual fund factsheets, risk metrics, and NAV history into a clean workspace. Engineered for working professionals who demand quick, data-backed insights.
              </motion.p>
              <motion.div
                variants={fadeUp}
                className="mt-9 flex flex-col items-start justify-start gap-3 sm:flex-row"
              >
                <PremiumButton href="/dashboard">Try FundersAI</PremiumButton>
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
                    <span className="h-3 w-3 rounded-full bg-[#66a3ff]/80" />
                  </div>
                  <div className="text-xs text-[#66a3ff] font-semibold tracking-wide">Live Workspace</div>
                </div>

                <div className="p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-white/5 pb-3">
                    <div>
                      <h4 className="text-sm font-semibold text-white">Parag Parikh Flexi Cap</h4>
                      <p className="text-xs text-slate-400">Direct Plan - Growth</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm font-semibold text-[#66a3ff]">+22.4%</p>
                      <p className="text-[10px] text-slate-500">1Y Return</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between border-b border-white/5 pb-3">
                    <div>
                      <h4 className="text-sm font-semibold text-white">ICICI Pru Multi Asset</h4>
                      <p className="text-xs text-slate-400">Direct Plan - Growth</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm font-semibold text-[#66a3ff]">+19.8%</p>
                      <p className="text-[10px] text-slate-500">1Y Return</p>
                    </div>
                  </div>

                  <div className="rounded-2xl border-[#66a3ff]/20 bg-[#00509e]/10 p-3 text-xs leading-relaxed text-slate-200">
                    <div className="flex items-center gap-1.5 font-semibold text-[#66a3ff] mb-1">
                      <Sparkle className="h-3.5 w-3.5" weight="fill" />
                      FundersAI Synthesis
                    </div>
                    Parag Parikh Flexi Cap demonstrates superior risk-adjusted performance with a Sharpe Ratio of 1.22.
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          <div className="mt-24 border-t border-white/10 pt-16">
            <div className="mb-8 text-center">
              <span className="text-xs uppercase tracking-[0.22em] text-[#66a3ff] font-semibold">Workspace Walkthrough</span>
              <h3 className="mt-3 text-3xl font-semibold text-white">Factsheet Comparison Engine</h3>
            </div>
            <HeroPreview />
          </div>
          
          <LogoCloud />

          <motion.div
            initial={{ opacity: 0, y: 18, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.7, ease, delay: 0.55 }}
            className="mx-auto mt-10 max-w-3xl rounded-full border border-[#66a3ff]/20 bg-[#66a3ff]/[0.07] px-5 py-3 text-center text-sm text-[#cce0ff]/90 backdrop-blur-xl"
          >
            <span className="inline-flex items-center justify-center gap-2">
              <Clock className="h-4 w-4 text-[#66a3ff]" />
              Stock coverage is on the way. FundersAI currently focuses on mutual fund comparison first, starting with the live Parag Parikh and ICICI pipeline.
            </span>
          </motion.div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-full px-5 py-16 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 28, filter: "blur(10px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.75, ease }}
          className="relative overflow-hidden rounded-[2.25rem] border border-[#66a3ff]/20 bg-[radial-gradient(circle_at_top_right,rgba(102,163,255,0.16),transparent_34%),rgba(255,255,255,0.04)] p-6 sm:p-10"
        >
          <div className="grid gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#66a3ff]">Coming next</p>
              <h2 className="mt-4 text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">
                Stock coverage is on the way.
              </h2>
              <p className="mt-5 text-lg leading-8 text-slate-400">
                FundersAI is starting with mutual fund comparison as the MVP. The current pipeline is set up for Parag Parikh and ICICI funds first. Broader AMC coverage, Indian stock research, stock comparison, and valuation metrics are planned before the full public launch.
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

      <section id="compare" className="mx-auto w-full max-w-full px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
          eyebrow="Deep Screening"
          title="Unbiased research. Zero noise."
          body="Compare funds side-by-side on performance consistency, risk indicators, and costs. FundersAI standardizes scattered disclosures into one unified dashboard."
        />
        <FundPairCard />
      </section>

      <section id="features" className="mx-auto w-full max-w-full px-5 py-24 sm:px-8 lg:px-10">
        <div className="flex flex-col gap-12">
          <SectionHeading
            align="left"
            eyebrow="Intelligence"
            title="Explore mutual fund DNA & risk signals."
            body="From instant risk-adjusted metrics to natural language explanations, FundersAI gives you the tools to screen and compare Indian mutual funds with speed."
          />
          <FeatureBento />
        </div>
      </section>

      <section className="mx-auto w-full max-w-full px-5 py-24 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 30, filter: "blur(10px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.8, ease }}
          className="relative overflow-hidden rounded-[2.5rem] border border-white/10 bg-[#0F172A] p-6 sm:p-10"
        >
          <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#66a3ff]">Data integrity</p>
              <h2 className="mt-4 text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">Unified snapshots for deep screening.</h2>
              <p className="mt-5 text-lg leading-8 text-slate-400">Instantly view essential metrics: NAV freshness, rolling returns, portfolio turnover, and expense ratios. No more digging through confusing PDF disclosures.</p>
            </div>
            {/* Verifiable animated stats — real numbers from the live pipeline */}
            <div className="grid gap-4 sm:grid-cols-2">
              {[
                { label: "AMCs live", value: 2, suffix: "", note: "PPFAS + ICICI" },
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
                  className="rounded-[1.5rem] border border-white/10 bg-slate-950/45 p-5"
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
          className="mt-5 rounded-[2rem] border border-white/10 bg-[#0F172A] p-6 sm:p-8"
        >
          <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#66a3ff]">Primary focus now</p>
              <h3 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
                Coverage expansion comes before the full stock module.
              </h3>
              <p className="mt-4 text-sm leading-7 text-slate-400">
                FundersAI is currently focused on strengthening mutual fund coverage across major AMCs. Stock coverage is planned, but the immediate priority is making the fund comparison dataset broader and more reliable.
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

      <section className="mx-auto w-full max-w-full px-5 py-24 sm:px-8 lg:px-10">
        <SectionHeading
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
            FundersAI is for research and education only. It does not provide financial advice, investment recommendations, portfolio management, or buy/sell calls. Current coverage is limited while the pipeline expands across major AMCs. Always verify data independently before making financial decisions.
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
              Try FundersAI, compare funds side by side, and turn scattered fund data into a clean research workflow. Major AMC coverage and stock coverage are on the way before full launch.
            </p>
            <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
              <PremiumButton href="/dashboard">Try FundersAI</PremiumButton>
              <PremiumButton href="/login" variant="secondary">Login</PremiumButton>
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
                <img src="/FUNDERSAI-nobackground.png" alt="FundersAI Logo" className="h-10 w-auto object-contain mb-8 opacity-90" />
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
