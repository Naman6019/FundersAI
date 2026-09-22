import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import CatalogDirectory from '@/components/funds/CatalogDirectory';
import { tryGetPublishedFunds } from '@/lib/mf/catalog';
export const dynamic = 'force-dynamic';
export const dynamicParams = true;
type Props = { params: Promise<{ amcSlug: string }> };
async function fundsFor(amcSlug: string) {
  const catalog = await tryGetPublishedFunds();
  if (catalog === undefined) return undefined;
  const funds = catalog.filter(f => f.amc_slug === amcSlug);
  if (!funds.length) notFound();
  return funds;
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { amcSlug } = await params;
  const funds = await fundsFor(amcSlug);
  // An infrastructure failure returns the indexable metadata untouched; only a definitive
  // empty catalog withholds the page, so a transient outage cannot flip it to noindex.
  if (funds === undefined) return { title: 'Mutual Fund Directory | FundersAI',
    alternates: { canonical: `https://www.fundersai.co.in/mutual-funds/${amcSlug}` } };
  return { title: `${funds[0].amc_name} | FundersAI`,
    alternates: { canonical: `https://www.fundersai.co.in/mutual-funds/${amcSlug}` } };
}
export default async function Page({ params }: Props) {
  const funds = await fundsFor((await params).amcSlug);
  if (funds === undefined) return <CatalogDirectory title="Mutual Fund Directory" funds={null} />;
  return <CatalogDirectory breadcrumbs={<Breadcrumbs items={[{ label: 'Home', href: '/' }, { label: 'Mutual Funds', href: '/mutual-funds' }, { label: funds[0].amc_name }]} />} title={funds[0].amc_name} funds={funds} />;
}
