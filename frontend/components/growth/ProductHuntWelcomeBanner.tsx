"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Sparkles, X } from "lucide-react";
import { trackWhopEvent } from "@/lib/whopPixel";

const REFERRAL_KEY = "fundersai_producthunt_referral";
const DISMISSED_KEY = "fundersai_producthunt_dismissed";
const SIGNUP_HREF = "/login?mode=signup&next=%2Fsynthesis%2Fgenerate";

export default function ProductHuntWelcomeBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const productHuntVisit = params.get("ref")?.toLowerCase() === "producthunt"
      || params.get("utm_source")?.toLowerCase() === "producthunt";

    if (productHuntVisit) window.sessionStorage.setItem(REFERRAL_KEY, "true");
    const referred = productHuntVisit || window.sessionStorage.getItem(REFERRAL_KEY) === "true";
    const frame = window.requestAnimationFrame(() => {
      setVisible(referred && window.sessionStorage.getItem(DISMISSED_KEY) !== "true");
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  if (!visible) return null;

  return (
    <aside aria-label="Product Hunt welcome" className="relative z-50 border-b border-[#00FF9D]/30 bg-[#07141a] px-4 py-2 text-xs text-slate-200">
      <div className="mx-auto flex max-w-[1560px] flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-[#00FF9D]" />
          <span><strong className="text-white">Welcome, Product Hunters.</strong> Evidence-backed research only — never personalized financial advice.</span>
        </p>
        <div className="flex items-center gap-3">
          <Link
            href={SIGNUP_HREF}
            onClick={() => trackWhopEvent("lead")}
            className="inline-flex items-center gap-1 rounded-full border border-[#00FF9D]/45 bg-[#00FF9D]/15 px-3 py-1 font-semibold text-[#00FF9D] hover:bg-[#00FF9D]/25"
          >
            Start free research <ArrowRight className="h-3 w-3" />
          </Link>
          <button
            type="button"
            aria-label="Dismiss Product Hunt welcome"
            onClick={() => {
              window.sessionStorage.setItem(DISMISSED_KEY, "true");
              setVisible(false);
            }}
            className="rounded p-1 text-slate-400 hover:bg-white/10 hover:text-white"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
