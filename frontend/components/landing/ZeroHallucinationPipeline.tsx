"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";

interface PipelineStep {
  id: string;
  number: string;
  title: string;
  description: string;
  iconText: string;
  formula: string;
}

const STEPS: PipelineStep[] = [
  {
    id: "sourcing",
    number: "01",
    title: "Regulated Sourcing",
    description:
      "Direct ingestion from AMFI daily NAV feeds, NSE benchmark TRI indexes, and official monthly AMC portfolio disclosures.",
    iconText: "text-[#00FF9D]",
    formula:
      "source: AMFI NAV Bhav Copy (daily)\n     + AMC monthly portfolio disclosure (SEBI mandated)\n     + NSE/BSE benchmark TRI index feed",
  },
  {
    id: "math",
    number: "02",
    title: "Deterministic Math",
    description:
      "Pure TypeScript & Python financial formulas calculate CAGR, Sharpe, Sortino, Alpha, and portfolio overlaps. No LLM arithmetic.",
    iconText: "text-cyan-400",
    formula:
      "CAGR = (NAV_end / NAV_start) ** (1/years) - 1\nSharpe = (Rp - Rf) / stdev(Rp)\nOverlap% = sum(min(w_a[i], w_b[i]) for i in common_holdings)",
  },
  {
    id: "limits",
    number: "03",
    title: "Visible Limitations",
    description:
      "Whenever a field is missing, stale, or unavailable, FundersAI discloses the exact limit before generating research answers.",
    iconText: "text-purple-400",
    formula:
      'field: expense_ratio\nstatus: stale (45 days since last factsheet)\naction: flagged in response, never extrapolated',
  },
  {
    id: "synthesis",
    number: "04",
    title: "Grounded Synthesis",
    description:
      "Multi-agent LLM summaries only interpret calculated figures and cite source documents. Financial advice is strictly declined.",
    iconText: "text-amber-400",
    formula:
      "llm_input: computed_metrics + cited_source_chunks\nllm_output: interpretation only\nconstraint: no numeric claim without a citation",
  },
];

function PipelineNode({ step }: { step: PipelineStep }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 flex flex-col">
      <span className={`font-mono text-3xl font-bold leading-none ${step.iconText} opacity-40`} aria-hidden="true">
        {step.number}
      </span>
      <h4 className="text-base font-bold text-white mt-3">{step.title}</h4>
      <p className="text-xs text-[#aebed6] leading-relaxed mt-1.5">{step.description}</p>

      <button
        onClick={() => setOpen((v) => !v)}
        className="mt-3 inline-flex items-center gap-1 text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 hover:text-white transition self-start"
      >
        <span>Inspect formula</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <pre className="mt-3 rounded-lg bg-black/40 border border-white/10 p-3 text-[10px] font-mono text-slate-300 leading-relaxed whitespace-pre-wrap">
              {step.formula}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function PipelineConnector() {
  return (
    <div className="flex md:contents">
      {/* Vertical variant: stacked mobile layout */}
      <div className="flex md:hidden items-center justify-center py-1">
        <div className="relative w-0.5 h-6 rounded-full bg-white/10 overflow-hidden">
          <div className="pipeline-connector-pulse absolute inset-x-0 top-0 h-1/6 rounded-full bg-gradient-to-b from-transparent via-[#00FF9D] to-transparent animate-pipeline-flow-y" />
        </div>
      </div>
      {/* Horizontal variant: side-by-side desktop layout */}
      <div className="hidden md:flex items-center justify-center px-1">
        <div className="relative w-8 h-0.5 rounded-full bg-white/10 overflow-hidden">
          <div className="pipeline-connector-pulse absolute inset-y-0 left-0 w-1/6 rounded-full bg-gradient-to-r from-transparent via-[#00FF9D] to-transparent animate-pipeline-flow-x" />
        </div>
      </div>
    </div>
  );
}

export default function ZeroHallucinationPipeline() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] gap-4 md:gap-0 items-stretch">
      {STEPS.map((step, i) => (
        <React.Fragment key={step.id}>
          <PipelineNode step={step} />
          {i < STEPS.length - 1 && <PipelineConnector />}
        </React.Fragment>
      ))}
    </div>
  );
}
