import type { Metadata } from 'next';
import MasterEcosystemLandingPage from '@/components/landing/MasterEcosystemLandingPage';
import SchemaMarkup from '@/components/landing/SchemaMarkup';

export const metadata: Metadata = {
  title: 'FundersAI | Quantitative Mutual Fund Intelligence & Research Platform',
  description:
    'FundersAI is the modern intelligence platform for Indian mutual funds and equities. Uniting deterministic AMFI quantitative pipelines, autonomous research synthesis, screener directories, and financial utilities.',
  keywords: [
    'FundersAI',
    'Funders AI',
    'Indian mutual fund intelligence',
    'mutual fund research platform India',
    'deterministic quantitative finance',
    'mutual fund portfolio overlap calculator',
    'mutual fund step-up SIP calculator',
    'AMFI verified mutual fund metrics',
  ],
  alternates: {
    canonical: 'https://www.fundersai.co.in',
  },
  openGraph: {
    images: ['/opengraph-image'],
    title: 'FundersAI | Quantitative Mutual Fund Intelligence & Research Platform',
    description:
      'The modern intelligence platform for Indian mutual funds and equities with deterministic math, factsheet synthesis, and public utilities.',
    url: 'https://www.fundersai.co.in',
    siteName: 'FundersAI',
    locale: 'en_IN',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FundersAI | Quantitative Mutual Fund Intelligence & Research Platform',
    description:
      'Deterministic research, synthesis dossiers & quantitative analytics for Indian capital markets.',
  },
};

export const revalidate = 60;

export default async function LandingPage() {
  return (
    <>
      <SchemaMarkup />
      <MasterEcosystemLandingPage />
    </>
  );
}
