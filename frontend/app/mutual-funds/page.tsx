import type { Metadata } from 'next';
import CatalogDirectory from '@/components/funds/CatalogDirectory';
import { DirectoryJsonLd } from '@/components/seo/JsonLd';
import { tryGetPublishedFunds } from '@/lib/mf/catalog';
export const dynamic = 'force-dynamic';
const metadata: Metadata = {
  title: 'Mutual Fund Directory | FundersAI',
  description: 'Eligible Direct Growth mutual funds with dated NAV and full-window returns.',
  alternates: { canonical: 'https://www.fundersai.co.in/mutual-funds' },
};

export async function generateMetadata(): Promise<Metadata> {
  const funds = await tryGetPublishedFunds();

  // An infrastructure failure must not publish a `noindex` tag. Doing so left Google
  // oscillating between "Excluded by 'noindex' tag" and indexed as the catalog blipped.
  // Only a definitively empty catalog is thin enough to withhold from the index.
  if (funds === undefined) return metadata;
  if (funds.length > 0) return metadata;

  // Do not let an unpublished catalog create a thin indexed directory.
  return { ...metadata, robots: { index: false, follow: true } };
}

export default async function Page() {
  const funds = (await tryGetPublishedFunds()) ?? null;
  return (
    <>
      {/* Only a successful read is described as a collection; an outage must not assert an
          ItemList of funds we could not verify. */}
      {funds !== null && funds.length > 0 && (
        <DirectoryJsonLd
          funds={funds.map((f) => ({
            schemeName: f.scheme_name,
            amcSlug: f.amc_slug,
            fundSlug: f.fund_slug,
            category: f.category,
          }))}
        />
      )}
      <CatalogDirectory title="Mutual Fund Directory" funds={funds} />
    </>
  );
}
