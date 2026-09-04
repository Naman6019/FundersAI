"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PlusCircle,
  Layers,
  Building2,
  BookOpen,
  Zap
} from "lucide-react";

// Bare landing surface — the sub-nav is studio-only chrome and would be redundant here.
const LANDING_PATHS = new Set(["/synthesis"]);

export function ReportsSubNav() {
  const pathname = usePathname();
  if (LANDING_PATHS.has(pathname)) return null;

  const isDashboard = pathname === "/synthesis/dashboard";
  const isGenerate = pathname === "/synthesis/generate";
  const isOverlap = pathname.includes("/portfolio-overlap");
  const isFunds = pathname.includes("/supported-funds");
  const isMethodology = pathname.includes("/methodology");

  return (
    <div className="my-4 print:hidden">
      <nav className="inline-flex flex-wrap items-center gap-1.5 p-1.5 rounded-2xl bg-surface-1/90 border border-line shadow-xl backdrop-blur-xl text-xs font-medium">
        <Link
          href="/synthesis/generate"
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl transition-all ${
            isGenerate
              ? "bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm font-bold"
              : "text-text-3 hover:text-text-1 hover:bg-surface-2/60 border border-transparent"
          }`}
        >
          <PlusCircle className="w-3.5 h-3.5 text-violet-400" />
          <span>New Report</span>
        </Link>

        <Link
          href="/synthesis/dashboard"
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl transition-all ${
            isDashboard
              ? "bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm font-bold"
              : "text-text-3 hover:text-text-1 hover:bg-surface-2/60 border border-transparent"
          }`}
        >
          <LayoutDashboard className="w-3.5 h-3.5 text-violet-400" />
          <span>Dashboard</span>
        </Link>

        <Link
          href="/tools/portfolio-overlap"
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl transition-all ${
            isOverlap
              ? "bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm font-bold"
              : "text-text-3 hover:text-text-1 hover:bg-surface-2/60 border border-transparent"
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-violet-400" />
          <span>Overlap Tool</span>
        </Link>

        <Link
          href="/synthesis/supported-funds"
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl transition-all ${
            isFunds
              ? "bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm font-bold"
              : "text-text-3 hover:text-text-1 hover:bg-surface-2/60 border border-transparent"
          }`}
        >
          <Building2 className="w-3.5 h-3.5 text-violet-400" />
          <span>Supported Funds</span>
        </Link>

        <Link
          href="/synthesis/methodology"
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl transition-all ${
            isMethodology
              ? "bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm font-bold"
              : "text-text-3 hover:text-text-1 hover:bg-surface-2/60 border border-transparent"
          }`}
        >
          <BookOpen className="w-3.5 h-3.5 text-violet-400" />
          <span>Methodology</span>
        </Link>

        <div className="h-4 w-px bg-line mx-1 hidden sm:block" />

        <Link
          href="/billing"
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-emerald-300 hover:text-emerald-200 hover:bg-emerald-500/10 border border-emerald-500/20 transition-all font-semibold"
        >
          <Zap className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
          <span>Upgrade</span>
        </Link>
      </nav>
    </div>
  );
}
