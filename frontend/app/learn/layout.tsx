import Link from 'next/link';
import Image from 'next/image';

export default function LearnLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#050505] text-[#e8f0ff] antialiased selection:bg-[#00FF9D]/30 selection:text-white">
      {/* Background elements */}
      <div className="fixed inset-0 z-0 bg-[linear-gradient(to_right,rgba(102,163,255,0.08)_1px,transparent_1px),linear-gradient(to_bottom,rgba(102,163,255,0.07)_1px,transparent_1px)] bg-[size:88px_88px] [mask-image:radial-gradient(ellipse_at_top,black_22%,transparent_74%)]" />
      <div className="pointer-events-none fixed inset-0 z-0 bg-[radial-gradient(circle_at_50%_0%,rgba(102,163,255,0.06),transparent_65%)]" />
      
      <div className="relative z-10 flex flex-col min-h-screen">
        <header className="h-16 flex items-center justify-between border-b border-white/10 px-6 backdrop-blur-md bg-[#050505]/80">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/FUNDERSAI-nobackground.png" alt="FundersAI Logo" width={28} height={28} className="object-contain" />
            <span className="text-sm font-semibold text-white">FundersAI</span>
          </Link>
          <Link href="/dashboard" className="text-sm font-medium text-slate-300 hover:text-white transition">
            Go to App
          </Link>
        </header>
        <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-12">
          {children}
        </main>
      </div>
    </div>
  );
}
