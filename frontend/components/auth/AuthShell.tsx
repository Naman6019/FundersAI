import Image from 'next/image';
import Link from 'next/link';
import { Check, ShieldCheck } from 'lucide-react';
import type { ReactNode } from 'react';

type AuthShellProps = {
  title: string;
  description: string;
  children: ReactNode;
};

export default function AuthShell({ title, description, children }: AuthShellProps) {
  return (
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-[#050810] px-4 py-10 text-white selection:bg-blue-500/30 sm:px-6">
      {/* Cobalt Radial Background & Grid */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(37,99,235,0.14),transparent_42rem)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(rgba(59,130,246,0.08)_1px,transparent_1px)] [background-size:24px_24px] opacity-40" />

      <div className="relative z-10 w-full max-w-[440px]">
        {/* Structural Slab Vault Card */}
        <section className="rounded-2xl border border-gray-800/90 bg-[#070b12]/95 p-6 shadow-2xl backdrop-blur-xl sm:p-8 border-t-blue-500/30 shadow-blue-950/20">
          <div className="mb-6 flex flex-col items-center text-center">
            <Link
              href="/"
              aria-label="FundersAI home"
              className="relative mb-4 block h-[68px] w-[240px] max-w-full overflow-hidden rounded-xl border border-gray-800 bg-[#0b0f19] p-2 transition hover:border-blue-500/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              <Image
                src="/FUNDERSAI-nobackground.png"
                alt="FundersAI"
                fill
                priority
                sizes="240px"
                className="object-contain p-2"
                unoptimized
              />
            </Link>
            
            <div className="font-mono text-[10px] uppercase font-bold tracking-widest text-blue-400 px-2.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 mb-3">
              [ SECURE_IDENTITY_VAULT ]
            </div>

            <h1 className="text-2xl font-bold tracking-tight text-white font-serif-display">{title}</h1>
            <p className="mt-1.5 max-w-sm text-xs leading-5 text-gray-400 font-sans">{description}</p>
          </div>

          {children}

          <p className="mt-6 text-center font-mono text-[10px] leading-5 text-gray-500 uppercase tracking-wider">
            By continuing, you agree to{' '}
            <Link href="/terms" className="text-gray-400 underline underline-offset-2 hover:text-blue-400">
              Terms
            </Link>{' '}
            &amp;{' '}
            <Link href="/privacy" className="text-gray-400 underline underline-offset-2 hover:text-blue-400">
              Privacy Policy
            </Link>
            .
          </p>
        </section>

        <div className="mt-4 rounded-xl border border-gray-800/80 bg-[#070b12]/80 p-3.5 backdrop-blur-md">
          <div className="flex items-center justify-center gap-2 font-mono text-[11px] font-semibold text-gray-300">
            <ShieldCheck aria-hidden="true" className="h-4 w-4 text-blue-400" />
            <span>Institutional Research Workspace</span>
          </div>
          <div className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">
            <span className="inline-flex items-center gap-1">
              <Check aria-hidden="true" className="h-3 w-3 text-emerald-400" />
              Verified Evidence
            </span>
            <span className="inline-flex items-center gap-1">
              <Check aria-hidden="true" className="h-3 w-3 text-emerald-400" />
              SEBI Ingested
            </span>
            <span className="inline-flex items-center gap-1">
              <Check aria-hidden="true" className="h-3 w-3 text-emerald-400" />
              RLS Encrypted
            </span>
          </div>
        </div>
      </div>
    </main>
  );
}
