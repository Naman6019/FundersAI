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
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-[#050505] px-4 py-10 text-white selection:bg-[#00FF9D]/30 sm:px-6">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(0,255,157,0.12),transparent_38rem)]" />
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#00FF9D]/5 blur-[110px]" />

      <div className="relative z-10 w-full max-w-[430px]">
        <section className="rounded-2xl border border-white/10 bg-[#111415]/95 p-6 shadow-[0_28px_80px_rgba(0,0,0,0.55)] backdrop-blur-xl sm:p-8">
          <div className="mb-7 flex flex-col items-center text-center">
            <Link
              href="/"
              aria-label="FundersAI home"
              className="relative mb-5 block h-[72px] w-[250px] max-w-full overflow-hidden rounded-xl border border-white/10 bg-[#343337] shadow-[0_12px_32px_rgba(0,0,0,0.35)] transition hover:border-[#00FF9D]/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00FF9D]"
            >
              <Image
                src="/FUNDERSAI-background.png"
                alt="FundersAI"
                fill
                priority
                sizes="250px"
                className="object-cover object-center"
              />
            </Link>
            <h1 className="text-2xl font-semibold tracking-[-0.025em] text-white">{title}</h1>
            <p className="mt-2 max-w-sm text-sm leading-6 text-[#9aa3a1]">{description}</p>
          </div>

          {children}

          <p className="mt-6 text-center text-[11px] leading-5 text-[#78817f]">
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

        <div className="mt-5 rounded-xl border border-white/[0.07] bg-[#111415]/70 px-4 py-3">
          <div className="flex items-center justify-center gap-2 text-xs font-medium text-[#c3ccca]">
            <ShieldCheck aria-hidden="true" className="h-4 w-4 text-[#00FF9D]" />
            Research workspace with visible evidence and limits
          </div>
          <div className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 text-[11px] text-[#78817f]">
            <span className="inline-flex items-center gap-1">
              <Check aria-hidden="true" className="h-3 w-3 text-[#00FF9D]" />
              Research-only
            </span>
            <span className="inline-flex items-center gap-1">
              <Check aria-hidden="true" className="h-3 w-3 text-[#00FF9D]" />
              Official evidence where available
            </span>
            <span className="inline-flex items-center gap-1">
              <Check aria-hidden="true" className="h-3 w-3 text-[#00FF9D]" />
              Data limits shown
            </span>
          </div>
        </div>
      </div>
    </main>
  );
}
