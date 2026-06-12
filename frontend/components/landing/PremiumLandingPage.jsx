"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  CheckCircle,
  Cpu,
  Database,
  Lock,
  MagnifyingGlass,
  ShieldCheck,
  TrendUp,
} from "@phosphor-icons/react";

const ease = [0.22, 1, 0.36, 1];
const displayStyle = { fontFamily: '"Space Grotesk", var(--font-body-md)' };

const proofRail = [
  ["Verified AMCs", "PPFAS, ICICI, HDFC, SBI"],
  ["Output boundary", "Research-only, no recommendations"],
  ["Data layer", "Stored records, freshness, limits"],
  ["Next focus", "Broader AMC coverage before stocks"],
];

const proofStats = [
  ["04", "validated AMC families", "Coverage is intentionally scoped to PPFAS, ICICI, HDFC, and SBI while expansion continues."],
  ["0", "advisory outputs", "The product avoids recommendations, buy/sell calls, and portfolio advice."],
  ["1", "research workspace", "Fund metrics, source freshness, and AI explanations stay visible together."],
];

const terminalFunds = [
  ["Parag Parikh Flexi Cap", "PPFAS", "+22.4%", "1Y return example"],
  ["ICICI Pru Multi Asset", "ICICI", "+19.8%", "1Y return example"],
];

const metricRows = [
  ["Sharpe ratio", "1.22", "1.08", "Risk-adjusted return"],
  ["Expense ratio", "0.63%", "1.05%", "Cost visibility"],
  ["NAV history", "Synced", "Synced", "Freshness check"],
  ["Source status", "Verified", "Verified", "Factsheet mapped"],
];

const productPanels = [
  ["Verified AMC coverage", "PPFAS, ICICI, HDFC, and SBI coverage is stated clearly while broader AMC expansion continues."],
  ["Source freshness", "NAV and factsheet status stay visible beside the metrics so stale data is easier to spot."],
  ["No advisory output", "The interface frames answers as research notes, not recommendations, suitability calls, or buy/sell guidance."],
];

const dataFlow = [
  ["Collect", "FundersAI starts from real fund and market records, not generated claims."],
  ["Store", "Raw files or payloads are retained for audit where needed."],
  ["Normalize", "Parsers convert messy documents into structured fields the app can read."],
  ["Validate", "Coverage, freshness, missing fields, and partial records are checked before display."],
  ["Compare", "Search, charts, detail views, and compare tables read normalized stored data."],
  ["Explain", "AI explains available data in plain English and shows limits beside the result."],
];

const workflow = [
  ["01", "Pick funds", "Select supported mutual funds from the comparison workspace."],
  ["02", "Compare", "Review normalized metrics, ratios, and NAV movement side by side."],
  ["03", "Ask", "Use FundersAI for a plain-English, research-only explanation."],
  ["04", "Verify", "Check source freshness and constraints before making independent decisions."],
];

const trustCards = [
  [Lock, "No advisory language", "No recommendations, buy/sell calls, portfolio advice, or suitability claims."],
  [MagnifyingGlass, "Transparent metrics", "AI notes sit beside the data table instead of replacing it."],
  [Database, "Source freshness", "NAV and factsheet status are part of the product surface."],
  [ShieldCheck, "Research boundary", "The site repeatedly states that FundersAI is for research and education only."],
];

const roadmap = [
  ["Now", "Verified four-AMC mutual fund comparison", "PPFAS, ICICI, HDFC, SBI"],
  ["Next", "Broader major-AMC coverage", "More factsheets, holdings, and metric mapping"],
  ["Later", "Stock research module", "Planned after the fund coverage layer is stronger"],
];

const promptChips = [
  "Compare Parag Parikh Flexi Cap vs ICICI Multi Asset",
  "Show expense ratio and risk signals",
  "Explain Sharpe and beta in simple terms",
  "Check NAV freshness for both funds",
  "Summarize source constraints",
  "Compare HDFC and SBI fund metrics",
];

function FineGrid() {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      aria-hidden="true"
      className="absolute inset-0 -z-10 bg-[linear-gradient(to_right,rgba(102,163,255,0.08)_1px,transparent_1px),linear-gradient(to_bottom,rgba(102,163,255,0.07)_1px,transparent_1px)] bg-[size:88px_88px] [mask-image:radial-gradient(ellipse_at_top,black_22%,transparent_74%)]"
      animate={reduceMotion ? undefined : { backgroundPosition: ["0px 0px", "88px 88px"], opacity: [0.42, 0.62, 0.42] }}
      transition={reduceMotion ? undefined : { backgroundPosition: { duration: 34, repeat: Infinity, ease: "linear" }, opacity: { duration: 8, repeat: Infinity, ease: "easeInOut" } }}
    />
  );
}

