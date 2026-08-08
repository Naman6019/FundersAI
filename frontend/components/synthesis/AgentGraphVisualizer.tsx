"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Database, Calculator, ShieldCheck, FileText, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { BorderBeam } from "../ui/border-beam";

export interface AgentNode {
  id: string;
  name: string;
  role: string;
  icon: React.ElementType;
  status: "completed" | "active" | "pending";
  detail: string;
}

interface AgentGraphVisualizerProps {
  onComplete?: () => void;
}

export function AgentGraphVisualizer({ onComplete }: AgentGraphVisualizerProps) {
  const [activeStep, setActiveStep] = useState<number>(0);

  const nodes: AgentNode[] = [
    {
      id: "ingest",
      name: "Data Ingestion Agent",
      role: "AMFI NAV & Official AMC Factsheets",
      icon: Database,
      status: activeStep > 0 ? "completed" : activeStep === 0 ? "active" : "pending",
      detail: "Retrieved 10Y NAV history and July 2026 factsheet chunks",
    },
    {
      id: "quant",
      name: "Quant Metrics Agent",
      role: "Sharpe, Sortino, Alpha & Drawdown",
      icon: Calculator,
      status: activeStep > 1 ? "completed" : activeStep === 1 ? "active" : "pending",
      detail: "Calculated 3Y CAGR, Sharpe 1.42, Max Drawdown -14.2%",
    },
    {
      id: "overlap",
      name: "Risk & Holdings Agent",
      role: "ISIN Overlap & Sector Concentration",
      icon: ShieldCheck,
      status: activeStep > 2 ? "completed" : activeStep === 2 ? "active" : "pending",
      detail: "Found 24.8% portfolio overlap across 14 stock holdings",
    },
    {
      id: "synthesis",
      name: "Synthesis Whitepaper Agent",
      role: "Grounding & Serverless PDF Compiler",
      icon: FileText,
      status: activeStep > 3 ? "completed" : activeStep === 3 ? "active" : "pending",
      detail: "Compiled institutional PDF report with cited claims",
    },
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((prev) => {
        if (prev < 3) return prev + 1;
        if (onComplete) onComplete();
        return 3;
      });
    }, 1800);

    return () => clearInterval(timer);
  }, [onComplete]);

  return (
    <div className="w-full my-6 p-6 rounded-2xl bg-[#0F111A]/90 border border-cyan-500/30 shadow-2xl relative overflow-hidden backdrop-blur-xl">
      <BorderBeam size={250} duration={8} delay={0} colorFrom="#06b6d4" colorTo="#10b981" />

      <div className="flex items-center justify-between mb-6 border-b border-white/10 pb-4">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400 font-bold flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Autonomous Multi-Agent Intelligence Graph</span>
          </span>
          <h3 className="text-lg font-bold text-white mt-1 font-sans">
            Synthesizing Institutional Mutual Fund Report
          </h3>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 bg-cyan-950/60 border border-cyan-800/40 rounded-full font-mono text-xs text-cyan-300">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Step {activeStep + 1} of 4 Active</span>
        </div>
      </div>

      {/* Pipeline Node Layout */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
        {nodes.map((node, index) => {
          const Icon = node.icon;
          const isCompleted = node.status === "completed";
          const isActive = node.status === "active";

          return (
            <motion.div
              key={node.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.15 }}
              className={`p-4 rounded-xl border transition-all relative ${
                isActive
                  ? "bg-cyan-950/40 border-cyan-400 shadow-lg shadow-cyan-950/50 scale-[1.02]"
                  : isCompleted
                  ? "bg-slate-900/60 border-emerald-500/40"
                  : "bg-slate-900/20 border-white/5 opacity-50"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className={`p-2 rounded-lg ${isActive ? "bg-cyan-500/20 text-cyan-400" : isCompleted ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-800 text-slate-500"}`}>
                  <Icon className="w-4 h-4" />
                </div>

                {isCompleted ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isActive ? (
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-slate-700" />
                )}
              </div>

              <h4 className="text-xs font-bold text-white font-sans">{node.name}</h4>
              <p className="text-[10px] text-slate-400 font-mono mt-0.5">{node.role}</p>

              {isActive && (
                <p className="text-[11px] text-cyan-300 font-sans mt-2 pt-2 border-t border-cyan-500/20 animate-pulse">
                  {node.detail}
                </p>
              )}

              {isCompleted && (
                <p className="text-[11px] text-emerald-400/90 font-sans mt-2 pt-2 border-t border-white/5">
                  ✓ {node.detail}
                </p>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
