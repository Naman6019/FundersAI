"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  BarChart3,
  Home,
  Menu,
  ShieldCheck,
  X,
  Search,
  ArrowUpRight,
  Zap
} from "lucide-react";
import { supabaseBrowser } from "@/lib/supabaseBrowser";
import { FUND_REGISTRY } from "@/lib/fund-registry";
import { useEcosystemHref } from "@/lib/ecosystem-origin";

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
  containerClassName = "max-w-[1560px] mx-auto px-4 sm:px-6 lg:px-8",
}: EcosystemHeaderProps) {
  const [commandOpen, setCommandOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const mobileNavRef = useRef<HTMLDivElement | null>(null);
  const mobileNavTriggerRef = useRef<HTMLButtonElement | null>(null);
  const activeTab = currentApp;
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Synthesis gets its own mark; every other surface (Research, Data & Trust,
  // marketing pages) uses the main FundersAI wordmark.
  const isSynthesis = currentApp === "synthesis";
  const logoSrc = isSynthesis ? "/Synthesis_FUNDERSAI.png" : "/FUNDERSAI-nobackground.png";
  const logoAlt = isSynthesis ? "Synthesis by FundersAI" : "FundersAI";
  const logoCaption = isSynthesis ? "Synthesis Studio" : "Research Ecosystem";

  // Logged-in users skip the Synthesis pitch page and land directly in the studio.
  const synthesisHref = isAuthenticated ? SYNTHESIS_STUDIO_HREF : SYNTHESIS_LANDING_HREF;

  // The brand mark always leaves for the ecosystem home, including from inside
  // Synthesis, where a relative "/" would be rewritten straight back to /synthesis.
  const ecosystemHref = useEcosystemHref();
  const homeHref = ecosystemHref("/");

  const navItems = useMemo(
    () => [
      {
        key: "home",
        label: "Home",
        href: homeHref,
        icon: <Home className="w-3.5 h-3.5" />,
        adornment: null,
        activeClass: "bg-surface-hover text-white border border-line-strong shadow-sm",
      },
      {
        key: "mutual-funds",
        label: "Mutual Funds",
        href: ecosystemHref("/mutual-funds"),
        icon: null,
        adornment: null,
        activeClass:
          "bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm",
      },
      {
        key: "tools",
        label: "Tools",
        href: ecosystemHref("/tools"),
        icon: null,
        adornment: (
          <span className="text-[9px] px-1.5 py-0.2 bg-blue-950 text-blue-300 rounded-full font-mono font-bold">
            New
          </span>
        ),
        activeClass: "bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow-sm",
      },
      {
        key: "research",
        label: "Research",
        href: ecosystemHref("/research"),
        icon: <BarChart3 className="w-3.5 h-3.5" />,
        adornment: <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />,
        activeClass:
          "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm",
      },
      {
        key: "synthesis",
        label: "Synthesis",
        href: synthesisHref,
        icon: <Zap className="w-3.5 h-3.5 text-accent-synthesis" />,
        adornment: (
          <span className="text-[9px] px-1.5 py-0.2 bg-violet-950 text-accent-synthesis rounded-full font-mono font-bold">
            AI
          </span>
        ),
        activeClass: "bg-accent-synthesis/20 text-violet-300 border border-accent-synthesis/40 shadow-sm",
      },
      {
        key: "datatrust",
        label: "Data & Trust",
        href: ecosystemHref(dataTrustHref),
        icon: <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />,
        adornment: null,
        activeClass: "bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm",
      },
    ],
    [homeHref, synthesisHref, dataTrustHref, ecosystemHref],
  );

  // The drawer is a modal surface, so it has to behave like one: Escape closes it, the
  // page behind it must not scroll (or the body scrolls under the panel on iOS), and
  // focus has to move inside and stay there — `aria-modal` promises that to assistive
  // tech, and without it a keyboard user tabs through the page hidden behind the panel.
  useEffect(() => {
    if (!mobileNavOpen) return;

    const panel = mobileNavRef.current;
    const trigger = mobileNavTriggerRef.current;
    const tabbable = () =>
      Array.from(
        panel?.querySelectorAll<HTMLElement>("a[href], button:not([disabled])") ?? [],
      ).filter((el) => el.offsetParent !== null);

    tabbable()[0]?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileNavOpen(false);
        return;
      }
      if (e.key !== "Tab") return;

      const items = tabbable();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      // Deferred a frame: the panel is still unmounting via its exit animation, and
      // focusing during that commit is dropped when the focused node is removed.
      requestAnimationFrame(() => trigger?.focus());
    };
  }, [mobileNavOpen]);

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
          { name: "FundersAI Home", href: homeHref, type: "Ecosystem" },
          { name: "Research Workspace", href: ecosystemHref("/research"), type: "Workspace" },
          { name: "Synthesis Studio", href: "/synthesis", type: "Studio" },
          { name: "Mutual Fund Screener & Explorer", href: ecosystemHref("/mutual-funds"), type: "Directory" },
          { name: "Portfolio Overlap Calculator", href: ecosystemHref("/tools/portfolio-overlap"), type: "Calculator" },
          { name: "SIP & Step-Up Calculator", href: ecosystemHref("/tools/sip-calculator"), type: "Calculator" },
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

    const contentPages = [
      { name: "Methodology Hub", href: ecosystemHref("/methodology"), type: "Reference", desc: "How every metric is calculated and sourced" },
      { name: "How It Works", href: ecosystemHref("/how-it-works"), type: "Reference", desc: "The deterministic pipeline end to end" },
      { name: "Learn", href: ecosystemHref("/learn"), type: "Guides", desc: "Investing concepts and metric explainers" },
      { name: "Pricing & Plans", href: ecosystemHref("/pricing"), type: "Account", desc: "Free, Pro and Ultra research limits" },
      { name: "About FundersAI", href: ecosystemHref("/about"), type: "Company", desc: "What FundersAI is and is not" },
      { name: "Contact Support", href: ecosystemHref("/contact"), type: "Company", desc: "Reach the team" },
    ];

    const publicTools = [
      { name: "FundersAI Home", href: homeHref, type: "Ecosystem", desc: "Ecosystem hub — Research, Synthesis and free tools" },
      { name: "Research Workspace", href: ecosystemHref("/research"), type: "Workspace", desc: "Quantitative AI evidence & market analysis" },
      { name: "Synthesis Studio", href: "/synthesis", type: "Studio", desc: "Autonomous multi-agent fund factsheet reports" },
      { name: "Portfolio Overlap Calculator", href: ecosystemHref("/tools/portfolio-overlap"), type: "Tool", desc: "Compare fund holdings overlap" },
      { name: "SIP & Compounding Calculator", href: ecosystemHref("/tools/sip-calculator"), type: "Tool", desc: "Calculate future corpus & step-up SIP" },
      { name: "Mutual Fund Directory & Screener", href: ecosystemHref("/mutual-funds"), type: "Directory", desc: "Screen 30+ funds by AMC and category" },
      { name: "Data & Trust Methodology Portal", href: ecosystemHref("/data-trust"), type: "Portal", desc: "Deterministic metrics & SEBI compliance" },
    ].filter(t => t.name.toLowerCase().includes(q) || t.desc.toLowerCase().includes(q));

    const matchedContent = contentPages.filter(
      (t) => t.name.toLowerCase().includes(q) || t.desc.toLowerCase().includes(q),
    );

    return {
      tools: [...publicTools, ...matchedContent],
      funds: matchedFunds,
      comparisons: []
    };
  }, [searchQuery, homeHref, ecosystemHref]);

  return (
    <>
      {/* First tab stop on every page: the header has ~15 focusable controls before the
          content starts, which is a long way to tab past on each navigation. */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[70] focus:px-4 focus:py-2.5 focus:rounded-lg focus:bg-primary focus:text-primary-foreground focus:font-bold focus:text-sm focus:shadow-lg"
      >
        Skip to content
      </a>

      <header className="sticky top-0 z-50 w-full border-b border-line bg-background/80 backdrop-blur-xl transition-all">
        <div className={`${containerClassName} h-16 flex items-center justify-between gap-4`}>

          {/* Brand Logo & Product Identifier */}
          <div className="flex items-center gap-3 min-w-0">
            {leading}
            <Link href={homeHref} className="flex items-center gap-2.5 group shrink-0">
              <Image
                src={logoSrc}
                alt={logoAlt}
                width={isSynthesis ? 160 : 800}
                height={160}
                priority
                className={isSynthesis ? "h-9 w-9 object-contain" : "h-8 w-auto object-contain"}
              />
              <span className="hidden 2xl:inline text-[10px] text-text-2 font-mono tracking-wider uppercase whitespace-nowrap">{logoCaption}</span>
            </Link>

            {/* Ecosystem Navigation Switcher Pill (desktop) */}
            <nav className="hidden xl:flex shrink-0 items-center p-1 bg-surface-1 border border-line rounded-full text-xs font-medium">
              {navItems.map((item) => (
                <Link
                  key={item.key}
                  href={item.href}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-full transition-all ${
                    activeTab === item.key
                      ? item.activeClass
                      : "text-text-2 hover:text-text-1 hover:bg-surface-1"
                  }`}
                >
                  {item.icon}
                  <span className="whitespace-nowrap">{item.label}</span>
                  {item.adornment}
                </Link>
              ))}
            </nav>
          </div>

          {/* Global Search Command Bar Trigger & User Passport */}
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => {
                setCommandOpen(true);
                setSearchQuery("");
              }}
              aria-label="Search stocks or funds"
              className="2xl:hidden flex items-center justify-center w-9 h-9 rounded-lg bg-surface-1 border border-line text-text-2 hover:text-white hover:border-line-strong transition-all"
            >
              <Search className="w-4 h-4" />
            </button>

            <button
              ref={mobileNavTriggerRef}
              type="button"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open navigation menu"
              aria-expanded={mobileNavOpen}
              aria-controls="ecosystem-mobile-nav"
              className="xl:hidden flex items-center justify-center w-9 h-9 rounded-lg bg-surface-1 border border-line text-text-2 hover:text-white hover:border-line-strong transition-all"
            >
              <Menu className="w-4 h-4" />
            </button>

            {centerSlot ?? (
              <button
                onClick={() => {
                  setCommandOpen(true);
                  setSearchQuery("");
                }}
                className="hidden 2xl:flex items-center gap-2 px-3 py-1.5 bg-surface-1 border border-line hover:border-line-strong rounded-lg text-text-2 text-xs transition-all group shrink-0"
              >
                <Search className="w-3.5 h-3.5 text-text-2 group-hover:text-emerald-400 transition-colors" />
                <span className="whitespace-nowrap">Search stocks or funds...</span>
                <kbd className="ml-2 px-1.5 py-0.5 text-[10px] font-mono bg-surface-2 text-text-2 border border-line rounded">⌘K</kbd>
              </button>
            )}

            {trailing ?? (
              <>
                <Link
                  href={ecosystemHref("/login")}
                  className="hidden md:inline-flex items-center px-2 py-1.5 text-xs font-medium text-text-2 hover:text-text-1 transition-colors shrink-0"
                >
                  Sign In
                </Link>

                <Link
                  href={ecosystemHref("/dashboard")}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-lg shadow-lg shadow-emerald-950/40 border border-emerald-400/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
                >
                  <span>Launch App</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Skip-link landing point. Lives here rather than as an id on each page's <main>,
          so every surface that renders the header gets a working skip target for free. */}
      <div id="main-content" tabIndex={-1} className="outline-none" />

        {/* Mobile Navigation Drawer — below lg the switcher pill is hidden, and without
            this the only controls on the header are the logo and Launch App. */}
        <AnimatePresence>
          {mobileNavOpen && (
            <div className="xl:hidden fixed inset-0 z-[60]">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                onClick={() => setMobileNavOpen(false)}
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
              />

              <motion.div
                ref={mobileNavRef}
              id="ecosystem-mobile-nav"
                role="dialog"
                aria-modal="true"
                aria-label="Site navigation"
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "spring", damping: 30, stiffness: 300 }}
                className="absolute right-0 top-0 h-full w-[85%] max-w-sm bg-surface-2 border-l border-line shadow-2xl flex flex-col"
              >
                <div className="flex items-center justify-between px-5 h-16 border-b border-line shrink-0">
                  <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-text-3">
                    Navigate
                  </span>
                  <button
                    type="button"
                    onClick={() => setMobileNavOpen(false)}
                    aria-label="Close navigation menu"
                    className="flex items-center justify-center w-9 h-9 rounded-lg border border-line text-text-2 hover:text-white hover:border-line-strong transition-all"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <nav className="flex-1 overflow-y-auto p-4 space-y-1.5">
                  {navItems.map((item) => (
                    <Link
                      key={item.key}
                      href={item.href}
                      onClick={() => setMobileNavOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm font-semibold transition-all ${
                        activeTab === item.key
                          ? item.activeClass
                          : "text-text-2 border border-transparent hover:bg-surface-1 hover:text-white"
                      }`}
                    >
                      {item.icon}
                      <span className="flex-1 whitespace-nowrap">{item.label}</span>
                      {item.adornment}
                    </Link>
                  ))}
                </nav>

                <div className="p-4 border-t border-line space-y-2.5 shrink-0">
                  <button
                    type="button"
                    onClick={() => {
                      setMobileNavOpen(false);
                      setCommandOpen(true);
                      setSearchQuery("");
                    }}
                    className="w-full flex items-center gap-2 px-4 py-3 bg-surface-1 border border-line rounded-xl text-text-2 text-sm transition-all hover:border-line-strong"
                  >
                    <Search className="w-4 h-4 text-emerald-400" />
                    <span className="whitespace-nowrap">Search stocks or funds...</span>
                  </button>

                  {!isAuthenticated && (
                    <Link
                      href={ecosystemHref("/login")}
                      onClick={() => setMobileNavOpen(false)}
                      className="w-full flex items-center justify-center px-4 py-3 rounded-xl border border-line text-sm font-semibold text-text-2 hover:text-white hover:bg-surface-1 transition-all"
                    >
                      Sign In
                    </Link>
                  )}

                  <Link
                    href={ecosystemHref("/dashboard")}
                    onClick={() => setMobileNavOpen(false)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-600 rounded-xl border border-emerald-400/30 transition-all"
                  >
                    <span>Launch App</span>
                    <ArrowUpRight className="w-4 h-4" />
                  </Link>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        {/* Global Cmd+K Search Modal Backdrop */}
        <AnimatePresence>
          {commandOpen && (
            <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-start justify-center pt-20 px-4">
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: -10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -10 }}
                className="w-full max-w-xl bg-surface-2 border border-line-strong rounded-2xl shadow-2xl overflow-hidden"
              >
                <div className="flex items-center px-4 py-3.5 border-b border-line bg-black/40">
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
                    className="text-xs text-text-3 hover:text-text-2 font-mono px-2 py-1 bg-surface-2 border border-line rounded ml-2"
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
                          className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-1 border border-transparent hover:border-line transition-all group"
                        >
                          <div className="flex items-center gap-2">
                            <Zap className="w-3.5 h-3.5 text-blue-400" />
                            <span className="text-xs font-semibold text-text-1 group-hover:text-white">{t.name}</span>
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
                    <div className="space-y-1 pt-1 border-t border-line">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 px-2 font-bold">Mutual Funds</div>
                      {searchResults.funds.map((f) => (
                        <Link
                          key={f.schemeCode}
                          href={ecosystemHref(`/mutual-funds/${f.amcSlug}/${f.fundSlug}`)}
                          onClick={() => setCommandOpen(false)}
                          className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-1 border border-transparent hover:border-line transition-all group"
                        >
                          <div className="truncate pr-2">
                            <p className="text-xs font-medium text-white group-hover:text-emerald-300 truncate">{f.schemeName}</p>
                            <p className="text-[10px] text-text-2 font-mono">{f.amcName} • AMFI {f.schemeCode}</p>
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
                    <div className="space-y-1 pt-1 border-t border-line">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-purple-400 px-2 font-bold">Trending Duels</div>
                      {searchResults.comparisons.map((c) => (
                        <Link
                          key={c.href}
                          href={ecosystemHref(c.href)}
                          onClick={() => setCommandOpen(false)}
                          className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-1 border border-transparent hover:border-line transition-all group"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-purple-400 text-[10px] font-mono font-bold">VS</span>
                            <span className="text-xs font-medium text-text-1 group-hover:text-white">{c.label}</span>
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
    </>
  );
}
