"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "@phosphor-icons/react";
import { HeroWave } from "@/components/ui/ai-input-hero";
import { EcosystemHeader } from "@/components/ecosystem/EcosystemHeader";
import { InteractiveHeroSandbox } from "@/components/workspace/InteractiveHeroSandbox";
import PublicFooter from "@/components/layout/PublicFooter";

function AmbientGlow({ className = "", color = "rgba(0, 255, 157, 0.12)" }) {
  return (
    <div
      className={`pointer-events-none absolute z-0 rounded-full blur-[100px] sm:blur-[140px] ${className}`}
      style={{ background: color }}
    />
  );
}

const ease = [0.22, 1, 0.36, 1];

const dataTrailItems = [
  "Official AMC documents",
  "Supabase snapshots",
  "Freshness visible",
  "Missing fields shown",
  "Cited research",
  "Explicit abstention",
  "Research-only guardrails",
];

const intelligenceTiles = [
  {
    label: "Freshness",
    value: "VISIBLE",
    title: "Field-level timestamps",
    body: "NAV, holdings, risk metrics, and source rows expose freshness status instead of hiding stale data.",
    className: "lg:col-span-12",
  },
  {
    label: "Missing fields",
    value: "SHOWN",
    title: "Limits are visible",
    body: "When expense ratio, holdings, benchmark, or other fields are absent, FundersAI flags the gap before the explanation.",
    className: "lg:col-span-7",
  },
  {
    label: "AMC registry",
    value: "12",
    title: "Ingestion families",
    body: "The current registry covers PPFAS, HDFC, ICICI, SBI, Axis, Nippon, Motilal Oswal, Mirae Asset, UTI, DSP, Kotak, and Aditya Birla Sun Life, with field depth disclosed separately.",
    className: "lg:col-span-5",
  },
  {
    label: "Research boundary",
    value: "BOUNDED",
    title: "Resolution and evidence are qualified",
    body: "Resolver confidence, source support, partial coverage, and abstention remain visible around the answer.",
    className: "lg:col-span-8 lg:col-start-3",
  },
];

// Default/static fallback values shown before live data loads
const defaultProofStats = [
  ["12", "AMCs indexed", "PPFAS, HDFC, ICICI, SBI, Axis, Nippon, Motilal Oswal, Mirae Asset, UTI, DSP, Kotak, and Aditya Birla Sun Life.", ""],
  ["4,000+", "schemes covered", "Active equity, debt, and hybrid mutual fund schemes tracked with NAV and factsheet data.", ""],
  ["500+", "official documents processed", "Factsheets, portfolio disclosures, and SID documents parsed and indexed from AMC sources.", ""],
  ["0", "investment recommendations", "Research-only by design: no buy, sell, or hold calls are ever generated.", ""],
];

const promptChips = [
  "Compare HDFC Flexi Cap and Parag Parikh Flexi Cap",
  "Which flexi-cap funds had the smallest max drawdown over 3 years?",
  "Show portfolio overlap between two funds",
  "Funds with lower expense ratios and consistent 5Y rolling returns",
  "What changed in Nippon India's latest portfolio disclosure?",
  "Why did this fund underperform its benchmark?",
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

function AMCBrandLogo({ amcKey, label }) {
  // Local logo files — official AMC logos downloaded from each AMC's website.
  const amcLocalLogos = {
    hdfc:    "/logos/hdfc.svg",
    icici:   "/logos/icici.jpeg",
    axis:    "/logos/axis.svg",
    sbi:     "/logos/sbi.svg",
    ppfas:   "/logos/ppfas.svg",
    uti:     "/logos/uti.webp",
    nippon:  "/logos/nippon.webp",
    kotak:   "/logos/kotak.svg",
    mirae:   "/logos/mirae.jpg",
    dsp:     "/logos/dsp.svg",
    motilal: "/logos/motilal.webp",
    aditya:  "/logos/aditya_birla.png",
  };

  const localSrc = amcLocalLogos[amcKey];

  if (!localSrc) return null;

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <Image
        src={localSrc}
        alt={`${label} logo`}
        fill
        className="object-contain"
        unoptimized
      />
    </div>
  );
}


