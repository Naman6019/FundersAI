import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { categorySlug as slug } from '@/lib/fund-registry';
import { tryGetPublishedFunds } from '@/lib/mf/catalog';
import { CategoryJsonLd } from '@/components/seo/JsonLd';
import CatalogDirectory from '@/components/funds/CatalogDirectory';
export const dynamic = 'force-dynamic';
export const dynamicParams = true;
type Props = { params: Promise<{ categorySlug: string }> };
async function fundsFor(categorySlug: string) {
  const catalog = await tryGetPublishedFunds();
  if (catalog === undefined) return undefined;
  const funds = catalog.filter(f => slug(f.category) === categorySlug);
  if (!funds.length) notFound();
  return funds;
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { categorySlug } = await params;
  const funds = await fundsFor(categorySlug);
  // An infrastructure failure returns the indexable metadata untouched; only a definitive
  // empty catalog withholds the page, so a transient outage cannot flip it to noindex.
  if (funds === undefined) return { title: 'Mutual Fund Directory | FundersAI',
    alternates: { canonical: `https://www.fundersai.co.in/mutual-funds/category/${categorySlug}` } };
  return { title: `${funds[0].category} Mutual Funds in India — NAV & Returns | FundersAI`,
    description: `${funds.length} ${funds[0].category} Direct Growth scheme${funds.length === 1 ? '' : 's'} with dated NAV and full-window annualised returns. Deterministic metrics from official AMFI sources.`,
    alternates: { canonical: `https://www.fundersai.co.in/mutual-funds/category/${categorySlug}` } };
}
export default async function Page({ params }: Props) {
  const categorySlugValue = (await params).categorySlug;
  const funds = await fundsFor(categorySlugValue);
  if (funds === undefined) return <CatalogDirectory title="Mutual Fund Directory" funds={null} />;
  return (
    <>
      <CategoryJsonLd
        category={funds[0].category}
        categorySlug={categorySlugValue}
        fundCount={funds.length}
        funds={funds.map((f) => ({
          schemeName: f.scheme_name,
          amcSlug: f.amc_slug,
          fundSlug: f.fund_slug,
          category: f.category,
        }))}
      />
      <CatalogDirectory breadcrumbs={<Breadcrumbs items={[{ label: 'Home', href: '/' }, { label: 'Mutual Funds', href: '/mutual-funds' }, { label: funds[0].category }]} />} title={`${funds[0].category} Mutual Funds`} funds={funds} />
    </>
  );
}
