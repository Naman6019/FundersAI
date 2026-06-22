"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
} from "@phosphor-icons/react";
import LandingPromptBox from "./LandingPromptBox";
import { HeroWave } from "@/components/ui/ai-input-hero";
import { FeatureCarousel } from "@/components/ui/animated-feature-carousel";

function AmbientGlow({ className = "", color = "rgba(0, 255, 157, 0.12)" }) {
  return (
    <div
      className={`pointer-events-none absolute z-0 rounded-full blur-[100px] sm:blur-[140px] ${className}`}
      style={{ background: color }}
    />
  );
}

function HeroGrid() {
  return (
    <div className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center overflow-hidden">
      {/* Animated Glowing Orbs */}
      <div className="absolute top-[10%] left-[20%] h-[40vw] w-[40vw] animate-pulse rounded-full bg-[#00FF9D]/20 blur-[100px] mix-blend-screen" style={{ animationDuration: '8s' }} />
      <div className="absolute top-[30%] right-[20%] h-[40vw] w-[40vw] animate-pulse rounded-full bg-[#66a3ff]/20 blur-[120px] mix-blend-screen" style={{ animationDuration: '12s', animationDelay: '2s' }} />
      
      {/* High-Tech Grid Pattern */}
      <div 
        className="absolute inset-0 z-0 bg-[length:50px_50px] opacity-[0.15]"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(255,255,255,1) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255,255,255,1) 1px, transparent 1px)
          `,
          maskImage: 'radial-gradient(ellipse 80% 80% at 50% 40%, #000 10%, transparent 80%)',
          WebkitMaskImage: 'radial-gradient(ellipse 80% 80% at 50% 40%, #000 10%, transparent 80%)'
        }}
      />
    </div>
  );
}

const ease = [0.22, 1, 0.36, 1];

const dataTrailItems = [
  "HDFC Flexi Cap",
  "NAV INR 1,247.3",
  "Updated 3h ago",
  "Axis Bluechip",
  "NAV INR 892.1",
  "Updated 1h ago",
  "SBI Small Cap",
  "NAV INR 234.6",
  "Updated 2h ago",
  "PPFAS Flexi Cap",
  "Sharp 1.8",
  "Tracking Err 0.4%",
];

const carouselImages = {
  alt: "FundersAI Research Flow",
  // Data Gathering: Server racks and glowing data flows
  step1img1: "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?q=80&w=2000&auto=format&fit=crop",
  step1img2: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=2070&auto=format&fit=crop",
  // Multi-Agent Processing: Abstract AI nodes and circuit boards
  step2img1: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop",
  step2img2: "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1740&auto=format&fit=crop",
  // Confidence Scoring: Verification dashboards and analytics
  step3img: "https://images.unsplash.com/photo-1543286386-2e659306cd6c?q=80&w=2000&auto=format&fit=crop",
  // Synthesis: Clean UI reporting
  step4img: "https://images.unsplash.com/photo-1555421689-d68471e189f2?q=80&w=2000&auto=format&fit=crop",
};

const researchSteps = [
  ["01", "Ask a natural language question", "Compare Axis Large Cap and HDFC Mid Cap, or ask why one fund looks riskier."],
  ["02", "Resolve matching funds", "Typos, AMC shorthand, and scheme variants are routed to normalized records before analysis."],
  ["03", "Open the comparison canvas", "Returns, cost, NAV history, AUM, and risk metrics sit side by side in one workspace."],
  ["04", "Explain risk and cost", "Sharpe, beta, drawdown, expense ratio, and missing fields are translated into plain research context."],
  ["05", "Show sources and confidence", "Freshness, data gaps, and research-only guardrails stay visible before any independent decision."],
];

const intelligenceTiles = [
  {
    label: "Freshness",
    value: "3h",
    title: "Field-level timestamps",
    body: "NAV, holdings, risk metrics, and source rows carry freshness status instead of hiding stale data.",
    className: "lg:col-span-12",
  },
  {
    label: "Missing fields",
    value: "16",
    title: "Limits are visible",
    body: "When expense ratio, holdings, or benchmark data is absent, FundersAI flags it before the explanation.",
    className: "lg:col-span-7",
  },
  {
    label: "Coverage",
    value: "5",
    title: "Supported AMC families",
    body: "PPFAS, ICICI, HDFC, SBI, and Axis are treated as active supported coverage in the research flow.",
    className: "lg:col-span-5",
  },
  {
    label: "Confidence",
    value: "0.91",
    title: "Resolver-aware badges",
    body: "The interface distinguishes a matched fund from an ambiguous or partial comparison.",
    className: "lg:col-span-8 lg:col-start-3",
  },
];

const proofStats = [
  ["INR 81.58L Cr", "Indian MF industry AUM", "As of May 31, 2026", ""],
  ["27.66 Cr", "mutual fund folios", "Large participation, uneven clarity", ""],
  ["INR 30,954 Cr", "monthly SIP contribution", "May 2026", ""],
  ["0", "advisory outputs", "Research only, no buy/sell calls", ""],
];

function MetadataLabel({ children, className = "" }) {
  return (
    <p className={`text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)] ${className}`}>
      {children}
    </p>
  );
}

function Reveal({ children, className = "", delay = 0 }) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 60 }}
      whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 1.6, ease, delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function HeroLine({ children, delay }) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.span
      className="block"
      initial={reduceMotion ? false : { opacity: 0, y: 80 }}
      animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
      transition={{ duration: 1.6, ease, delay }}
    >
      {children}
    </motion.span>
  );
}

function EditorialButton({ href, children }) {
  return (
    <Link
      href={href}
      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-white/20 bg-white/5 px-6 text-sm font-semibold text-white backdrop-blur-md transition-all hover:bg-white/10 hover:border-white/30"
    >
      {children}
      <ArrowRight className="h-4 w-4" />
    </Link>
  );
}

function DataTrailRibbon({ compact = false }) {
  return (
    <div className={`landing-data-trail ${compact ? "landing-data-trail-compact" : ""}`} aria-label="FundersAI data trail">
      <div className="landing-data-trail-track">
        {[...Array(3)].map((_, groupIndex) => (
          <div className="landing-data-trail-group" key={groupIndex}>
            {dataTrailItems.map((item, itemIndex) => (
              <React.Fragment key={`${groupIndex}-${item}`}>
                <span>{item}</span>
                {itemIndex < dataTrailItems.length - 1 ? <b>/</b> : null}
              </React.Fragment>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function ComparisonWorkspaceMock() {
  const panels = [
    ["Chat", "Compare Axis Large Cap and HDFC Mid Cap for risk, cost, and source freshness."],
    ["Canvas", "Side-by-side metrics with NAV, expense ratio, Sharpe, drawdown, and AUM."],
    ["Sources", "Freshness badges, missing fields, and confidence status remain visible."],
  ];

  return (
    <div className="grid overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-md lg:grid-cols-3">
      {panels.map(([title, body], index) => (
        <div
          key={title}
          className="group relative min-h-72 border-b border-white/10 p-6 transition-all hover:bg-white/[0.04] lg:border-b-0 lg:border-r lg:last:border-r-0"
        >
          <MetadataLabel>0{index + 1}</MetadataLabel>
          <h3 className="mt-5 text-2xl font-semibold text-white">{title}</h3>
          <p className="mt-5 text-sm leading-7 text-[var(--text-muted)]">{body}</p>
          <div className="mt-8 rounded-lg border border-[#00FF9D]/30 bg-[#00FF9D]/10 px-3 py-2 text-xs text-[#00FF9D] opacity-0 backdrop-blur-md transition-opacity duration-300 group-hover:opacity-100">
            Research-only surface. No buy/sell language.
          </div>
          <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100" style={{boxShadow: "inset 0 0 40px rgba(0, 255, 157, 0.05)"}} />
        </div>
      ))}
    </div>
  );
}

function NoiseOverlay() {
  return (
    <div
      className="pointer-events-none fixed inset-0 z-50 opacity-[0.04] mix-blend-multiply"
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
      }}
    />
  );
}

export default function FundersAILandingPage() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();

  return (
    <main className="landing-editorial relative min-h-screen overflow-x-hidden bg-[var(--bg-base)] text-[var(--text-primary)]  selection:bg-[var(--accent-crimson)] selection:text-[var(--bg-base)]">
      <NoiseOverlay />

      <header className="fixed top-0 z-40 w-full border-b border-[var(--line)] bg-[var(--bg-base)]/88 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-[1500px] items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/" className="flex items-center gap-3">
            <Image 
              src="/FUNDERSAI-nobackground.png" 
              alt="FundersAI Logo" 
              width={160} 
              height={40} 
              unoptimized 
              className="h-10 w-auto object-contain"
              style={{ width: 'auto' }}
            />
          </Link>
          <nav className="hidden items-center gap-8 text-sm font-semibold text-[var(--text-muted)] md:flex">
            <a href="#flow" className="transition hover:text-[var(--text-primary)]">Flow</a>
            <a href="#intelligence" className="transition hover:text-[var(--text-primary)]">Intelligence</a>
            <a href="#workspace" className="transition hover:text-[var(--text-primary)]">Workspace</a>
            <a href="#proof" className="transition hover:text-[var(--text-primary)]">Proof</a>
          </nav>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-semibold text-[var(--text-muted)] transition hover:text-[var(--text-primary)]">
              Login
            </Link>
            <EditorialButton href="/dashboard">Workspace</EditorialButton>
          </div>
        </div>
      </header>
      <HeroWave 
        title={<>Research funds <br /><span className="bg-gradient-to-r from-white via-white/80 to-[#00FF9D] bg-clip-text text-transparent opacity-90 mix-blend-lighten">at lightspeed</span></>}
        subtitle="We analyze millions of data points to help you pick the best mutual funds in India."
        onPromptSubmit={(query) => {
          router.push(`/dashboard?query=${encodeURIComponent(query)}`);
        }}
      />

      <DataTrailRibbon />

      <section id="flow" className="relative mx-auto w-full max-w-[1500px] gap-12 px-5 py-24 sm:px-8 lg:py-32">
        <div className="relative mb-16 text-center z-10">
          <AmbientGlow className="left-1/2 top-0 h-[300px] w-[300px] -translate-x-1/2" color="rgba(102, 163, 255, 0.1)" />
          <MetadataLabel className="text-[var(--accent-glow)] mx-auto relative z-10">Live research flow</MetadataLabel>
          <h2 className="mt-8 font-sans text-4xl sm:text-6xl lg:text-7xl font-bold leading-[1.05] tracking-tight text-white relative z-10">
            Research Flow
          </h2>
        </div>

        <FeatureCarousel image={carouselImages} />
      </section>

      <section id="intelligence" className="relative mx-auto w-full max-w-[1500px] border-t border-white/10 px-5 py-24 sm:px-8 lg:py-32">
        <AmbientGlow className="right-0 top-1/2 h-[400px] w-[400px] -translate-y-1/2" color="rgba(0, 255, 157, 0.05)" />
        <Reveal className="relative z-10 max-w-5xl">
          <MetadataLabel className="text-[var(--accent-glow)]">Source intelligence layer</MetadataLabel>
          <h2 className="mt-8 font-sans text-[10.5vw] font-bold leading-[1.05] tracking-tight text-white sm:text-[8vw] lg:text-[5.7vw]">
            The answer shows<br />what it knows.
          </h2>
        </Reveal>

        <div className="relative z-10 mt-14 grid gap-8 lg:grid-cols-12">
          {intelligenceTiles.map((tile, index) => (
            <Reveal key={tile.title} delay={index * 0.06} className={tile.className}>
              <div className="group relative h-full min-h-64 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-md transition-all hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.04]">
                <MetadataLabel>{tile.label}</MetadataLabel>
                <p className="mt-8 font-sans text-[12vw] font-bold tracking-tight leading-none text-transparent bg-clip-text bg-gradient-to-r from-[#00FF9D] to-[#66a3ff] sm:text-[10vw] lg:text-[6vw]">
                  {tile.value}
                </p>
                <h3 className="mt-8 text-2xl font-semibold text-white">{tile.title}</h3>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">{tile.body}</p>
                <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100" style={{boxShadow: "inset 0 0 60px rgba(0, 255, 157, 0.05)"}} />
              </div>
            </Reveal>
          ))}
        </div>
        <div className="relative z-10 mt-16 flex justify-center">
          <EditorialButton href="/dashboard">Try FundersAI Workspace</EditorialButton>
        </div>
      </section>

      <section id="workspace" className="relative bg-white/[0.01]">
        <div className="relative z-10 mx-auto grid w-full max-w-[1500px] gap-12 px-5 py-24 sm:px-8 lg:grid-cols-[0.28fr_0.72fr] lg:py-32">
          <div>
            <div className="lg:sticky lg:top-32">
              <MetadataLabel className="text-[var(--accent-glow)]">Comparison workspace</MetadataLabel>
              <h2 className="mt-8 font-sans text-[10.5vw] font-bold leading-[1.05] tracking-tight text-white sm:text-[8vw] lg:text-[4.8vw]">
                Not a chat toy.
              </h2>
              <p className="mt-6 text-sm leading-7 text-[var(--text-muted)]">
                The product surface keeps source-backed research, comparison, and guardrails visible together.
              </p>
              <div className="mt-10">
                <EditorialButton href="/dashboard">Open Workspace</EditorialButton>
              </div>
            </div>
          </div>
          <Reveal>
            <ComparisonWorkspaceMock />
          </Reveal>
        </div>
      </section>

      <section id="proof" className="relative mx-auto w-full max-w-[1500px] border-t border-white/10 px-5 py-24 sm:px-8 lg:py-32">
        <AmbientGlow className="left-1/4 top-1/2 h-[300px] w-[500px] -translate-x-1/2 -translate-y-1/2" color="rgba(102, 163, 255, 0.06)" />
        <Reveal className="relative z-10 max-w-4xl">
          <MetadataLabel className="text-[var(--accent-glow)]">Market proof</MetadataLabel>
          <h2 className="mt-8 font-sans text-[10.5vw] font-bold leading-[1.05] tracking-tight text-white sm:text-[8vw] lg:text-[5.4vw]">
            More capital needs better research.
          </h2>
        </Reveal>

        <div className="relative z-10 mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {proofStats.map(([value, title, body, offset], index) => (
            <Reveal key={title} delay={index * 0.15} className={offset}>
              <div className="group relative min-h-64 overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-md transition-all hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.04]">
                <p className="font-sans text-[10.5vw] font-bold tracking-tight leading-none text-transparent bg-clip-text bg-gradient-to-br from-white to-white/40 sm:text-[9vw] lg:text-[4.2vw]">
                  {value}
                </p>
                <MetadataLabel className="mt-8">{title}</MetadataLabel>
                <p className="mt-4 text-sm leading-7 text-[var(--text-muted)]">{body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="relative w-full border-t border-white/10 overflow-hidden bg-[var(--bg-base)]">
        <AmbientGlow className="left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2" color="rgba(0, 255, 157, 0.15)" />
        <div className="relative z-10 mx-auto w-full max-w-[1500px] px-5 py-32 sm:px-8 lg:py-48 text-center">
          <Reveal>
            <h2 className="font-sans text-5xl sm:text-7xl lg:text-8xl font-bold tracking-tight text-white mb-8 drop-shadow-2xl">
              Start building <br className="hidden sm:block" />your research.
            </h2>
            <p className="text-xl sm:text-2xl text-white/60 mb-12 max-w-2xl mx-auto leading-relaxed">
              Join thousands of quantitative researchers and institutional investors using FundersAI.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/login" className="inline-flex items-center justify-center rounded-full bg-[#00FF9D] px-8 py-4 text-base font-bold text-black transition-all hover:scale-105 hover:bg-[#00FF9D]/90 hover:shadow-[0_0_40px_rgba(0,255,157,0.4)]">
                Get Started Free
              </Link>
              <Link href="#flow" className="inline-flex items-center justify-center rounded-full border border-white/20 bg-white/5 px-8 py-4 text-base font-bold text-white transition-all hover:bg-white/10">
                Explore the flow
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      <footer className="relative border-t border-[var(--line)] bg-[var(--bg-base)] px-5 py-12 sm:px-8">
        <div className="mx-auto grid w-full max-w-[1500px] gap-8 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
          <div className="flex items-center gap-3">
            <Image 
              src="/FUNDERSAI-nobackground.png" 
              alt="FundersAI Logo" 
              width={160} 
              height={40} 
              unoptimized 
              className="h-10 w-auto object-contain"
              style={{ width: 'auto' }}
            />
          </div>
          <div className="flex flex-wrap gap-6 text-sm font-semibold text-[var(--text-muted)]">
            <a href="#flow" className="transition hover:text-[var(--text-primary)]">Flow</a>
            <a href="#intelligence" className="transition hover:text-[var(--text-primary)]">Intelligence</a>
            <a href="#workspace" className="transition hover:text-[var(--text-primary)]">Workspace</a>
          </div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--text-muted)] lg:text-right">
            Research only · not financial advice · verify independently
          </p>
        </div>
      </footer>
    </main>
  );
}
