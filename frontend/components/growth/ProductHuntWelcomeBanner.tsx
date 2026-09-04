"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Sparkles, X, ArrowRight, Copy, Check } from "lucide-react";
import { trackEvent } from "@/lib/analytics";

const STORAGE_KEY_REFERRAL = "fundersai_ph_referral";
const STORAGE_KEY_DISMISSED = "fundersai_ph_dismissed";

export default function ProductHuntWelcomeBanner() {
  const [isVisible, setIsVisible] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    try {
      const urlParams = new URLSearchParams(window.location.search);
      const ref = (urlParams.get("ref") || "").toLowerCase();
      const utmSource = (urlParams.get("utm_source") || "").toLowerCase();

      const isPhSource = ref === "producthunt" || utmSource === "producthunt";

      if (isPhSource) {
        window.sessionStorage.setItem(STORAGE_KEY_REFERRAL, "true");
      }

      const hasReferralSession = window.sessionStorage.getItem(STORAGE_KEY_REFERRAL) === "true";
      const isDismissed = window.sessionStorage.getItem(STORAGE_KEY_DISMISSED) === "true";

      if ((isPhSource || hasReferralSession) && !isDismissed) {
        requestAnimationFrame(() => {
          setIsVisible(true);
          trackEvent("ph_banner_viewed", { source: ref || utmSource || "session" });
        });
      }
    } catch {
      // Ignore storage restrictions
    }
  }, []);

  const handleDismiss = () => {
    setIsVisible(false);
    try {
      window.sessionStorage.setItem(STORAGE_KEY_DISMISSED, "true");
      trackEvent("ph_banner_dismissed");
    } catch {
      // Ignore
    }
  };

  const handleCopyCode = () => {
    try {
      navigator.clipboard.writeText("PRODUCTHUNT");
      setCopied(true);
      trackEvent("ph_coupon_copied");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Ignore
    }
  };

  if (!isVisible) return null;

  return (
    <aside
      aria-label="Product Hunt Welcome"
      className="relative z-50 w-full bg-gradient-to-r from-[#050b14] via-[#0d1b2a] to-[#050b14] border-b border-[#00FF9D]/30 py-2 px-4 text-xs font-sans text-slate-200 shadow-[0_2px_15px_rgba(0,255,157,0.15)]"
    >
      <div className="max-w-[1560px] mx-auto flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 flex-wrap">
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-[#EA532B] text-white text-[10px] font-bold shadow-sm">
            P
          </span>
          <span className="font-semibold text-white">Welcome Product Hunters!</span>
          <span className="hidden sm:inline text-slate-400">|</span>
          <span className="text-slate-300">
            Exclusive Launch Offer: Get <strong className="text-[#00FF9D]">50% off Pro</strong> with code
          </span>
          <button
            type="button"
            onClick={handleCopyCode}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white/10 hover:bg-white/20 border border-white/15 font-mono text-[#00FF9D] font-bold transition-colors cursor-pointer"
            title="Click to copy code"
          >
            PRODUCTHUNT
            {copied ? <Check className="w-3 h-3 text-[#00FF9D]" /> : <Copy className="w-3 h-3 text-slate-400" />}
          </button>
        </div>

        <div className="flex items-center gap-3 ml-auto">
          <Link
            href="/compare/parag-parikh-flexi-cap-fund-vs-hdfc-flexi-cap-fund"
            onClick={() => trackEvent("ph_banner_demo_clicked")}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#00FF9D]/15 hover:bg-[#00FF9D]/25 border border-[#00FF9D]/40 text-[#00FF9D] font-semibold text-[11px] transition-all hover:scale-[1.02]"
          >
            <Sparkles className="w-3 h-3" />
            <span>Try 1-Click Instant Demo</span>
            <ArrowRight className="w-3 h-3" />
          </Link>

          <button
            type="button"
            onClick={handleDismiss}
            aria-label="Dismiss banner"
            className="text-slate-400 hover:text-white transition-colors p-1 rounded hover:bg-white/10"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
