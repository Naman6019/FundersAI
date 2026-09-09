import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { getPublishedFund } from '@/lib/mf/catalog';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';

// Check freshness on every request; stale ISR HTML must not bypass the gate.
export const dynamic = 'force-dynamic';
export const dynamicParams = true;
type Props = { params: Promise<{ amcSlug: string; fundSlug: string }> };
async function requiredFund(params: Props['params']) {
  const { amcSlug, fundSlug } = await params;
  const fund = await getPublishedFund(amcSlug, fundSlug);
  if (!fund) notFound();
  return fund;
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const fund = await requiredFund(params);
  return { title: `${fund.scheme_name} – NAV & Returns | FundersAI`,
    description: `NAV dated ${fund.metrics.nav_date} and full-window returns for ${fund.scheme_name}. Research only.`,
    alternates: { canonical: `https://www.fundersai.co.in/mutual-funds/${fund.amc_slug}/${fund.fund_slug}` } };
}
export default async function Page({ params }: Props) {
  const fund = await requiredFund(params);
  const m = fund.metrics;
  return <div className="min-h-dvh bg-background text-foreground">
    <EcosystemHeader currentApp="mutual-funds" />
    <main className="mx-auto max-w-5xl px-5 py-12 space-y-8">
      <Breadcrumbs items={[{ label: 'Home', href: '/' },
        { label: 'Mutual Funds', href: '/mutual-funds' },
        { label: fund.amc_name, href: `/mutual-funds/${fund.amc_slug}` },
        { label: fund.scheme_name }]} />
      <h1 className="text-3xl font-bold">{fund.scheme_name}</h1>
      <p>{fund.category} · Direct · Growth · AMFI code {fund.scheme_code}</p>
      <section className="rounded-xl border p-6 space-y-3">
        <h2 className="text-xl font-semibold">NAV and returns</h2>
        <p className="text-2xl">₹{m.nav.toFixed(4)}</p><p>As of {m.nav_date}</p>
        <table className="w-full text-left"><caption className="text-left">Annualized returns ending {m.nav_date}</caption>
          <thead><tr><th scope="col">Period</th><th scope="col">CAGR</th></tr></thead>
          <tbody>{([['1 year', m.cagr_1y], ['3 years', m.cagr_3y], ['5 years', m.cagr_5y]] as const).map(([label, value]) =>
            <tr key={label}><th scope="row">{label}</th><td>{value == null ? 'Insufficient history' : `${value.toFixed(2)}%`}</td></tr>)}</tbody>
        </table>
      </section>
      <section className="space-y-3"><h2 className="text-xl font-semibold">Sources and method</h2>
        <p>NAV history supplied by <a href={`https://api.mfapi.in/mf/${fund.scheme_code}`} rel="noreferrer">MFapi</a>.
          FundersAI computes annualized returns using actual elapsed days and a 365-day year. Each period requires full history, at least 250 observations per year, and no gap exceeding seven calendar days.</p>
        <p>Stored history begins {m.history_start}; {m.observation_count} unique observations. Method: {m.method_version}.</p>
        <p>Risk metrics, holdings, expense ratio, manager and benchmark evidence are not available on this page.</p>
      </section>
      <p>Research only. This is not personalized investment advice. Past performance does not guarantee future returns.</p>
      <Link href="/methodology">Full methodology</Link>
    </main><PublicFooter />
  </div>;
}
