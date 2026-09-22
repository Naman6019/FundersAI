import type { Metadata } from 'next';
import { notFound, permanentRedirect } from 'next/navigation';
import Link from 'next/link';
import { tryGetPublishedFund, tryGetCatalogUrlRedirect } from '@/lib/mf/catalog';
import { categorySlug, getFundBySchemeCode, getPeerFunds } from '@/lib/fund-registry';
import { FundJsonLd, fundFaqs, type FundJsonLdFund } from '@/components/seo/JsonLd';
import { CatalogUnavailable } from '@/components/funds/CatalogDirectory';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';

// Check freshness on every request; stale ISR HTML must not bypass the gate.
export const dynamic = 'force-dynamic';
export const dynamicParams = true;
type Props = { params: Promise<{ amcSlug: string; fundSlug: string }> };

/*
 * The live catalog carries NAV and computed CAGR; the static registry carries the benchmark
 * index, plan/option and any former name. Both are needed to describe a fund honestly, so
 * they are merged on scheme code rather than one replacing the other. A catalog fund absent
 * from the registry still renders — it simply omits the fields the registry alone supplies.
 */
type MergedFund = {
  scheme_code: string;
  amc_slug: string;
  fund_slug: string;
  scheme_name: string;
  amc_name: string;
  category: string;
  plan: string;
  option: string;
  benchmark?: string;
  formerName?: string;
  metrics: {
    method_version: string; nav: number; nav_date: string; history_start: string;
    observation_count: number; cagr_1y: number; cagr_3y: number | null; cagr_5y: number | null;
  };
};

// The schema component takes the camelCase shape; keep the adapter in one place so the page
// body and the structured data can never disagree about what the fund is.
function toSchemaFund(fund: MergedFund): FundJsonLdFund {
  return {
    schemeCode: fund.scheme_code,
    schemeName: fund.scheme_name,
    amcSlug: fund.amc_slug,
    amcName: fund.amc_name,
    fundSlug: fund.fund_slug,
    category: fund.category,
    plan: fund.plan,
    option: fund.option,
    benchmark: fund.benchmark,
    formerName: fund.formerName,
    metrics: fund.metrics,
  };
}

async function requiredFund(params: Props['params']): Promise<MergedFund | undefined> {
  const { amcSlug, fundSlug } = await params;
  const fund = await tryGetPublishedFund(amcSlug, fundSlug);
  // `undefined` is an infrastructure failure and must stay distinguishable from a definitive
  // missing fund, which is a real 404. Flattening both to `null` made a transient outage
  // emit a `noindex` tag on a live page.
  if (fund === undefined) return undefined;
  if (fund === null) {
    // A retired URL must redirect permanently, not 404. Published catalog URLs are immutable, so
    // a slug correction is recorded as a reviewed redirect; without this lookup the old path
    // would become an unannounced 404 on a page that may already be ranking.
    const target = await tryGetCatalogUrlRedirect(amcSlug, fundSlug);
    // On a redirect-lookup failure, throw rather than 404: the URL may well have moved, and a
    // cached 404 for a live page is the harmful outcome.
    if (target === undefined) throw new Error('Catalog redirect lookup failed');
    if (target) permanentRedirect(`/mutual-funds/${target.amcSlug}/${target.fundSlug}`);
    notFound();
  }

  const entry = getFundBySchemeCode(Number(fund.scheme_code));
  return {
    ...fund,
    scheme_code: fund.scheme_code,
    amc_slug: fund.amc_slug,
    fund_slug: fund.fund_slug,
    scheme_name: fund.scheme_name,
    amc_name: fund.amc_name,
    category: fund.category,
    plan: entry?.plan ?? 'Direct',
    option: entry?.option ?? 'Growth',
    benchmark: entry?.benchmark,
    formerName: entry?.formerName,
  };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const resolved = await params;
  const fund = await requiredFund(params);
  // Infra failure: keep the canonical and stay indexable rather than publishing noindex.
  if (!fund) return { title: 'Mutual Fund Directory | FundersAI',
    alternates: { canonical: `https://www.fundersai.co.in/mutual-funds/${resolved.amcSlug}/${resolved.fundSlug}` } };

  const m = fund.metrics;
  // The former name is what much of the search demand still uses ("hdfc top 100 fund"), so it
  // belongs in the description; the current SEBI name stays first in the title for correctness.
  return {
    title: `${fund.scheme_name} – NAV ₹${m.nav.toFixed(4)} & Returns | FundersAI`,
    description: `${fund.scheme_name}${fund.formerName ? ` (formerly ${fund.formerName})` : ''} — ${fund.category} Direct Growth. NAV ₹${m.nav.toFixed(4)} dated ${m.nav_date}, 1Y/3Y/5Y annualised returns${fund.benchmark ? `, benchmark ${fund.benchmark}` : ''}, AMFI code ${fund.scheme_code}. Research only.`,
    alternates: { canonical: `https://www.fundersai.co.in/mutual-funds/${fund.amc_slug}/${fund.fund_slug}` },
    openGraph: {
      title: `${fund.scheme_name} – NAV & Returns | FundersAI`,
      description: `Deterministic NAV, annualised returns and benchmark for ${fund.scheme_name}.`,
      url: `https://www.fundersai.co.in/mutual-funds/${fund.amc_slug}/${fund.fund_slug}`,
    },
  };
}

function fmtPct(value: number | null): string {
  return value == null ? 'Insufficient history' : `${value.toFixed(2)}%`;
}

