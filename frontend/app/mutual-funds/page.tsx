import type { Metadata } from 'next';
import CatalogDirectory from '@/components/funds/CatalogDirectory';
import { getPublishedFunds } from '@/lib/mf/catalog';
export const dynamic = 'force-dynamic';
export const metadata: Metadata = {
  title: 'Mutual Fund Directory | FundersAI',
  description: 'Eligible Direct Growth mutual funds with dated NAV and full-window returns.',
  alternates: { canonical: 'https://www.fundersai.co.in/mutual-funds' },
};
export default async function Page() {
  return <CatalogDirectory title="Mutual Fund Directory" funds={await getPublishedFunds()} />;
}
