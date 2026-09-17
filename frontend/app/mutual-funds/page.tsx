import type { Metadata } from 'next';
import CatalogDirectory from '@/components/funds/CatalogDirectory';
import { tryGetPublishedFunds } from '@/lib/mf/catalog';
export const dynamic = 'force-dynamic';
const metadata: Metadata = {
  title: 'Mutual Fund Directory | FundersAI',
  description: 'Eligible Direct Growth mutual funds with dated NAV and full-window returns.',
  alternates: { canonical: 'https://www.fundersai.co.in/mutual-funds' },
};

export async function generateMetadata(): Promise<Metadata> {
  const funds = await tryGetPublishedFunds();
  if (funds && funds.length > 0) return metadata;

  // Do not let an outage or an unpublished catalog create a thin indexed directory.
  return { ...metadata, robots: { index: false, follow: true } };
}

export default async function Page() {
  return <CatalogDirectory title="Mutual Fund Directory" funds={await tryGetPublishedFunds()} />;
}
