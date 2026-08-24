"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  BarChart3,
  ShieldCheck,
  Search,
  ArrowUpRight,
  Zap
} from "lucide-react";
import { supabaseBrowser } from "@/lib/supabaseBrowser";
import { FUND_REGISTRY } from "@/lib/fund-registry";

// The Synthesis product has no separate "home" for signed-in users — logged-out
// visitors see the marketing landing page, logged-in users should land straight
// in the studio instead of being routed back through the pitch.
const SYNTHESIS_LANDING_HREF = "/synthesis";
const SYNTHESIS_STUDIO_HREF = "/synthesis/generate";

interface EcosystemHeaderProps {
  currentApp?: "research" | "synthesis" | "datatrust" | "mutual-funds" | "tools" | "none";
  /** Destination for the Data & Trust pill. Public pages use the default public portal;
   *  authenticated app shells should point at their own live status page. */
  dataTrustHref?: string;
  /** Rendered before the logo — e.g. a sidebar trigger inside an authenticated app shell. */
  leading?: React.ReactNode;
  /** Replaces the default global-search trigger button, e.g. an app-specific inline search box. */
  centerSlot?: React.ReactNode;
  /** Replaces the default Sign In / Launch App buttons, e.g. tier upgrade + status + theme toggle. */
  trailing?: React.ReactNode;
  /** Override the header's inner container width/padding. Defaults to a centered max-w-7xl for
   *  marketing/content pages; authenticated app shells pass a full-bleed value to match the shell below. */
  containerClassName?: string;
}

