import Link from 'next/link';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import { ArrowRight, Compass, Search, Terminal } from 'lucide-react';

export const metadata = {
  title: '404 — Research Asset Not Found | FundersAI',
  description: 'The requested financial entity, page, or research asset could not be located.',
};

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col justify-between selection:bg-primary/20 selection:text-primary-foreground">
      <EcosystemHeader />

      <main className="flex-1 flex items-center justify-center px-4 py-16 sm:py-24">
        <div className="max-w-xl w-full text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-1 border border-line text-xs font-mono text-text-2">
            <span className="h-2 w-2 rounded-full bg-amber-400" />
            <span>HTTP 404 · Unresolved Research Target</span>
          </div>

          <div className="space-y-3">
            <h1 className="text-4xl sm:text-5xl font-extrabold font-serif-display tracking-tight text-white">
              Asset Not Located
            </h1>
            <p className="text-sm sm:text-base text-text-3 max-w-md mx-auto leading-relaxed">
              The scheme, stock entity, or research view you requested does not exist or has been relocated within the data registry.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left max-w-md mx-auto pt-2">
            <Link
              href="/dashboard"
              className="group p-4 rounded-xl bg-surface-1 border border-line hover:border-primary/40 transition-all flex flex-col justify-between"
            >
              <div className="flex items-center justify-between text-primary mb-2">
                <Terminal className="w-5 h-5" />
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div>
                <div className="text-sm font-semibold text-white">Research Workspace</div>
                <div className="text-xs text-text-3">Launch interactive chat & canvas</div>
              </div>
            </Link>

            <Link
              href="/mutual-funds"
              className="group p-4 rounded-xl bg-surface-1 border border-line hover:border-primary/40 transition-all flex flex-col justify-between"
            >
              <div className="flex items-center justify-between text-emerald-400 mb-2">
                <Search className="w-5 h-5" />
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div>
                <div className="text-sm font-semibold text-white">Fund Directory</div>
                <div className="text-xs text-text-3">Screen 1,000+ verified schemes</div>
              </div>
            </Link>

            <Link
              href="/tools"
              className="group p-4 rounded-xl bg-surface-1 border border-line hover:border-primary/40 transition-all flex flex-col justify-between"
            >
              <div className="flex items-center justify-between text-blue-400 mb-2">
                <Compass className="w-5 h-5" />
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div>
                <div className="text-sm font-semibold text-white">Quantitative Tools</div>
                <div className="text-xs text-text-3">Portfolio overlap & SIP calculators</div>
              </div>
            </Link>

            <Link
              href="/synthesis"
              className="group p-4 rounded-xl bg-surface-1 border border-line hover:border-violet-500/40 transition-all flex flex-col justify-between"
            >
              <div className="flex items-center justify-between text-violet-400 mb-2">
                <span className="text-lg font-bold">⚡</span>
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div>
                <div className="text-sm font-semibold text-white">Synthesis Studio</div>
                <div className="text-xs text-text-3">Multi-agent comparative reports</div>
              </div>
            </Link>
          </div>

          <div className="pt-4">
            <Link
              href="/"
              className="inline-flex items-center gap-2 text-xs font-mono text-text-3 hover:text-primary transition-colors"
            >
              <span>← Return to FundersAI Home</span>
            </Link>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
