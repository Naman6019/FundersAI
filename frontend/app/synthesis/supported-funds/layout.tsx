import type { Metadata } from 'next';
import type { ReactNode } from 'react';

/**
 * The page itself is a client component and cannot export metadata, so it shipped with no
 * title, description or canonical — Google crawled it and declined to index it. Canonical
 * points at the Synthesis subdomain, the one host this product is served from.
 */
export const metadata: Metadata = {
  // The parent synthesis layout appends "| Synthesis by FundersAI" via title.template.
  title: 'Supported Mutual Funds & Coverage',
  description:
    'Every AMC and scheme Synthesis can generate a research report for, grouped by fund house, with the official factsheet coverage backing each one.',
  alternates: {
    canonical: 'https://synthesis.fundersai.co.in/synthesis/supported-funds',
  },
  openGraph: {
    title: 'Supported Mutual Funds & Coverage | Synthesis by FundersAI',
    description:
      'The full list of AMCs and schemes covered by Synthesis, grouped by fund house.',
    url: 'https://synthesis.fundersai.co.in/synthesis/supported-funds',
  },
};

export default function SupportedFundsLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