export function EcosystemHeader({
  currentApp = "none",
  dataTrustHref = "/data-trust",
  leading,
  centerSlot,
  trailing,
  containerClassName = "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
}: EcosystemHeaderProps) {
  const [commandOpen, setCommandOpen] = useState(false);
  const [activeTab] = useState<string>(currentApp);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Synthesis gets its own mark; every other surface (Research, Data & Trust,
  // marketing pages) uses the main FundersAI wordmark.
  const isSynthesis = currentApp === "synthesis";
  const logoSrc = isSynthesis ? "/Synthesis_FUNDERSAI.png" : "/FUNDERSAI-nobackground.png";
  const logoAlt = isSynthesis ? "Synthesis by FundersAI" : "FundersAI";
  const logoCaption = isSynthesis ? "Synthesis Studio" : "Research Ecosystem";

  // Logged-in users skip the Synthesis pitch page and land directly in the studio.
  const synthesisHref = isAuthenticated ? SYNTHESIS_STUDIO_HREF : SYNTHESIS_LANDING_HREF;

  const [rememberedLanding, setRememberedLanding] = useState<string>("/");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("fundersai_last_landing");
      if (saved) setRememberedLanding(saved);
    } catch {}
  }, []);

  // The logo returns to the Synthesis landing page (/synthesis) if in Synthesis,
  // or to the user's remembered landing page (/ or /synthesis).
  const logoHref = isSynthesis ? "/synthesis" : rememberedLanding;

  // Keyboard shortcut listener for Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Track auth state so the Synthesis Studio switcher and logo can route
  // signed-in users straight into the studio instead of the marketing landing page.
  useEffect(() => {
    let isActive = true;
    supabaseBrowser.auth.getUser().then(({ data }) => {
      if (isActive) setIsAuthenticated(!!data.user);
    });
    const { data: listener } = supabaseBrowser.auth.onAuthStateChange((_event, session) => {
      setIsAuthenticated(!!session?.user);
    });
    return () => {
      isActive = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  const [searchQuery, setSearchQuery] = useState("");

  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) {
      return {
        tools: [
          { name: "Mutual Fund Screener & Metric Explorer", href: "/mutual-funds", type: "Directory" },
          { name: "Mutual Fund Portfolio Overlap Calculator", href: "/tools/portfolio-overlap", type: "Calculator" },
          { name: "Mutual Fund SIP & Step-Up Calculator", href: "/tools/sip-calculator", type: "Calculator" },
        ],
        funds: FUND_REGISTRY.slice(0, 4),
        comparisons: [
          { label: "Parag Parikh Flexi Cap vs HDFC Flexi Cap", href: "/compare/parag-parikh-flexi-cap-vs-hdfc-flexi-cap" },
          { label: "Quant Small Cap vs Nippon India Small Cap", href: "/compare/quant-small-cap-vs-nippon-india-small-cap" },
          { label: "SBI Bluechip vs ICICI Prudential Bluechip", href: "/compare/sbi-bluechip-vs-icici-prudential-bluechip" },
        ]
      };
    }

    const matchedFunds = FUND_REGISTRY.filter(
      (f) =>
        f.schemeName.toLowerCase().includes(q) ||
        f.amcName.toLowerCase().includes(q) ||
        f.category.toLowerCase().includes(q) ||
        String(f.schemeCode).includes(q)
    ).slice(0, 6);

    const publicTools = [
      { name: "Portfolio Overlap Calculator", href: "/tools/portfolio-overlap", type: "Tool", desc: "Compare fund holdings overlap" },
      { name: "SIP & Compounding Calculator", href: "/tools/sip-calculator", type: "Tool", desc: "Calculate future corpus & step-up SIP" },
      { name: "Mutual Fund Directory & Screener", href: "/mutual-funds", type: "Directory", desc: "Screen 30+ funds by AMC and category" },
      { name: "Data & Trust Methodology Portal", href: "/data-trust", type: "Portal", desc: "Deterministic metrics & SEBI compliance" },
    ].filter(t => t.name.toLowerCase().includes(q) || t.desc.toLowerCase().includes(q));

    return {
      tools: publicTools,
      funds: matchedFunds,
      comparisons: []
    };
  }, [searchQuery]);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-[#07080C]/80 backdrop-blur-xl transition-all">
      <div className={`${containerClassName} h-16 flex items-center justify-between gap-4`}>

        {/* Brand Logo & Product Identifier */}
        <div className="flex items-center gap-3 min-w-0">
          {leading}
          <Link href={logoHref} className="flex items-center gap-2.5 group shrink-0">
            <Image
              src={logoSrc}
              alt={logoAlt}
              width={isSynthesis ? 160 : 800}
              height={160}
              priority
              className={isSynthesis ? "h-9 w-9 object-contain" : "h-8 w-auto object-contain"}
            />
            <span className="text-[10px] text-slate-400 font-mono tracking-wider uppercase whitespace-nowrap">{logoCaption}</span>
          </Link>

          {/* Ecosystem Navigation Switcher Pill */}
          <nav className="hidden lg:flex items-center p-1 bg-slate-900/80 border border-white/10 rounded-full text-xs font-medium">
            <Link
              href="/mutual-funds"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-all ${
                activeTab === "mutual-funds"
                  ? "bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <span>Mutual Funds</span>
            </Link>

            <Link
              href="/tools"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-all ${
                activeTab === "tools"
                  ? "bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <span>Tools</span>
              <span className="text-[9px] px-1.5 py-0.2 bg-blue-950 text-blue-300 rounded-full font-mono font-bold">New</span>
            </Link>

            <Link
              href="/dashboard"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-all ${
                activeTab === "research"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Research</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </Link>

            <Link
              href={synthesisHref}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-all ${
                activeTab === "synthesis" 
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm" 
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              <span>Synthesis</span>
              <span className="text-[9px] px-1.5 py-0.2 bg-cyan-950 text-cyan-400 rounded-full font-mono font-bold">AI</span>
            </Link>

            <Link
              href={dataTrustHref}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-all ${
                activeTab === "datatrust"
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm" 
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
              <span>Data & Trust</span>
            </Link>
          </nav>
        </div>

        {/* Global Search Command Bar Trigger & User Passport */}
        <div className="flex items-center gap-3 min-w-0">
          {centerSlot ?? (
            <button
              onClick={() => {
                setCommandOpen(true);
                setSearchQuery("");
              }}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-slate-900/60 border border-white/10 hover:border-white/20 rounded-lg text-slate-400 text-xs transition-all group"
            >
              <Search className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-400 transition-colors" />
              <span>Search stocks or funds...</span>
              <kbd className="ml-2 px-1.5 py-0.5 text-[10px] font-mono bg-slate-800 text-slate-400 border border-white/10 rounded">⌘K</kbd>
            </button>
          )}

          {trailing ?? (
            <>
              <Link
                href="/login"
                className="hidden sm:inline-flex items-center px-2 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
              >
                Sign In
              </Link>

              <Link
                href="/dashboard"
                className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-lg shadow-lg shadow-emerald-950/40 border border-emerald-400/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <span>Launch App</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Global Cmd+K Search Modal Backdrop */}
      <AnimatePresence>
        {commandOpen && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-start justify-center pt-20 px-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              className="w-full max-w-xl bg-[#0b111e] border border-white/15 rounded-2xl shadow-2xl overflow-hidden"
            >
              <div className="flex items-center px-4 py-3.5 border-b border-white/10 bg-black/40">
                <Search className="w-4 h-4 text-emerald-400 mr-2.5 shrink-0" />
                <input
                  type="text"
                  placeholder="Search 30+ funds, tools, categories, or AMFI codes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-transparent text-white text-sm focus:outline-none placeholder-slate-500"
                  autoFocus
                />
                <button 
                  onClick={() => setCommandOpen(false)}
                  className="text-xs text-slate-500 hover:text-slate-300 font-mono px-2 py-1 bg-slate-900 border border-white/10 rounded ml-2"
                >
                  ESC
                </button>
              </div>

              <div className="p-3 space-y-3 max-h-96 overflow-y-auto">
                {/* Tools & Hubs */}
                {searchResults.tools.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-blue-400 px-2 font-bold">Tools &amp; Portals</div>
                    {searchResults.tools.map((t) => (
                      <Link
                        key={t.href}
                        href={t.href}
                        onClick={() => setCommandOpen(false)}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5 border border-transparent hover:border-white/10 transition-all group"
                      >
                        <div className="flex items-center gap-2">
                          <Zap className="w-3.5 h-3.5 text-blue-400" />
                          <span className="text-xs font-semibold text-slate-200 group-hover:text-white">{t.name}</span>
                        </div>
                        <span className="text-[9px] text-blue-300 font-mono bg-blue-950/80 px-2 py-0.5 rounded border border-blue-800/40">
                          {t.type}
                        </span>
                      </Link>
                    ))}
                  </div>
                )}

                {/* Matched Funds */}
                {searchResults.funds.length > 0 && (
                  <div className="space-y-1 pt-1 border-t border-white/5">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 px-2 font-bold">Mutual Funds</div>
                    {searchResults.funds.map((f) => (
                      <Link
                        key={f.schemeCode}
                        href={`/mutual-funds/${f.amcSlug}/${f.fundSlug}`}
                        onClick={() => setCommandOpen(false)}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5 border border-transparent hover:border-white/10 transition-all group"
                      >
                        <div className="truncate pr-2">
                          <p className="text-xs font-medium text-white group-hover:text-emerald-300 truncate">{f.schemeName}</p>
                          <p className="text-[10px] text-slate-400 font-mono">{f.amcName} • AMFI {f.schemeCode}</p>
                        </div>
                        <span className="text-[10px] text-emerald-400 font-mono bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40 shrink-0">
                          {f.category}
                        </span>
                      </Link>
                    ))}
                  </div>
                )}

                {/* Popular Comparisons */}
                {searchResults.comparisons.length > 0 && (
                  <div className="space-y-1 pt-1 border-t border-white/5">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-purple-400 px-2 font-bold">Trending Duels</div>
                    {searchResults.comparisons.map((c) => (
                      <Link 
                        key={c.href}
                        href={c.href} 
                        onClick={() => setCommandOpen(false)}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5 border border-transparent hover:border-white/10 transition-all group"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-purple-400 text-[10px] font-mono font-bold">VS</span>
                          <span className="text-xs font-medium text-slate-200 group-hover:text-white">{c.label}</span>
                        </div>
                        <span className="text-[10px] text-purple-300 font-mono bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/40">
                          Head-to-Head
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </header>
  );
}
