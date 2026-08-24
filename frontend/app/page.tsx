import type { Metadata } from 'next';
import PremiumLandingPage from '@/components/landing/PremiumLandingPage';
import SchemaMarkup from '@/components/landing/SchemaMarkup';

export const metadata: Metadata = {
  alternates: {
    canonical: 'https://www.fundersai.co.in',
  },
};

export const revalidate = 60;

export default async function LandingPage() {
  return (
    <>
      <SchemaMarkup />
      <PremiumLandingPage />
    </>
  );
}
