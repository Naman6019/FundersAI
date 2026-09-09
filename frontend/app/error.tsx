'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { AlertTriangle, RefreshCw, Terminal, Home } from 'lucide-react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Unhandled runtime error caught by boundary:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-surface-1 border border-line rounded-2xl p-6 sm:p-8 space-y-6 shadow-2xl text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 mx-auto">
          <AlertTriangle className="w-6 h-6" />
        </div>

        <div className="space-y-2">
          <h1 className="text-xl font-bold font-serif-display text-white">
            Workspace Interruption
          </h1>
          <p className="text-xs sm:text-sm text-text-3 leading-relaxed">
            An unexpected error occurred during research interface execution. Deterministic state has been preserved.
          </p>
          {error?.digest && (
            <p className="text-[10px] font-mono text-text-3 bg-surface-2 px-2 py-1 rounded inline-block">
              Error Digest: {error.digest}
            </p>
          )}
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <button
            type="button"
            onClick={() => reset()}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-semibold text-xs hover:bg-primary/90 transition-all shadow-md"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Try Again</span>
          </button>

          <Link
            href="/dashboard"
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-surface-2 border border-line text-xs font-semibold text-white hover:bg-surface-hover transition-all"
          >
            <Terminal className="w-4 h-4 text-primary" />
            <span>Workspace</span>
          </Link>
        </div>

        <div className="pt-2 border-t border-line">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-[11px] font-mono text-text-3 hover:text-white transition-colors"
          >
            <Home className="w-3.5 h-3.5" />
            <span>Back to Ecosystem Home</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
