import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { categorySlug as slug } from '@/lib/fund-registry';
import { getPublishedFunds } from '@/lib/mf/catalog';
import CatalogDirectory from '@/components/funds/CatalogDirectory';
export const dynamic = 'force-dynamic';
export const dynamicParams = true;
type Props = { params: Promise<{ categorySlug: string }> };
async function fundsFor(categorySlug: string) {
  const funds = (await getPublishedFunds()).filter(f => slug(f.category) === categorySlug);
  if (!funds.length) notFound();
  return funds;
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { categorySlug } = await params;
  const funds = await fundsFor(categorySlug);
  return { title: `${funds[0].category} Mutual Funds | FundersAI`,
    alternates: { canonical: `https://www.fundersai.co.in/mutual-funds/category/${categorySlug}` } };
}
export default async function Page({ params }: Props) {
  const funds = await fundsFor((await params).categorySlug);
  return <CatalogDirectory breadcrumbs={<Breadcrumbs items={[{ label: 'Home', href: '/' }, { label: 'Mutual Funds', href: '/mutual-funds' }, { label: funds[0].category }]} />} title={`${funds[0].category} Mutual Funds`} funds={funds} />;
}