function Reveal({ children, className = "", delay = 0 }) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 22, filter: "blur(8px)" }}
      whileInView={reduceMotion ? undefined : { opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-70px" }}
      transition={{ duration: 0.65, ease, delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function PremiumButton({ href, children, variant = "primary" }) {
  const reduceMotion = useReducedMotion();
  const base = "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold transition";
  const styles =
    variant === "primary"
      ? "bg-[#66a3ff] text-[#020617] shadow-[0_18px_60px_rgba(102,163,255,0.22)] hover:bg-[#8bbcff]"
      : "border border-white/12 bg-white/[0.045] text-white hover:border-[#66a3ff]/45 hover:bg-white/[0.075]";

  return (
    <motion.a
      href={href}
      whileHover={reduceMotion ? undefined : { y: -3 }}
      whileTap={reduceMotion ? undefined : { scale: 0.98 }}
      className={`${base} ${styles}`}
    >
      {children}
      {variant === "primary" && <ArrowRight className="h-4 w-4" />}
    </motion.a>
  );
}

function SectionHeading({ number, eyebrow, title, body }) {
  return (
    <Reveal className="grid gap-6 border-t border-white/10 pt-8 lg:grid-cols-12 lg:gap-8">
      <div className="lg:col-span-3">
        <p className="font-mono text-sm font-semibold text-[#66a3ff]">{number}</p>
        <p className="mt-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">{eyebrow}</p>
      </div>
      <div className="lg:col-span-9">
        <h2 style={displayStyle} className="max-w-5xl text-4xl font-semibold leading-[1.02] tracking-normal text-white sm:text-5xl 2xl:text-6xl">
          {title}
        </h2>
        {body && <p className="mt-5 max-w-3xl text-base leading-7 text-slate-400 sm:text-lg">{body}</p>}
      </div>
    </Reveal>
  );
}

function DataChip({ children, tone = "blue" }) {
  const toneClass =
    tone === "green"
      ? "border-emerald-300/20 bg-emerald-300/[0.08] text-emerald-100"
      : tone === "amber"
        ? "border-amber-300/25 bg-amber-300/[0.08] text-amber-100"
        : "border-[#66a3ff]/25 bg-[#66a3ff]/10 text-[#cfe1ff]";

  return (
    <span className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em] ${toneClass}`}>
      {children}
    </span>
  );
}

function Panel({ children, className = "" }) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      whileHover={reduceMotion ? undefined : { y: -5, borderColor: "rgba(102,163,255,0.34)" }}
      transition={{ duration: 0.25, ease }}
      className={`rounded-2xl border border-white/10 bg-white/[0.045] shadow-[0_24px_90px_rgba(0,0,0,0.18)] ${className}`}
    >
      {children}
    </motion.div>
  );
}

function HeroTerminal() {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 18, rotateX: 4 }}
      animate={reduceMotion ? undefined : { opacity: 1, y: [0, -8, 0], rotateX: 0 }}
      transition={reduceMotion ? undefined : { opacity: { duration: 0.7, ease }, y: { duration: 7, repeat: Infinity, ease: "easeInOut" }, rotateX: { duration: 0.7, ease } }}
      className="relative rounded-[18px] border border-white/12 bg-[#07111f]/92 p-2 shadow-[0_34px_120px_rgba(0,0,0,0.42)] backdrop-blur-2xl"
    >
      <div className="absolute inset-x-12 -top-px h-px bg-gradient-to-r from-transparent via-[#66a3ff] to-transparent" />
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#07111f]">
        <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.035] px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-300/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-300/80" />
          </div>
          <DataChip tone="green">Workspace online</DataChip>
        </div>

        <div className="grid gap-0 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="border-b border-white/10 p-5 sm:p-6 xl:border-b-0 xl:border-r">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Comparison query</p>
            <h3 style={displayStyle} className="mt-4 text-2xl font-semibold leading-tight text-white">
              Which fund has stronger risk-adjusted metrics?
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              FundersAI compares supported funds, explains the signals, and keeps source constraints visible.
            </p>

            <div className="mt-6 space-y-3">
              {terminalFunds.map(([fund, amc, value, label]) => (
                <div key={fund} className="rounded-xl border border-white/10 bg-slate-950/45 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-white">{fund}</p>
                      <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.14em] text-slate-500">{amc}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-lg font-semibold text-emerald-300">{value}</p>
                      <p className="mt-1 text-[11px] text-slate-500">{label}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="p-5 sm:p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <DataChip>Source mapped</DataChip>
              <DataChip tone="amber">Research-only</DataChip>
            </div>
            <div className="overflow-hidden rounded-xl border border-white/10">
              {metricRows.map(([metric, a, b, note], index) => (
                <div key={metric} className={`grid grid-cols-[1.1fr_0.7fr_0.7fr] gap-3 px-4 py-3 text-sm ${index !== metricRows.length - 1 ? "border-b border-white/8" : ""}`}>
                  <div>
                    <p className="font-medium text-slate-200">{metric}</p>
                    <p className="mt-1 text-xs text-slate-500">{note}</p>
                  </div>
                  <p className="self-center text-right font-mono font-semibold text-white">{a}</p>
                  <p className="self-center text-right font-mono font-semibold text-slate-300">{b}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-xl border border-[#66a3ff]/20 bg-[#66a3ff]/10 p-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[#d7e7ff]">
                <Cpu className="h-4 w-4 text-[#66a3ff]" />
                FundersAI explanation
              </div>
              <p className="text-sm leading-6 text-slate-300">
                PPFAS appears stronger on this sample risk-adjusted view. This is a research note, not a recommendation.
              </p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function ProofRail() {
  return (
    <Reveal className="mt-8 grid gap-3 border-y border-white/10 py-4 sm:grid-cols-2 xl:grid-cols-4">
      {proofRail.map(([label, value]) => (
        <div key={label} className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
          <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</p>
          <p className="mt-2 text-sm font-semibold text-slate-100">{value}</p>
        </div>
      ))}
    </Reveal>
  );
}

function ProductTerminal() {
  return (
    <div className="mt-8 grid gap-6 lg:grid-cols-12">
      <Panel className="p-6 lg:col-span-7">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-white">Comparison terminal</p>
            <p className="mt-1 text-xs text-slate-500">Example view for supported mutual funds.</p>
          </div>
          <DataChip>Fund comparison</DataChip>
        </div>
        <div className="overflow-hidden rounded-xl border border-white/10">
          <div className="grid grid-cols-[1.1fr_0.8fr_0.8fr] bg-white/[0.04] px-4 py-3 font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
            <span>Metric</span>
            <span className="text-right">PPFAS</span>
            <span className="text-right">ICICI</span>
          </div>
          {metricRows.map(([metric, a, b]) => (
            <div key={metric} className="grid grid-cols-[1.1fr_0.8fr_0.8fr] border-t border-white/8 px-4 py-4 text-sm">
              <span className="font-medium text-slate-300">{metric}</span>
              <span className="text-right font-mono text-white">{a}</span>
              <span className="text-right font-mono text-slate-300">{b}</span>
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid gap-4 lg:col-span-5">
        {productPanels.map(([title, body], index) => (
          <Reveal key={title} delay={index * 0.06}>
            <Panel className="p-6">
              <p style={displayStyle} className="text-xl font-semibold text-white">{title}</p>
              <p className="mt-3 text-sm leading-6 text-slate-400">{body}</p>
            </Panel>
          </Reveal>
        ))}
      </div>
    </div>
  );
}

function PromptMarquee() {
  const reduceMotion = useReducedMotion();

  return (
    <div className="mt-8 overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
      <motion.div
        className="flex w-max gap-3 hover:[animation-play-state:paused]"
        animate={reduceMotion ? undefined : { x: [0, -760] }}
        transition={reduceMotion ? undefined : { duration: 34, repeat: Infinity, ease: "linear" }}
      >
        {[...promptChips, ...promptChips, ...promptChips].map((prompt, index) => (
          <span
            key={`${prompt}-${index}`}
            className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300"
          >
            {prompt}
          </span>
        ))}
      </motion.div>
    </div>
  );
}

export default function FundersAILandingPage() {
  return (
    <main className="relative min-h-screen overflow-x-hidden bg-[#020617] text-slate-200" style={{ fontFamily: "var(--font-body-md)" }}>
      <FineGrid />
      <div aria-hidden="true" className="absolute left-1/2 top-0 -z-10 h-[560px] w-[92vw] -translate-x-1/2 bg-[radial-gradient(circle,rgba(102,163,255,0.16),transparent_62%)] blur-3xl" />

      <header className="mx-auto w-full max-w-[1720px] px-5 pt-6 sm:px-10 2xl:px-16">
        <nav className="flex items-center justify-between rounded-2xl border border-white/10 bg-[#07111f]/78 px-4 py-3 shadow-[0_18px_70px_rgba(0,0,0,0.28)] backdrop-blur-xl">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-[#020617]">
              <TrendUp className="h-5 w-5" weight="bold" />
            </div>
            <span style={displayStyle} className="text-lg font-semibold text-white">FundersAI</span>
          </Link>
          <div className="hidden items-center gap-8 text-sm font-semibold text-slate-400 lg:flex">
            <a href="#proof" className="transition hover:text-white">Proof</a>
            <a href="#data-flow" className="transition hover:text-white">Data flow</a>
            <a href="#product" className="transition hover:text-white">Product</a>
            <a href="#workflow" className="transition hover:text-white">Workflow</a>
            <a href="#trust" className="transition hover:text-white">Trust</a>
            <a href="#roadmap" className="transition hover:text-white">Roadmap</a>
          </div>
          <div className="flex items-center gap-2">
            <a href="/login" className="rounded-xl border border-white/10 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-white/20 hover:bg-white/[0.05]">
              Login
            </a>
            <a href="/dashboard" className="hidden rounded-xl bg-white px-4 py-2 text-sm font-semibold text-[#020617] transition hover:bg-[#dce9ff] sm:inline-flex">
              Open workspace
            </a>
          </div>
        </nav>
      </header>

      <section className="mx-auto w-full max-w-[1720px] px-5 pb-12 pt-12 sm:px-10 sm:pb-16 sm:pt-16 2xl:px-16 2xl:pt-20">
        <div className="grid items-center gap-12 xl:grid-cols-12 2xl:gap-16">
          <Reveal className="xl:col-span-6">
            <DataChip tone="blue">
              <CheckCircle className="h-3.5 w-3.5" weight="fill" />
              AI mutual fund research workspace
            </DataChip>
            <h1 style={displayStyle} className="mt-6 max-w-6xl text-5xl font-semibold leading-[0.96] tracking-normal text-white sm:text-7xl xl:text-7xl 2xl:text-[6.4rem]">
              AI-orchestrated mutual fund research.
            </h1>
            <p className="mt-6 max-w-3xl text-lg leading-8 text-slate-400 sm:text-xl">
              Compare fund metrics, source freshness, and risk signals in one research workspace. Built for professionals who need clean evidence, not advisory language.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <PremiumButton href="/dashboard">Open research workspace</PremiumButton>
              <PremiumButton href="/login" variant="secondary">Login</PremiumButton>
            </div>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              Research-only. No recommendations. Verified AMC coverage is shown clearly.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <DataChip tone="green">PPFAS</DataChip>
              <DataChip tone="green">ICICI</DataChip>
              <DataChip tone="green">HDFC</DataChip>
              <DataChip tone="green">SBI</DataChip>
              <DataChip tone="amber">No recommendations</DataChip>
            </div>
          </Reveal>

          <div className="xl:col-span-6">
            <HeroTerminal />
          </div>
        </div>

        <ProofRail />
      </section>

      <section id="proof" className="mx-auto w-full max-w-[1720px] px-5 py-12 sm:px-10 sm:py-16 2xl:px-16">
        <SectionHeading
          number="01"
          eyebrow="Proof"
          title="Validated coverage, stated constraints, visible boundaries."
          body="The landing page should sound like financial software: concrete, scoped, and clear about what the product can and cannot do today."
        />
        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          {proofStats.map(([value, title, body], index) => (
            <Reveal key={title} delay={index * 0.06}>
              <Panel className="p-6">
                <p className="font-mono text-5xl font-semibold text-[#66a3ff]">{value}</p>
                <h3 style={displayStyle} className="mt-5 text-2xl font-semibold text-white">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-400">{body}</p>
              </Panel>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="data-flow" className="mx-auto w-full max-w-[1720px] px-5 py-12 sm:px-10 sm:py-16 2xl:px-16">
        <SectionHeading
          number="02"
          eyebrow="Data flow"
          title="Real records become structured research, then plain-English explanations."
          body="Every product claim should trace back to stored data, visible freshness, and clear limits. Missing values stay missing instead of being filled by AI."
        />
        <Reveal className="mt-8 overflow-hidden rounded-2xl border border-white/10 bg-[#07111f]/80">
          <div className="grid gap-0 md:grid-cols-2 xl:grid-cols-3">
            {dataFlow.map(([step, body], index) => (
              <div key={step} className={`min-h-44 p-6 ${index % 3 !== 2 ? "xl:border-r xl:border-white/10" : ""} ${index < 3 ? "xl:border-b xl:border-white/10" : ""} ${index % 2 === 0 ? "md:border-r md:border-white/10 xl:border-r" : ""} ${index < 4 ? "md:border-b md:border-white/10 xl:border-b" : ""}`}>
                <p className="font-mono text-xs font-semibold uppercase tracking-[0.16em] text-[#66a3ff]">{String(index + 1).padStart(2, "0")} / {step}</p>
                <p className="mt-4 text-sm leading-6 text-slate-300">{body}</p>
              </div>
            ))}
          </div>
          <div className="border-t border-white/10 bg-white/[0.025] px-6 py-5">
            <p className="text-sm leading-6 text-slate-400">
              Trust rule: if data is missing, partial, stale, or not backed by stored records, FundersAI should show that limit beside the answer.
            </p>
          </div>
        </Reveal>
      </section>

      <section id="product" className="mx-auto w-full max-w-[1720px] px-5 py-12 sm:px-10 sm:py-16 2xl:px-16">
        <SectionHeading
          number="03"
          eyebrow="Product"
          title="A comparison terminal, metric table, and AI explanation in one view."
          body="FundersAI should feel like a working research console, not a generic marketing grid."
        />
        <ProductTerminal />
        <PromptMarquee />
      </section>

      <section id="workflow" className="mx-auto w-full max-w-[1720px] px-5 py-12 sm:px-10 sm:py-16 2xl:px-16">
        <SectionHeading
          number="04"
          eyebrow="Workflow"
          title="Pick funds. Compare metrics. Ask questions. Verify sources."
          body="The core workflow stays simple so a researcher can move from screening to explanation without losing the audit trail."
        />
        <div className="mt-8 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {workflow.map(([number, title, body], index) => (
            <Reveal key={title} delay={index * 0.06}>
              <Panel className="min-h-56 p-6">
                <p className="font-mono text-sm font-semibold text-[#66a3ff]">{number}</p>
                <h3 style={displayStyle} className="mt-8 text-2xl font-semibold text-white">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-400">{body}</p>
              </Panel>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="trust" className="mx-auto w-full max-w-[1720px] px-5 py-12 sm:px-10 sm:py-16 2xl:px-16">
        <SectionHeading
          number="05"
          eyebrow="Trust"
          title="Compliance guardrails are part of the interface."
          body="Professional financial AI needs restraint: visible assumptions, source-state labels, and consistent research-only language."
        />
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          {trustCards.map(([Icon, title, body], index) => (
            <Reveal key={title} delay={index * 0.06}>
              <Panel className="grid min-h-44 grid-cols-[auto_1fr] gap-5 p-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-[#66a3ff]/25 bg-[#66a3ff]/10">
                  <Icon className="h-6 w-6 text-[#66a3ff]" />
                </div>
                <div>
                  <h3 style={displayStyle} className="text-2xl font-semibold text-white">{title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-400">{body}</p>
                </div>
              </Panel>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="roadmap" className="mx-auto w-full max-w-[1720px] px-5 py-12 sm:px-10 sm:py-16 2xl:px-16">
        <SectionHeading
          number="06"
          eyebrow="Roadmap"
          title="Broader fund coverage first. Stock research later."
          body="This keeps the page honest about the current product stage while still giving users a clear expansion path."
        />
        <Reveal className="mt-8 overflow-hidden rounded-2xl border border-white/10 bg-[#07111f]/80">
          {roadmap.map(([stage, title, body], index) => (
            <div key={stage} className={`grid gap-4 px-5 py-6 lg:grid-cols-[0.22fr_0.9fr_1fr] lg:items-center ${index !== roadmap.length - 1 ? "border-b border-white/10" : ""}`}>
              <p className="font-mono text-sm font-semibold uppercase tracking-[0.16em] text-[#66a3ff]">{stage}</p>
              <h3 style={displayStyle} className="text-2xl font-semibold text-white">{title}</h3>
              <p className="text-sm leading-6 text-slate-400">{body}</p>
            </div>
          ))}
        </Reveal>
      </section>

      <section id="disclaimer" className="mx-auto w-full max-w-[1720px] px-5 py-12 sm:px-10 2xl:px-16">
        <Reveal>
          <div className="rounded-2xl border border-amber-300/25 bg-amber-300/[0.055] p-6 sm:p-8">
            <DataChip tone="amber">Research-only disclaimer</DataChip>
            <p className="mt-5 max-w-5xl text-base leading-8 text-amber-50/80">
              FundersAI is for research and education only. It does not provide financial advice, investment recommendations, portfolio management, or buy/sell calls. Current coverage is limited while the pipeline expands across major AMCs. Always verify data independently before making financial decisions.
            </p>
          </div>
        </Reveal>
      </section>

      <section className="mx-auto w-full max-w-[1720px] px-5 pb-16 pt-8 sm:px-10 2xl:px-16">
        <Reveal>
          <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#0f172a] p-7 text-center shadow-[0_30px_100px_rgba(0,0,0,0.24)] sm:p-12">
            <div aria-hidden="true" className="absolute inset-x-16 top-0 h-px bg-gradient-to-r from-transparent via-[#66a3ff] to-transparent" />
            <h2 style={displayStyle} className="mx-auto max-w-5xl text-4xl font-semibold leading-tight tracking-normal text-white sm:text-6xl">
              Compare Indian mutual funds with explainable AI.
            </h2>
            <p className="mx-auto mt-5 max-w-3xl text-lg leading-8 text-slate-400">
              Start with verified PPFAS, ICICI, HDFC, and SBI coverage while FundersAI expands the research dataset.
            </p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <PremiumButton href="/dashboard">Start fund research</PremiumButton>
              <PremiumButton href="/login" variant="secondary">Login</PremiumButton>
            </div>
            <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              Research-only. No recommendations. Verified AMC coverage is shown clearly.
            </p>
          </div>
        </Reveal>
      </section>

      <footer className="border-t border-white/[0.07] bg-[#020611] pb-10 pt-14">
        <div className="mx-auto w-full max-w-[1720px] px-5 sm:px-10 2xl:px-16">
          <div className="grid gap-10 lg:grid-cols-12">
            <div className="lg:col-span-5">
              <Image
                src="/FUNDERSAI-vertical.png"
                alt="FundersAI"
                width={2000}
                height={861}
                unoptimized
                className="mb-6 h-16 w-auto object-contain opacity-90"
              />
              <p className="max-w-md text-sm leading-6 text-slate-400">
                Professional AI research workspace for Indian mutual fund comparison. Research-only outputs. No advisory language.
              </p>
              <a href="mailto:contact@fundersai.co.in" className="mt-5 inline-flex text-sm font-semibold text-[#cfe1ff] transition hover:text-white">
                contact@fundersai.co.in
              </a>
            </div>

            <div className="lg:col-span-2">
              <h3 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-[#66a3ff]">Product</h3>
              <nav className="mt-5 flex flex-col gap-3 text-sm text-slate-400">
                <a href="#proof" className="transition hover:text-white">Proof</a>
                <a href="#data-flow" className="transition hover:text-white">Data flow</a>
                <a href="#product" className="transition hover:text-white">Product</a>
                <a href="#workflow" className="transition hover:text-white">Workflow</a>
                <a href="#trust" className="transition hover:text-white">Trust</a>
              </nav>
            </div>

            <div className="lg:col-span-2">
              <h3 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-[#66a3ff]">Legal</h3>
              <nav className="mt-5 flex flex-col gap-3 text-sm text-slate-400">
                <a href="#" className="transition hover:text-white">Terms and Conditions</a>
                <a href="#" className="transition hover:text-white">Privacy Policy</a>
                <a href="#" className="transition hover:text-white">Cookie Policy</a>
              </nav>
            </div>

            <div className="lg:col-span-3">
              <h3 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-amber-300">Strict disclaimer</h3>
              <div className="mt-5 border-l border-amber-300/30 pl-4">
                <p className="text-xs leading-6 text-slate-400">
                  <strong className="font-semibold text-slate-200">FundersAI is strictly a research and educational platform.</strong> We do not provide financial advice, investment recommendations, or buy/sell signals.
                </p>
                <p className="mt-3 text-xs leading-6 text-amber-100/70">
                  Always verify data independently before making financial decisions.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-12 flex flex-col-reverse items-start justify-between gap-5 border-t border-white/[0.07] pt-7 md:flex-row md:items-center">
            <p className="font-mono text-xs uppercase tracking-[0.14em] text-slate-600">
              Copyright {new Date().getFullYear()} FundersAI. All rights reserved.
            </p>
            <div className="flex gap-6 font-mono text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
              <a href="#" className="transition hover:text-white">X</a>
              <a href="#" className="transition hover:text-white">LinkedIn</a>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}
