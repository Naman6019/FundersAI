"use client";

import React from "react";
import Image from "next/image";

const AMC_LOGOS = [
  { name: "HDFC Mutual Fund", file: "hdfc.svg" },
  { name: "Parag Parikh (PPFAS)", file: "ppfas.svg" },
  { name: "SBI Mutual Fund", file: "sbi.svg" },
  { name: "ICICI Prudential", file: "icici.jpeg" },
  { name: "Nippon India", file: "nippon.webp" },
  { name: "Mirae Asset", file: "mirae.jpg" },
  { name: "Axis Mutual Fund", file: "axis.svg", darkTile: true },
  { name: "Kotak Mahindra", file: "kotak.svg", darkTile: true },
  { name: "Motilal Oswal", file: "motilal.webp", darkTile: true },
  { name: "UTI Mutual Fund", file: "uti.webp" },
  { name: "DSP Mutual Fund", file: "dsp.svg", darkTile: true },
  { name: "Aditya Birla Sun Life", file: "aditya_birla.png" },
] as const;

function LogoTile({ name, file, darkTile }: { name: string; file: string; darkTile?: boolean }) {
  return (
    <div
      className={`group relative shrink-0 w-[132px] h-16 sm:w-[152px] sm:h-[72px] rounded-2xl border flex items-center justify-center px-5 py-3 transition-all duration-300 hover:-translate-y-1 hover:border-[#00FF9D]/40 ${
        darkTile
          ? "bg-[#0d1220] border-white/10 shadow-[0_1px_2px_rgba(0,0,0,0.3)] hover:shadow-[0_8px_24px_rgba(0,255,157,0.12)]"
          : "bg-white border-black/5 shadow-[0_1px_2px_rgba(0,0,0,0.08)] hover:shadow-[0_8px_24px_rgba(0,255,157,0.18)]"
      }`}
      title={name}
    >
      <div className="relative w-full h-full">
        <Image
          src={`/logos/${file}`}
          alt={name}
          fill
          sizes="152px"
          className="object-contain"
        />
      </div>
    </div>
  );
}

export default function AmcLogoMarquee() {
  return (
    <section className="px-0 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <div className="text-center max-w-2xl mx-auto mb-10 px-4 space-y-3">
        <p className="text-xs font-mono font-bold uppercase tracking-[0.22em] text-[#00FF9D]">
          Institutional Data Lineage
        </p>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Ingesting Official Disclosures From India&apos;s Leading Asset Management Companies
        </h2>
        <p className="text-sm text-[#aebed6] leading-relaxed">
          AMFI-registered fund houses profiled on FundersAI, sourced directly from official NAV feeds and factsheet portfolios.
        </p>
      </div>

      <div
        className="relative overflow-hidden py-2"
        style={{
          maskImage:
            "linear-gradient(to right, transparent, black 8%, black 92%, transparent)",
          WebkitMaskImage:
            "linear-gradient(to right, transparent, black 8%, black 92%, transparent)",
        }}
      >
        <div
          className="amc-marquee-track flex w-max items-center gap-5 animate-marquee-scroll hover:[animation-play-state:paused] motion-reduce:animate-none"
        >
          {[0, 1].map((copy) => (
            <div
              key={copy}
              aria-hidden={copy === 1}
              className="flex items-center gap-5 shrink-0"
            >
              {AMC_LOGOS.map((amc) => (
                <LogoTile
                  key={`${copy}-${amc.file}`}
                  name={amc.name}
                  file={amc.file}
                  darkTile={"darkTile" in amc ? amc.darkTile : false}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