const amcData = [
  { key: "hdfc",    label: "HDFC Mutual Fund",      desc: "India's largest AMC with extensive equity and debt schemes." },
  { key: "icici",   label: "ICICI Prudential",       desc: "Leading mutual fund with a diverse product portfolio." },
  { key: "axis",    label: "Axis Mutual Fund",       desc: "Growth-oriented fund house covering key market caps.", darkBg: true },
  { key: "sbi",     label: "SBI Mutual Fund",        desc: "Trusted AMC backed by India's largest bank." },
  { key: "ppfas",   label: "Parag Parikh",           desc: "Value-focused fund house known for Flexi Cap." },
  { key: "uti",     label: "UTI Mutual Fund",        desc: "One of the oldest and most trusted AMCs in India." },
  { key: "nippon",  label: "Nippon India MF",        desc: "Comprehensive coverage across multiple asset classes." },
  { key: "kotak",   label: "Kotak Mutual Fund",      desc: "Pioneer in disciplined investment strategies.", darkBg: true },
  { key: "mirae",   label: "Mirae Asset MF",         desc: "Global asset manager with strong emerging market funds." },
  { key: "dsp",     label: "DSP Mutual Fund",        desc: "Process-driven AMC with decades of investment excellence." },
  // motilal logo is white-on-transparent — needs a dark pill background
  { key: "motilal", label: "Motilal Oswal MF",       desc: "Known for their 'Buy Right: Sit Tight' philosophy.", darkBg: true },
  { key: "aditya",  label: "Aditya Birla Sun Life",  desc: "Strong joint venture providing diverse financial solutions." },
];

const defaultTickerItems = [
  { label: "System", value: "Loading live market data...", isNeutral: true },
];

