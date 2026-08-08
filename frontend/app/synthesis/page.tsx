import type { Metadata } from 'next';
import ReportsLandingPage from '../reports/page';
import ReportsLayout from '../reports/layout';

export const metadata: Metadata = {
  title: 'Synthesis by FundersAI | Autonomous AI Mutual Fund Research Studio',
  description:
    'Synthesis by FundersAI leverages autonomous multi-agent graph intelligence to synthesize institutional mutual fund comparison reports, risk metrics, portfolio overlap, and 1-click PDF exports.',
  keywords: [
    'Synthesis by FundersAI',
    'Synthesis Studio',
    'FundersAI Synthesis',
    'AI mutual fund synthesis report',
    'autonomous financial multi-agent research',
    'mutual fund factsheet parser India',
    'Parag Parikh vs HDFC Flexi Cap report',
    'institutional mutual fund comparison PDF',
  ],
  openGraph: {
    title: 'Synthesis by FundersAI | Autonomous AI Mutual Fund Research Studio',
    description:
      'Instant institutional-grade mutual fund comparison reports with quantitative risk metrics, portfolio overlap, and direct serverless PDF exports.',
    url: 'https://www.fundersai.co.in/synthesis',
    siteName: 'Synthesis by FundersAI',
    locale: 'en_IN',
    type: 'website',
    images: [
      {
        url: '/Synthesis_FUNDERSAI.png',
        width: 1200,
        height: 630,
        alt: 'Synthesis by FundersAI',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Synthesis by FundersAI | Autonomous AI Mutual Fund Research Studio',
    description:
      'Instant institutional-grade mutual fund comparison reports with risk metrics, portfolio overlap, and PDF export.',
    images: ['/Synthesis_FUNDERSAI.png'],
  },
};

export default function SynthesisPage() {
  return (
    <ReportsLayout>
      <ReportsLandingPage />
    </ReportsLayout>
  );
}
