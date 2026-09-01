import type { Metadata } from 'next';
import type { ReactNode } from 'react';

/** Per-user saved reports and watchlists — nothing here is the same for two visitors. */
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function SynthesisDashboardLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
