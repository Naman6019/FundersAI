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
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-[#070b12] px-4 py-10 text-white sm:px-6">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(79,143,247,0.16),transparent_38rem)]" />
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#66a3ff]/7 blur-[110px]" />

      <div className="relative z-10 w-full max-w-[430px]">
        <section className="rounded-2xl border border-white/10 bg-[#101724]/95 p-6 shadow-[0_28px_80px_rgba(0,0,0,0.48)] backdrop-blur-xl sm:p-8">
          <div className="mb-7 flex flex-col items-center text-center">
            <Link
              href="/"
              aria-label="FundersAI home"
              className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] shadow-lg transition hover:border-white/20 hover:bg-white/[0.07] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#66a3ff]"
            >
              <span
                aria-hidden="true"
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-[#8cc0ff] to-[#4f8ff7] text-base font-black text-[#07111f] shadow-[0_8px_20px_rgba(79,143,247,0.25)]"
              >
                F
              </span>
            </Link>
            <h1 className="text-2xl font-semibold tracking-[-0.025em] text-white">{title}</h1>
            <p className="mt-2 max-w-sm text-sm leading-6 text-[#91a3bf]">{description}</p>
          </div>

          {children}

          <p className="mt-6 text-center text-[11px] leading-5 text-[#7183a0]">
            By continuing, you agree to the{' '}
            <Link href="/terms" className="underline underline-offset-2 transition hover:text-white">
              Terms
            </Link>{' '}
            and acknowledge the{' '}
            <Link href="/privacy" className="underline underline-offset-2 transition hover:text-white">
              Privacy Policy
            </Link>
            .
          </p>
        </section>

        <div className="mt-5 rounded-xl border border-white/[0.07] bg-white/[0.025] px-4 py-3">
          <div className="flex items-center justify-center gap-2 text-xs font-medium text-[#b5c6df]">
            <ShieldCheck aria-hidden="true" className="h-4 w-4 text-[#77aaf7]" />
            Research workspace with visible evidence and limits
          </div>
          <div className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 text-[11px] text-[#7183a0]">
            <span className="inline-flex items-center gap-1">
              <Check aria-hidden="true" className="h-3 w-3 text-[#35ce94]" />
              Research-only
            </span>
            <span className="inline-flex items-center gap-1">
              <Check aria-hidden="true" className="h-3 w-3 text-[#35ce94]" />
              Official evidence where available
            </span>
            <span className="inline-flex items-center gap-1">
              <Check aria-hidden="true" className="h-3 w-3 text-[#35ce94]" />
              Data limits shown
            </span>
          </div>
        </div>
      </div>
    </main>
  );
}
