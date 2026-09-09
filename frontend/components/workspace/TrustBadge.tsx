"use client";

import React from "react";
import { ShieldCheck, AlertTriangle, FileText, ExternalLink } from "lucide-react";

interface TrustBadgeProps {
  status?: "verified" | "lagging" | "stale" | "missing";
  asOfDate?: string;
  sourceDoc?: string;
  pdfChunkUrl?: string;
  showCitationAction?: boolean;
}

export function TrustBadge({
  status = "verified",
  asOfDate = "Snapshot date unavailable",
  sourceDoc = "Official AMC Factsheet",
  pdfChunkUrl,
  showCitationAction = true,
}: TrustBadgeProps) {
  const isVerified = status === "verified";
  const isLagging = status === "lagging";

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border backdrop-blur-md bg-slate-950/70 border-white/10 hover:border-emerald-500/40 transition-all shadow-sm group">
      {isVerified ? (
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
      ) : isLagging ? (
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
      ) : (
        <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
      )}

      <span className="font-mono text-[11px] text-slate-300">
        As of {asOfDate}
      </span>

      {sourceDoc && (
        <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 border-l border-white/10 pl-2">
          {sourceDoc}
        </span>
      )}

      {showCitationAction && (
        <a
          href={pdfChunkUrl || "/data-trust"}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[10px] text-emerald-400 hover:text-emerald-300 font-mono pl-1 group-hover:underline"
          title="Inspect official AMC PDF evidence chunk"
        >
          <FileText className="w-3 h-3" />
          <span>Evidence</span>
          <ExternalLink className="w-2.5 h-2.5 opacity-70" />
        </a>
      )}
    </div>
  );
}
