import Link from 'next/link';
import type { CatalogFund } from '@/lib/mf/catalog';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import type { ReactNode } from 'react';

export default function CatalogDirectory({ title, funds, breadcrumbs }: { title: string; funds: CatalogFund[] | null; breadcrumbs?: ReactNode }) {
  if (funds === null) {
    return <div className="min-h-dvh bg-background text-foreground">
      <EcosystemHeader currentApp="mutual-funds" />
      <main className="mx-auto max-w-3xl px-5 py-12 space-y-6">
        {breadcrumbs}
        <h1 className="text-3xl font-bold">{title}</h1>
        <section className="rounded-xl border p-6 space-y-4">
          <p className="text-lg font-semibold">The verified fund directory is temporarily unavailable.</p>
          <p className="text-sm text-muted-foreground">We are validating coverage before publishing fund records. FundersAI does not substitute unverified data or recommendations.</p>
          <div className="flex flex-wrap gap-4 text-sm">
            <Link href="/methodology">Data methodology</Link>
            <Link href="/data-trust">Data trust</Link>
          </div>
        </section>
      </main><PublicFooter />
    </div>;
  }
  const amcs = [...new Map(funds.map(f => [f.amc_slug, f.amc_name])).entries()];
  return <div className="min-h-dvh bg-background text-foreground">
    <EcosystemHeader currentApp="mutual-funds" />
    <main className="mx-auto max-w-6xl px-5 py-12 space-y-8">
      {breadcrumbs}
      <h1 className="text-3xl font-bold">{title}</h1>
      <p>{funds.length} eligible Direct Growth schemes with dated NAV history. Research only.</p>
      <nav aria-label="Fund houses" className="flex flex-wrap gap-4">{amcs.map(([slug, name]) =>
        <Link key={slug} href={`/mutual-funds/${slug}`}>{name}</Link>)}</nav>
      <ul className="grid gap-4 sm:grid-cols-2">{funds.map(f => <li key={f.scheme_code} className="rounded-xl border p-5">
        <Link className="font-semibold" href={`/mutual-funds/${f.amc_slug}/${f.fund_slug}`}>{f.scheme_name}</Link>
        <p className="text-sm mt-2">{f.category} · NAV ₹{f.metrics.nav.toFixed(4)} as of {f.metrics.nav_date}</p>
      </li>)}</ul>
      <Link href="/methodology">Data methodology</Link>
    </main><PublicFooter />
  </div>;
}
