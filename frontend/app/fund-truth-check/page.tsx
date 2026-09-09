import type { Metadata } from 'next';
import FundTruthCheckLaunchPage from '@/components/landing/FundTruthCheckLaunchPage';

export const metadata: Metadata = {
  title: 'Fund Truth Check | Evidence-first mutual fund claim review',
  description: 'See how Fund Truth Check turns a mutual-fund claim into exact scheme, metric, source, date, calculation and freshness checks—and abstains when proof is missing.',
  alternates: {
    canonical: 'https://www.fundersai.co.in/fund-truth-check',
  },
  openGraph: {
    title: 'Fund Truth Check | FundersAI',
    description: 'A mutual-fund claim checker that shows its evidence boundary.',
    url: 'https://www.fundersai.co.in/fund-truth-check',
    siteName: 'FundersAI',
    type: 'website',
    images: ['/fund-truth-check/opengraph-image'],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Fund Truth Check | FundersAI',
    description: 'A mutual-fund claim checker that shows its evidence boundary.',
    images: ['/fund-truth-check/opengraph-image'],
  },
};

export default function FundTruthCheckLaunchRoute() {
  return <FundTruthCheckLaunchPage />;
}