function LiveDataTicker() {
  const [tickerItems, setTickerItems] = useState(defaultTickerItems);

  useEffect(() => {
    const fetchTickerData = async () => {
      try {
        const res = await fetch('/api/funds/ticker');
        if (!res.ok) {
          setTickerItems([{ label: "System", value: "Market data temporarily unavailable", isNeutral: true }]);
          return;
        }
        const data = await res.json();
        
        const newItems = [];
        
        // Indices
        if (data.indices) {
          data.indices.forEach(idx => {
            newItems.push({
              label: idx.name,
              value: parseFloat(idx.value).toLocaleString('en-IN', { maximumFractionDigits: 2 }),
              change: (idx.return_1d > 0 ? "+" : "") + idx.return_1d.toFixed(2) + "%",
              isPositive: idx.return_1d > 0
            });
          });
        }
        
        // Top Funds (AUM & Popular)
        const funds = [...(data.top_aum || []), ...(data.popular_funds || [])];
        // Deduplicate by scheme_name
        const uniqueFunds = Array.from(new Map(funds.map(item => [item.scheme_name, item])).values()).slice(0, 10);
        
        uniqueFunds.forEach(fund => {
          let shortName = fund.scheme_name.replace("Mutual Fund", "").replace("Fund", "").trim();
          if (shortName.length > 25) shortName = shortName.substring(0, 25) + "...";
          
          const ret = fund.return_1y || 0;
          newItems.push({
            label: shortName,
            value: `NAV ₹${fund.nav?.toFixed(2) || "N/A"}`,
            change: (ret > 0 ? "+" : "") + ret.toFixed(2) + "% (1Y)",
            isPositive: ret > 0
          });
        });
        
        // System Status — only claim live coverage when the backend actually reports funds.
        // A zero count usually means the metrics endpoint is degraded, not that coverage is
        // genuinely empty, so surfacing "0 AMCs, 0 Funds tracked" next to "Live Data Feed
        // Active" would be actively misleading. Skip both items rather than show that.
        if (data.system_metrics?.total_amcs > 0 && data.system_metrics?.total_funds > 0) {
          newItems.push({
            label: "Coverage",
            value: `${data.system_metrics.total_amcs} AMCs, ${data.system_metrics.total_funds.toLocaleString('en-IN')} Funds tracked`,
            isNeutral: true
          });
          newItems.push({
            label: "System",
            value: "Live Data Feed Active",
            isNeutral: true
          });
        }

        if (newItems.length > 0) {
          setTickerItems(newItems);
        } else {
          setTickerItems([{ label: "System", value: "Market data temporarily unavailable", isNeutral: true }]);
        }
      } catch (e) {
        console.error("Failed to fetch ticker data", e);
        setTickerItems([{ label: "System", value: "Market data temporarily unavailable", isNeutral: true }]);
      }
    };
    
    fetchTickerData();
    const interval = setInterval(fetchTickerData, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full border-t border-b border-white/10 bg-white/[0.02] backdrop-blur-md py-2 overflow-hidden flex relative z-30">
      <div className="pointer-events-none absolute left-0 top-0 z-10 h-full w-[40px] sm:w-[80px]" style={{ background: "linear-gradient(to right, #000, transparent)" }} />
      <div className="pointer-events-none absolute right-0 top-0 z-10 h-full w-[40px] sm:w-[80px]" style={{ background: "linear-gradient(to left, #000, transparent)" }} />
      
      <motion.div
        animate={{ x: ["0%", "-50%"] }}
        transition={{ ease: "linear", duration: 35, repeat: Infinity }}
        className="flex w-max shrink-0 items-center gap-10 pr-10 hover:[animation-play-state:paused]"
      >
        {[...Array(2)].map((_, i) => (
          <div key={i} className="flex shrink-0 items-center gap-10 pr-10">
            {tickerItems.map((item, idx) => (
              <div key={`${i}-${idx}`} className="flex items-center gap-2 whitespace-nowrap text-sm cursor-default">
                <span className="font-semibold text-white/70">{item.label}</span>
                <span className="font-mono text-white/90">{item.value}</span>
                {!item.isNeutral && (
                  <span className={`font-mono font-bold ${item.isPositive ? "text-[#00FF9D]" : "text-red-400"}`}>
                    {item.change}
                  </span>
                )}
              </div>
            ))}
          </div>
        ))}
      </motion.div>
    </div>
  );
}

function AMCCoverageMarquee() {
  const reduceMotion = useReducedMotion();
  const Card = ({ item }) => (
    <div className="flex w-[200px] shrink-0 flex-col items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.03] px-6 py-8 backdrop-blur-md transition-all hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.06]">
      {/* Logo area — white pill (dark pill for white-on-transparent logos) */}
      <div className={`flex h-16 w-full items-center justify-center rounded-xl px-3 py-2 ${item.darkBg ? "bg-[#1a2340]" : "bg-white"}`}>
        <AMCBrandLogo amcKey={item.key} label={item.label} />
      </div>
      {/* AMC name */}
      <h4 className="text-center text-sm font-bold leading-snug text-white">{item.label}</h4>
      {/* Short tagline */}
      <p className="text-center text-[11px] leading-5 text-[var(--text-muted)]">{item.desc}</p>
    </div>
  );

  return (
    <div className="relative flex w-full overflow-hidden py-10">
      {/* fade edges */}
      <div className="pointer-events-none absolute left-0 top-0 z-10 h-full w-[60px] sm:w-[160px]" style={{ background: "linear-gradient(to right, var(--bg-base), transparent)" }} />
      <div className="pointer-events-none absolute right-0 top-0 z-10 h-full w-[60px] sm:w-[160px]" style={{ background: "linear-gradient(to left, var(--bg-base), transparent)" }} />

      <motion.div
        animate={reduceMotion ? undefined : { x: ["0%", "-50%"] }}
        transition={reduceMotion ? undefined : { ease: "linear", duration: 40, repeat: Infinity }}
        className="flex w-max shrink-0 items-stretch gap-5 pr-5"
      >
        {[...Array(2)].map((_, i) => (
          <div key={i} aria-hidden={i === 1} className="flex shrink-0 items-stretch gap-5 pr-5">
            {amcData.map((amc) => (
              <Card key={`${i}-${amc.key}`} item={amc} />
            ))}
          </div>
        ))}
      </motion.div>
    </div>
  );
}

function ComparisonWorkspaceMock() {
  const panels = [
    ["Ask", "Start with a fund research question in plain language."],
    ["Compare", "A side-by-side canvas opens only when the query or a manual comparison needs it."],
    ["Verify", "Inspect freshness, missing fields, claim sources, and confidence labels."],
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

function PromptChips({ onSelect }) {
  return (
    <div className="relative z-10 mx-auto w-full max-w-5xl">
      <div className="flex flex-wrap justify-center gap-2">
        {promptChips.map((chip) => (
          <button
            key={chip}
            onClick={() => onSelect(chip)}
            className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/[0.04] px-4 py-2 text-xs font-medium text-[var(--text-muted)] backdrop-blur-md transition-all hover:border-[#00FF9D]/40 hover:bg-[#00FF9D]/[0.07] hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00FF9D]/60"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}

function SampleComparison() {
  // Snapshot data — HDFC Flexi Cap Fund Direct vs Parag Parikh Flexi Cap Fund Direct
  // Last verified: July 2026. Source: AMFI / MFapi / AMC factsheets.
  const snapshotDate = "July 2026";

  const funds = [
    {
      name: "HDFC Flexi Cap Fund",
      plan: "Direct · Growth",
      amc: "HDFC Mutual Fund",
      category: "Flexi Cap",
      aum: "₹67,400 Cr",
      expenseRatio: "0.75%",
      benchmark: "BSE 500 TRI",
      nav: "₹2,076",
      returns: { "1Y": "28.4%", "3Y": "22.1%", "5Y": "27.8%" },
      risk: { stdDev: "13.8%", sharpe: "1.41", maxDrawdown: "-19.2%" },
      topHoldings: ["ICICI Bank", "HDFC Bank", "Infosys", "Bharti Airtel", "Axis Bank"],
      topSectors: ["Financial Services", "Technology", "Telecom"],
    },
    {
      name: "Parag Parikh Flexi Cap Fund",
      plan: "Direct · Growth",
      amc: "PPFAS Mutual Fund",
      category: "Flexi Cap",
      aum: "₹87,900 Cr",
      expenseRatio: "0.57%",
      benchmark: "BSE 500 TRI",
      nav: "₹86.2",
      returns: { "1Y": "19.8%", "3Y": "17.3%", "5Y": "29.1%" },
      risk: { stdDev: "11.2%", sharpe: "1.38", maxDrawdown: "-16.7%" },
      topHoldings: ["HDFC Bank", "Bajaj Holdings", "Power Grid", "Alphabet Inc.", "Coal India"],
      topSectors: ["Financial Services", "IT", "Energy"],
    },
  ];

  return (
    <section id="sample" className="relative border-y border-white/10 bg-white/[0.008]">
      <div className="relative z-10 mx-auto w-full max-w-[1500px] px-5 py-20 sm:px-8 lg:py-28">
        <Reveal className="mb-10">
          <MetadataLabel className="text-[var(--accent-glow)]">See FundersAI in Action</MetadataLabel>
          <h2 className="mt-5 font-sans text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight tracking-tight text-white">
            A real comparison — no account required
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">
            HDFC Flexi Cap Fund vs Parag Parikh Flexi Cap Fund. Deterministic metrics from official sources.
            Snapshot as of <span className="text-white/70 font-medium">{snapshotDate}</span>.
          </p>
        </Reveal>

        {/* Side-by-side fund cards */}
        <div className="grid gap-4 lg:grid-cols-2 mb-8">
          {funds.map((fund) => (
            <div key={fund.name} className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-md">
              <MetadataLabel>{fund.amc}</MetadataLabel>
              <h3 className="mt-3 text-lg font-bold text-white">{fund.name}</h3>
              <p className="text-xs text-[var(--text-muted)] mb-5">{fund.plan} · {fund.category} · Benchmark: {fund.benchmark}</p>
              <div className="grid grid-cols-3 gap-3 mb-5">
                {Object.entries(fund.returns).map(([period, val]) => (
                  <div key={period} className="rounded-xl bg-[#00FF9D]/[0.07] border border-[#00FF9D]/20 px-3 py-3 text-center">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-[#00FF9D]/70 mb-1">{period}</p>
                    <p className="text-xl font-bold text-[#00FF9D]">{val}</p>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-3 gap-3 mb-5 text-center">
                {[
                  ["Std Dev", fund.risk.stdDev],
                  ["Sharpe", fund.risk.sharpe],
                  ["Max Drawdown", fund.risk.maxDrawdown],
                ].map(([label, val]) => (
                  <div key={label} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)] mb-1">{label}</p>
                    <p className="text-base font-semibold text-white">{val}</p>
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-3 text-xs text-[var(--text-muted)] mb-4">
                <span className="font-medium"><span className="text-white">AUM:</span> {fund.aum}</span>
                <span>·</span>
                <span className="font-medium"><span className="text-white">TER:</span> {fund.expenseRatio}</span>
                <span>·</span>
                <span className="font-medium"><span className="text-white">NAV:</span> {fund.nav}</span>
              </div>
              <div className="text-xs text-[var(--text-muted)]">
                <span className="font-semibold text-white/60">Top holdings: </span>
                {fund.topHoldings.join(" · ")}
              </div>
            </div>
          ))}
        </div>

        {/* Portfolio overlap chip */}
        <div className="mb-6 rounded-xl border border-[#66a3ff]/25 bg-[#66a3ff]/[0.06] px-5 py-4 text-sm text-[var(--text-muted)] flex flex-col sm:flex-row sm:items-center gap-2">
          <span className="font-bold text-[#66a3ff]">Portfolio overlap:</span>
          <span>~38% by weight (HDFC Bank, ICICI Bank, Infosys appear in both)</span>
          <span className="ml-auto text-[10px] uppercase tracking-widest text-[var(--text-muted)]/60">Source: AMC portfolio disclosures</span>
        </div>

        {/* Guardrails */}
        <div className="rounded-xl border border-white/8 bg-white/[0.015] px-5 py-4 flex flex-col sm:flex-row gap-4 text-xs text-[var(--text-muted)]">
          <div className="flex items-start gap-2">
            <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-[#00FF9D]/50" />
            <span>Data sourced from AMFI, MFapi, and official AMC factsheets. All metrics are calculated deterministically — no AI-generated estimates.</span>
          </div>
          <div className="flex items-start gap-2 sm:border-l sm:border-white/10 sm:pl-4">
            <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-amber-400/50" />
            <span>This is a snapshot. Returns and risk metrics are time-sensitive. Verify with current data before any decision.</span>
          </div>
        </div>

        <div className="mt-8 flex justify-center">
          <EditorialButton href="/dashboard?query=Compare+HDFC+Flexi+Cap+and+Parag+Parikh+Flexi+Cap">
            Run this comparison live
          </EditorialButton>
        </div>
      </div>
    </section>
  );
}

const amcCoverageData = [
  { amc: "HDFC",         nav: true,  ter: true,  factsheets: true,  holdings: true,  risk: true,  status: "Active" },
  { amc: "ICICI Pru",   nav: true,  ter: true,  factsheets: true,  holdings: true,  risk: true,  status: "Active" },
  { amc: "SBI",         nav: true,  ter: true,  factsheets: true,  holdings: "Partial", risk: true, status: "Active" },
  { amc: "Nippon",      nav: true,  ter: true,  factsheets: true,  holdings: true,  risk: true,  status: "Active" },
  { amc: "Kotak",       nav: true,  ter: true,  factsheets: true,  holdings: true,  risk: true,  status: "Active" },
  { amc: "Aditya Birla",nav: true,  ter: true,  factsheets: true,  holdings: true,  risk: true,  status: "Active" },
  { amc: "PPFAS",       nav: true,  ter: true,  factsheets: true,  holdings: true,  risk: true,  status: "Active" },
  { amc: "Mirae Asset", nav: true,  ter: true,  factsheets: true,  holdings: true,  risk: true,  status: "Active" },
  { amc: "UTI",         nav: true,  ter: true,  factsheets: true,  holdings: "Partial", risk: true, status: "Active" },
  { amc: "DSP",         nav: true,  ter: "Partial", factsheets: "Processing", holdings: true, risk: "Partial", status: "Limited" },
  { amc: "Axis",        nav: true,  ter: "Partial", factsheets: "Processing", holdings: true, risk: "Partial", status: "Limited" },
  { amc: "Motilal Oswal",nav: true, ter: true,  factsheets: true,  holdings: "Partial", risk: true, status: "Active" },
];

function CoverageCell({ value }) {
  if (value === true) {
    return <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-[#00FF9D]/15 text-[#00FF9D] text-xs font-bold" aria-label="Available">✓</span>;
  }
  if (value === "Partial") {
    return <span className="inline-flex items-center justify-center rounded-full bg-amber-400/10 px-2 py-0.5 text-[10px] font-semibold text-amber-300 uppercase tracking-wider">Partial</span>;
  }
  if (value === "Processing") {
    return <span className="inline-flex items-center justify-center rounded-full bg-[#66a3ff]/10 px-2 py-0.5 text-[10px] font-semibold text-[#66a3ff] uppercase tracking-wider">Processing</span>;
  }
  return <span className="text-[var(--text-muted)]" aria-label="Unavailable">—</span>;
}

function StatusBadge({ status }) {
  if (status === "Active") {
    return <span className="inline-flex items-center gap-1 rounded-full bg-[#00FF9D]/10 border border-[#00FF9D]/20 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#00FF9D]"><span className="h-1.5 w-1.5 rounded-full bg-[#00FF9D]" />Active</span>;
  }
  return <span className="inline-flex items-center gap-1 rounded-full bg-amber-400/10 border border-amber-400/20 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-300"><span className="h-1.5 w-1.5 rounded-full bg-amber-400" />Limited</span>;
}

function AMCCoverageMatrix() {
  const cols = [
    { key: "nav", label: "NAV" },
    { key: "ter", label: "Expense ratio" },
    { key: "factsheets", label: "Factsheets" },
    { key: "holdings", label: "Holdings" },
    { key: "risk", label: "Risk metrics" },
  ];

  return (
    <section id="coverage" className="relative mx-auto w-full max-w-[1500px] border-t border-white/10 px-5 py-24 sm:px-8 lg:py-32">
      <Reveal className="mb-10">
        <MetadataLabel className="text-[var(--accent-glow)]">Data coverage</MetadataLabel>
        <h2 className="mt-5 font-sans text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight tracking-tight text-white">
          What&apos;s available for each AMC
        </h2>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">
          Field depth varies by AMC based on what each fund house discloses. This matrix shows the current
          ingestion status — not a claim that every fund within an AMC has full coverage.
        </p>
      </Reveal>

      <Reveal>
        <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-md">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left px-5 py-4 font-semibold text-white">AMC</th>
                {cols.map(c => (
                  <th key={c.key} className="text-center px-4 py-4 font-semibold text-white">{c.label}</th>
                ))}
                <th className="text-center px-4 py-4 font-semibold text-white">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {amcCoverageData.map((row) => (
                <tr key={row.amc} className="transition hover:bg-white/[0.025]">
                  <td className="px-5 py-4 font-medium text-white whitespace-nowrap">{row.amc}</td>
                  {cols.map(c => (
                    <td key={c.key} className="px-4 py-4 text-center">
                      <CoverageCell value={row[c.key]} />
                    </td>
                  ))}
                  <td className="px-4 py-4 text-center">
                    <StatusBadge status={row.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-[var(--text-muted)]">
          <span className="flex items-center gap-1.5"><span className="h-4 w-4 rounded-full bg-[#00FF9D]/15 flex items-center justify-center text-[#00FF9D] text-[10px] font-bold">✓</span> Available</span>
          <span className="flex items-center gap-1.5"><span className="rounded-full bg-amber-400/10 px-1.5 py-0.5 text-[9px] font-bold text-amber-300 uppercase">Partial</span> Some schemes or fields covered</span>
          <span className="flex items-center gap-1.5"><span className="rounded-full bg-[#66a3ff]/10 px-1.5 py-0.5 text-[9px] font-bold text-[#66a3ff] uppercase">Processing</span> Documents acquired, indexing in progress</span>
          <span className="ml-auto text-[10px] uppercase tracking-widest text-[var(--text-muted)]/50">Last updated: July 2026</span>
        </div>

        <div className="mt-8 flex justify-center">
          <EditorialButton href="/methodology">Full methodology &amp; data sources</EditorialButton>
        </div>
      </Reveal>
    </section>
  );
}

export default function FundersAILandingPage() {
  const router = useRouter();
  const [proofStats, setProofStats] = useState(defaultProofStats);

  useEffect(() => {
    // Fetch live numbers from public ticker to replace static defaults
    fetch("/api/funds/ticker")
      .then((r) => r.json())
      .then((data) => {
        if (!data || !data.system_metrics) return;
        const navMetric = data.metrics?.find((m) => m.label === "MF NAV");
        if (navMetric?.last_updated) {
          const ts = new Date(navMetric.last_updated);
          const formatted = ts.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
          setProofStats((prev) => [
            prev[0],
            prev[1],
            prev[2],
            [formatted, "last NAV refresh", "Live NAV data sourced daily from MFapi and NSE.", ""],
          ]);
        }
      })
      .catch(() => {
        // Silently fall back to default static stats
      });
  }, []);

  return (
    <main className="landing-editorial relative min-h-screen overflow-x-hidden bg-[var(--bg-base)] text-[var(--text-primary)]  selection:bg-[var(--accent-crimson)] selection:text-[var(--bg-base)]">
      <NoiseOverlay />

      <EcosystemHeader currentApp="none" />

      <HeroWave 
        title={<>Research funds <br /><span className="bg-gradient-to-r from-white via-white/80 to-[#00FF9D] bg-clip-text text-transparent opacity-90 mix-blend-lighten">with evidence</span></>}
        subtitle="Compare Indian mutual funds with deterministic metrics, official-source evidence, and visible data limits."
        onPromptSubmit={(query) => {
          router.push(`/dashboard?query=${encodeURIComponent(query)}`);
        }}
        ticker={<LiveDataTicker />}
      >
        <PromptChips onSelect={(chip) => router.push(`/dashboard?query=${encodeURIComponent(chip)}`)} />
      </HeroWave>

      {/* Interactive Sandbox Hero Component */}
      <InteractiveHeroSandbox />

      <DataTrailRibbon />

      <section id="flow" className="relative mx-auto w-full max-w-[1500px] px-5 py-24 sm:px-8 lg:py-32">
        <div className="relative mb-12 text-center z-10">
          <AmbientGlow className="left-1/2 top-0 h-[300px] w-[300px] -translate-x-1/2" color="rgba(102, 163, 255, 0.1)" />
          <MetadataLabel className="text-[var(--accent-glow)] mx-auto relative z-10">Integrated Support</MetadataLabel>
          <h2 className="mt-8 font-sans text-4xl sm:text-6xl lg:text-7xl font-bold leading-[1.05] tracking-tight text-white relative z-10">
            Supported AMC&apos;s
          </h2>
        </div>
        
        <AMCCoverageMarquee />
      </section>

      <SampleComparison />

      <AMCCoverageMatrix />

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

      <section id="data-trust" className="relative border-y border-white/10 bg-white/[0.01]">
        <div className="relative z-10 mx-auto grid w-full max-w-[1500px] gap-12 px-5 py-24 sm:px-8 lg:grid-cols-[0.46fr_0.54fr] lg:py-32">
          <Reveal>
            <MetadataLabel className="text-[var(--accent-glow)]">Data &amp; Trust</MetadataLabel>
            <h2 className="mt-8 font-sans text-[10.5vw] font-bold leading-[1.05] tracking-tight text-white sm:text-[8vw] lg:text-[4.6vw]">
              Know what is ready.
            </h2>
            <p className="mt-6 max-w-xl text-sm leading-7 text-[var(--text-muted)]">
              FundersAI keeps discovery, acquisition, parsing, and validated runtime data separate.
              Status labels explain freshness and gaps instead of turning pipeline activity into a false claim of readiness.
            </p>
            <div className="mt-10">
              <EditorialButton href="/dashboard/data-trust">Open Data &amp; Trust</EditorialButton>
            </div>
          </Reveal>

          <Reveal className="grid gap-4 sm:grid-cols-2">
            {[
              ["MF NAV", "FRESH", "Checked against the latest expected business day."],
              ["AMC docs", "PROCESSING", "New official documents can be in progress without changing current answers."],
              ["Missing fields", "SHOWN", "Unavailable fields stay visible and out of unsupported conclusions."],
              ["Claim sources", "LINKED", "Official-document evidence stays directly beneath supported answers."],
            ].map(([label, value, body]) => (
              <div key={label} className="group rounded-2xl border border-white/10 bg-white/[0.025] p-6 backdrop-blur-md transition hover:border-white/20 hover:bg-white/[0.045]">
                <MetadataLabel>{label}</MetadataLabel>
                <p className="mt-6 text-2xl font-semibold text-[#00FF9D]">{value}</p>
                <p className="mt-4 text-sm leading-6 text-[var(--text-muted)]">{body}</p>
              </div>
            ))}
          </Reveal>
        </div>
      </section>

      <section id="workspace" className="relative bg-white/[0.01]">
        <div className="relative z-10 mx-auto grid w-full max-w-[1500px] gap-12 px-5 py-24 sm:px-8 lg:grid-cols-[0.28fr_0.72fr] lg:py-32">
          <div>
            <div className="lg:sticky lg:top-32">
              <MetadataLabel className="text-[var(--accent-glow)]">Comparison workspace</MetadataLabel>
              <h2 className="mt-8 font-sans text-[10.5vw] font-bold leading-[1.05] tracking-tight text-white sm:text-[8vw] lg:text-[4.8vw]">
                More than a chat interface.
              </h2>
              <p className="mt-6 text-sm leading-7 text-[var(--text-muted)]">
                The product surface keeps source-backed research, intent-driven comparison, and guardrails visible together.
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
          <MetadataLabel className="text-[var(--accent-glow)]">What&apos;s inside</MetadataLabel>
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

      <section id="pricing" className="relative border-t border-white/10 bg-white/[0.01]">
        <div className="relative z-10 mx-auto w-full max-w-[1500px] px-5 py-24 sm:px-8 lg:py-32">
          <Reveal className="text-center max-w-3xl mx-auto mb-16">
            <MetadataLabel className="text-[var(--accent-glow)]">Pricing &amp; Plans</MetadataLabel>
            <h2 className="mt-8 font-sans text-[10.5vw] font-bold leading-[1.05] tracking-tight text-white sm:text-[8vw] lg:text-[4.6vw]">
              Simple, transparent pricing.
            </h2>
            <p className="mt-6 text-sm leading-7 text-[var(--text-muted)]">
              Unified subscriptions covering both Research Platform AI tokens and Synthesis Studio comparison reports.
            </p>
          </Reveal>

          <div className="grid gap-8 md:grid-cols-3 max-w-6xl mx-auto">
            {/* Free */}
            <Reveal className="flex flex-col justify-between rounded-3xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-md">
              <div className="space-y-6">
                <div>
                  <MetadataLabel>Free Tier</MetadataLabel>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-5xl font-bold text-white">₹0</span>
                    <span className="text-sm text-[var(--text-muted)]">/ forever</span>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-[var(--text-muted)]">Starter research limits for fund research &amp; synthesis reports.</p>
                </div>
                <div className="space-y-3 border-t border-white/10 pt-6">
                  <div className="flex items-center gap-3 text-sm text-white">
                    <span className="text-[#00FF9D] font-bold">✓</span>
                    <span><strong>1 report per day</strong> (Synthesis Studio)</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-white">
                    <span className="text-[#00FF9D] font-bold">✓</span>
                    <span>Token-based queries in Research platform</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                    <span className="text-[#00FF9D] font-bold">✓</span>
                    <span>25k daily / 100k monthly AI tokens</span>
                  </div>
                </div>
              </div>
              <div className="mt-8">
                <Link href="/login" className="flex w-full items-center justify-center rounded-full border border-white/20 bg-white/5 py-3 text-sm font-semibold text-white backdrop-blur-md transition hover:bg-white/10">
                  Start Free
                </Link>
              </div>
            </Reveal>

            {/* Pro */}
            <Reveal className="relative flex flex-col justify-between rounded-3xl border border-[#00FF9D]/40 bg-white/[0.04] p-8 backdrop-blur-md shadow-2xl shadow-[rgba(0,255,157,0.08)]">
              <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-[#00FF9D] px-4 py-1 text-[10px] font-bold uppercase tracking-wider text-black">
                Most Popular
              </div>
              <div className="space-y-6">
                <div>
                  <MetadataLabel className="text-[#00FF9D]">Pro Tier</MetadataLabel>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-5xl font-bold text-white">₹99</span>
                    <span className="text-sm text-[var(--text-muted)]">/ month</span>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-[var(--text-muted)]">Higher limits for regular mutual-fund and stock research.</p>
                </div>
                <div className="space-y-3 border-t border-white/10 pt-6">
                  <div className="flex items-center gap-3 text-sm text-white">
                    <span className="text-[#00FF9D] font-bold">✓</span>
                    <span><strong>5 reports per day</strong> (Synthesis Studio)</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-white">
                    <span className="text-[#00FF9D] font-bold">✓</span>
                    <span><strong>10X Higher usage</strong> in Research platform</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                    <span className="text-[#00FF9D] font-bold">✓</span>
                    <span>250k daily / 2M monthly AI tokens</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                    <span className="text-[#00FF9D] font-bold">✓</span>
                    <span>Dashboard, Canvas &amp; Overlap Tool</span>
                  </div>
                </div>
              </div>
              <div className="mt-8">
                <Link href="/billing" className="flex w-full items-center justify-center rounded-full bg-[#00FF9D] py-3 text-sm font-bold text-black transition hover:bg-[#00FF9D]/90 shadow-lg shadow-[#00FF9D]/20">
                  Upgrade to Pro (₹99)
                </Link>
              </div>
            </Reveal>

            {/* Ultra */}
            <Reveal className="flex flex-col justify-between rounded-3xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-md">
              <div className="space-y-6">
                <div>
                  <MetadataLabel className="text-blue-400">Ultra Tier</MetadataLabel>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-5xl font-bold text-white">₹199</span>
                    <span className="text-sm text-[var(--text-muted)]">/ month</span>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-[var(--text-muted)]">Highest limits for heavy institutional research workflows.</p>
                </div>
                <div className="space-y-3 border-t border-white/10 pt-6">
                  <div className="flex items-center gap-3 text-sm text-white">
                    <span className="text-blue-400 font-bold">✓</span>
                    <span><strong>15 reports per day</strong> (Synthesis Studio)</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-white">
                    <span className="text-blue-400 font-bold">✓</span>
                    <span><strong>25X Higher usage than Free</strong> in Research</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                    <span className="text-blue-400 font-bold">✓</span>
                    <span>750k daily / 6M monthly AI tokens</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                    <span className="text-blue-400 font-bold">✓</span>
                    <span>Priority serverless PDF export &amp; budget</span>
                  </div>
                </div>
              </div>
              <div className="mt-8">
                <Link href="/billing" className="flex w-full items-center justify-center rounded-full border border-blue-500/40 bg-blue-500/10 py-3 text-sm font-semibold text-white backdrop-blur-md transition hover:bg-blue-500/20">
                  Upgrade to Ultra (₹199)
                </Link>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      <section className="relative w-full border-t border-white/10 overflow-hidden bg-[var(--bg-base)]">
        <AmbientGlow className="left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2" color="rgba(0, 255, 157, 0.15)" />
        <div className="relative z-10 mx-auto w-full max-w-[1500px] px-5 py-32 sm:px-8 lg:py-48 text-center">
          <Reveal>
            <h2 className="font-sans text-5xl sm:text-7xl lg:text-8xl font-bold tracking-tight text-white mb-8 drop-shadow-2xl">
              Start your <br className="hidden sm:block" />research.
            </h2>
            <p className="text-xl sm:text-2xl text-white/60 mb-12 max-w-2xl mx-auto leading-relaxed">
              Start with a research question, then inspect the metrics, sources, and limits yourself.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/login" className="inline-flex items-center justify-center rounded-full bg-[#00FF9D] px-8 py-4 text-base font-bold text-black transition-all hover:scale-105 hover:bg-[#00FF9D]/90 hover:shadow-[0_0_40px_rgba(0,255,157,0.4)]">
                Get Started Free
              </Link>
              <Link href="#pricing" className="inline-flex items-center justify-center rounded-full border border-white/20 bg-white/5 px-8 py-4 text-base font-bold text-white transition-all hover:bg-white/10">
                View Pricing Plans
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      <PublicFooter />
    </main>
  );
}
