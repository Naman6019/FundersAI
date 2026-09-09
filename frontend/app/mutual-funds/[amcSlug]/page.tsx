import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import CatalogDirectory from '@/components/funds/CatalogDirectory';
import { getPublishedFunds } from '@/lib/mf/catalog';
export const dynamic = 'force-dynamic';
export const dynamicParams = true;
type Props = { params: Promise<{ amcSlug: string }> };
async function fundsFor(amcSlug: string) {
  const funds = (await getPublishedFunds()).filter(f => f.amc_slug === amcSlug);
  if (!funds.length) notFound();
  return funds;
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { amcSlug } = await params;
  const funds = await fundsFor(amcSlug);
  return { title: `${funds[0].amc_name} | FundersAI`,
    alternates: { canonical: `https://www.fundersai.co.in/mutual-funds/${amcSlug}` } };
}
export default async function Page({ params }: Props) {
  const funds = await fundsFor((await params).amcSlug);
  return <CatalogDirectory breadcrumbs={<Breadcrumbs items={[{ label: 'Home', href: '/' }, { label: 'Mutual Funds', href: '/mutual-funds' }, { label: funds[0].amc_name }]} />} title={funds[0].amc_name} funds={funds} />;
}