export default async function Page({ params }: Props) {
  const fund = await requiredFund(params);
  if (!fund) return <CatalogUnavailable title="Mutual Fund Directory" />;

  const m = fund.metrics;
  const schemaFund = toSchemaFund(fund);
  const faqs = fundFaqs(schemaFund);
  const peers = getPeerFunds(Number(fund.scheme_code), 4);

  // Only rows we actually hold a value for are shown; an empty cell would read as a claim.
  const facts: Array<[string, string]> = [
    ['Fund house', fund.amc_name],
    ['AMFI scheme code', String(fund.scheme_code)],
    ['SEBI category', fund.category],
    ['Plan', fund.plan],
    ['Option', fund.option],
    ...(fund.benchmark ? [['Benchmark index', fund.benchmark] as [string, string]] : []),
    ...(fund.formerName ? [['Former name', fund.formerName] as [string, string]] : []),
    ['NAV date', m.nav_date],
    ['NAV history begins', m.history_start],
    ['Observations', `${m.observation_count} unique NAV points`],
    ['Method', m.method_version],
  ];

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <FundJsonLd fund={schemaFund} />
      <EcosystemHeader currentApp="mutual-funds" />
      <main className="mx-auto max-w-5xl px-5 py-12 space-y-8">
        <Breadcrumbs items={[{ label: 'Home', href: '/' },
          { label: 'Mutual Funds', href: '/mutual-funds' },
          { label: fund.amc_name, href: `/mutual-funds/${fund.amc_slug}` },
          { label: fund.scheme_name }]} />

        <div>
          <h1 className="text-3xl font-bold">{fund.scheme_name}</h1>
          {fund.formerName && (
            <p className="mt-2 text-sm text-muted-foreground">
              Previously named <span className="font-medium text-foreground">{fund.formerName}</span>. Renamed under SEBI
              re-categorisation; AMFI scheme code {fund.scheme_code} and its NAV history are unchanged.
            </p>
          )}
          <p className="mt-2">{fund.category} · {fund.plan} · {fund.option} · AMFI code {fund.scheme_code}</p>
        </div>

        <section className="rounded-xl border p-6 space-y-3">
          <h2 className="text-xl font-semibold">NAV and returns</h2>
          <p className="text-2xl">₹{m.nav.toFixed(4)}</p>
          <p>As of {m.nav_date}</p>
          <table className="w-full text-left">
            <caption className="text-left">Annualised returns (CAGR) ending {m.nav_date}</caption>
            <thead><tr><th scope="col">Period</th><th scope="col">CAGR</th></tr></thead>
            <tbody>{([['1 year', m.cagr_1y], ['3 years', m.cagr_3y], ['5 years', m.cagr_5y]] as const).map(([label, value]) =>
              <tr key={label}><th scope="row">{label}</th><td>{fmtPct(value)}</td></tr>)}</tbody>
          </table>
          <p className="text-sm text-muted-foreground">
            A period reads &ldquo;Insufficient history&rdquo; when the stored NAV series does not cover the full window.
            FundersAI does not extrapolate a partial window into a full-period figure.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Fund facts</h2>
          <table className="w-full text-left">
            <caption className="text-left">Scheme identity and evidence coverage</caption>
            <tbody>{facts.map(([label, value]) =>
              <tr key={label} className="border-b border-white/5">
                <th scope="row" className="py-2 pr-4 font-medium">{label}</th>
                <td className="py-2">{value}</td>
              </tr>)}</tbody>
          </table>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Frequently asked questions</h2>
          {faqs.map((faq) => (
            <div key={faq.q} className="rounded-xl border p-5 space-y-2">
              <h3 className="font-semibold">{faq.q}</h3>
              <p className="text-sm text-muted-foreground">{faq.a}</p>
            </div>
          ))}
        </section>

        {peers.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">Related funds to compare</h2>
            <p className="text-sm text-muted-foreground">
              Same-category schemes from the FundersAI registry. Peers by SEBI category, not recommendations.
            </p>
            <div className="flex flex-wrap gap-2">
              {peers.map((peer) => (
                <Link key={peer.fundSlug} href={`/mutual-funds/${peer.amcSlug}/${peer.fundSlug}`}
                  className="rounded-full border px-3.5 py-1.5 text-xs font-medium hover:border-white/30">
                  {peer.schemeName}
                </Link>
              ))}
            </div>
            <div className="flex flex-wrap gap-4 text-sm">
              <Link href="/compare">All head-to-head comparisons</Link>
              <Link href="/tools/portfolio-overlap">Check portfolio overlap</Link>
              <Link href={`/mutual-funds/category/${categorySlug(fund.category)}`}>{fund.category} funds</Link>
            </div>
          </section>
        )}

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Sources and method</h2>
          <p>NAV history supplied by <a href={`https://api.mfapi.in/mf/${fund.scheme_code}`} rel="noreferrer">MFapi</a>,
            originating from the official AMFI daily NAV feed under scheme code {fund.scheme_code}.
            FundersAI computes annualised returns using actual elapsed days and a 365-day year. Each period requires full
            history, at least 240 observations per year, and no gap exceeding seven calendar days.</p>
          <p>Stored history begins {m.history_start}; {m.observation_count} unique observations. Method: {m.method_version}.</p>
          <p className="text-sm text-muted-foreground">
            Expense ratio, AUM, fund manager, official holdings, exit load and riskometer are not published on this page:
            they require an official AMC factsheet that has passed FundersAI&apos;s evidence gate for this scheme. Their
            absence here is a coverage limit, not a claim that they are unavailable from the AMC.
          </p>
        </section>

        <p>Research only. This is not personalized investment advice. Past performance does not guarantee future returns.</p>
        <Link href="/methodology">Full methodology</Link>
      </main><PublicFooter />
    </div>
  );
}
