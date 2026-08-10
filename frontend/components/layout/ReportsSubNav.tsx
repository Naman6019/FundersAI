"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Bare landing surface — the sub-nav is studio-only chrome and would be redundant here.
const LANDING_PATHS = new Set(["/synthesis"]);

export function ReportsSubNav() {
  const pathname = usePathname();
  if (LANDING_PATHS.has(pathname)) return null;

  return (
    <div className="border-b border-terminal-border bg-terminal-bg/80 backdrop-blur-xl sticky top-16 z-40">
      <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 h-11 flex items-center justify-between">
        <nav className="flex items-center gap-1 overflow-x-auto">
          <Link
            href="/synthesis/dashboard"
            className="text-xs font-semibold px-3 py-1.5 rounded-md text-slate-400 hover:text-white hover:bg-white/5 transition-all whitespace-nowrap"
          >
            Dashboard
          </Link>
          <Link
            href="/synthesis/generate"
            className="text-xs font-semibold px-3 py-1.5 rounded-md text-slate-400 hover:text-white hover:bg-white/5 transition-all whitespace-nowrap"
          >
            New Report
          </Link>
          <Link
            href="/synthesis/tools/portfolio-overlap"
            className="text-xs font-semibold px-3 py-1.5 rounded-md text-slate-400 hover:text-white hover:bg-white/5 transition-all whitespace-nowrap"
          >
            Overlap Tool
          </Link>
          <Link
            href="/synthesis/supported-funds"
            className="text-xs font-semibold px-3 py-1.5 rounded-md text-slate-400 hover:text-white hover:bg-white/5 transition-all whitespace-nowrap"
          >
            Supported Funds
          </Link>
          <Link
            href="/synthesis/methodology"
            className="text-xs font-semibold px-3 py-1.5 rounded-md text-slate-400 hover:text-white hover:bg-white/5 transition-all whitespace-nowrap"
          >
            Methodology
          </Link>
        </nav>
        <Link
          href="/billing"
          className="text-xs font-semibold text-emerald-300 hover:text-emerald-200 px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 whitespace-nowrap"
        >
          <span className="text-amber-400">⚡</span>
          <span>Upgrade</span>
        </Link>
      </div>
    </div>
  );
}
