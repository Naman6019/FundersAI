import type { Metadata } from 'next';
import PremiumLandingPage from '@/components/landing/PremiumLandingPage';
import SchemaMarkup from '@/components/landing/SchemaMarkup';

export const metadata: Metadata = {
  title: 'FundersAI Research | Quantitative Mutual Fund Intelligence Workspace',
  description:
    'Research-first workspace for comparing Indian mutual funds and stocks with deterministic metrics, official-source evidence, Sharpe ratios, portfolio holdings, and visible data limits.',
  keywords: [
    'FundersAI Research',
    'FundersAI Research Workspace',
    'Indian mutual fund research AI',
    'deterministic quantitative finance India',
    'AMFI NAV calculation engine',
    'mutual fund risk metrics workspace',
    'Sharpe ratio mutual fund calculator India',
  ],
  alternates: {
    canonical: 'https://www.fundersai.co.in/research',
  },
  openGraph: {
    images: ['/opengraph-image'],
    title: 'FundersAI Research | Quantitative Mutual Fund Intelligence Workspace',
    description:
      'Explore evidence-based mutual fund research with deterministic metrics, official AMC factsheet sources, and zero hallucinations.',
    url: 'https://www.fundersai.co.in/research',
    siteName: 'FundersAI',
    locale: 'en_IN',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FundersAI Research | Quantitative Mutual Fund Intelligence Workspace',
    description:
      'Evidence-based mutual fund research workspace with deterministic metrics and official AMFI/AMC sources.',
  },
};

export const revalidate = 60;

export default function ResearchPage() {
  return (
    <>
      <SchemaMarkup />
      <PremiumLandingPage />
    </>
  );
}
