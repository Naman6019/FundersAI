"use client";

import React from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { useEcosystemHref } from "@/lib/ecosystem-origin";

/**
 * Footer for the Synthesis silo.
 *
 * Deliberately not `PublicFooter`: Synthesis is served from its own subdomain, where the
 * marketing footer's relative links would resolve to `synthesis.<root>/mutual-funds` and
 * friends — live duplicates of the www URLs. Studio links stay relative; everything that
 * leaves the silo goes through `useEcosystemHref` so it points back off the subdomain.
 */

const STUDIO_LINKS = [
  { label: "New Report", href: "/synthesis/generate" },
  { label: "Report Dashboard", href: "/synthesis/dashboard" },
  { label: "Portfolio Overlap", href: "/synthesis/tools/portfolio-overlap" },
  { label: "Supported Funds", href: "/synthesis/supported-funds" },
  { label: "Methodology", href: "/synthesis/methodology" },
];

const ECOSYSTEM_LINKS = [
  { label: "Research Workspace", href: "/research" },
  { label: "Mutual Fund Screener", href: "/mutual-funds" },
  { label: "Free Investor Tools", href: "/tools" },
  { label: "Data & Trust Portal", href: "/data-trust" },
];

const COMPANY_LINKS = [
  { label: "About FundersAI", href: "/about" },
  { label: "Pricing", href: "/pricing" },
  { label: "Contact Support", href: "/contact" },
  { label: "Privacy Policy", href: "/privacy" },
  { label: "Terms of Service", href: "/terms" },
];

export default function SynthesisFooter() {
  const ecosystemHref = useEcosystemHref();

  return (
    <footer className="relative z-10 mt-16 border-t border-line bg-background/80 px-5 py-14 sm:px-8 text-text-2 print:hidden">
      <div className="mx-auto grid w-full max-w-[1500px] gap-10 md:grid-cols-2 lg:grid-cols-4">
        {/* Brand + the explicit way out of the studio */}
        <div className="space-y-4">
          <div>
            <p className="text-sm font-bold text-white">Synthesis</p>
            <p className="text-[11px] font-mono-tech uppercase tracking-[0.18em] text-violet-400/80">
              by FundersAI
            </p>
          </div>
          <p className="max-w-sm text-xs leading-relaxed text-text-2">
            Autonomous multi-agent research that turns official AMC disclosures into
            institutional comparison dossiers.
          </p>
          <Link
            href={ecosystemHref("/")}
            className="group inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-1 px-3.5 py-2 text-[11px] font-bold text-white transition hover:bg-surface-hover"
          >
            <span>FundersAI Home</span>
            <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </Link>
        </div>

        {/* Studio — stays on the subdomain, so these remain relative */}
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-violet-400">
            Studio
          </p>
          <ul className="space-y-2 text-xs font-medium">
            {STUDIO_LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="transition-colors hover:text-white">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Ecosystem — leaves the silo, so these must be absolute */}
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-400">
            Ecosystem
          </p>
          <ul className="space-y-2 text-xs font-medium">
            {ECOSYSTEM_LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={ecosystemHref(link.href)}
                  className="transition-colors hover:text-white"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-text-2">
            Company
          </p>
          <ul className="space-y-2 text-xs font-medium">
            {COMPANY_LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={ecosystemHref(link.href)}
                  className="transition-colors hover:text-white"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mx-auto mt-12 flex max-w-[1500px] flex-col items-center justify-between gap-4 border-t border-line pt-6 text-[11px] text-text-3 sm:flex-row">
        <p>© {new Date().getFullYear()} FundersAI. All rights reserved.</p>
        <p className="font-mono-tech text-[10px] uppercase tracking-widest text-text-2">
          Research only · Not personalized financial advice · Verify independently
        </p>
      </div>
    </footer>
  );
}
