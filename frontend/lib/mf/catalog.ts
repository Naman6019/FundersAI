import 'server-only';
import { cache } from 'react';
import { createClient } from '@supabase/supabase-js';

export type CatalogFund = {
  scheme_code: string; amc_slug: string; fund_slug: string;
  scheme_name: string; amc_name: string; category: string;
  is_published: boolean; gate_reasons: string[];
  metrics: { method_version: string; nav: number; nav_date: string;
    history_start: string; observation_count: number;
    cagr_1y: number; cagr_3y: number | null; cagr_5y: number | null };
};

function client() {
  const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error('Catalog service credentials unavailable');
  return createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false },
    global: { fetch: (url, init) => fetch(url, { ...init, cache: 'no-store' }) } });
}

export function isEligible(fund: CatalogFund, now = Date.now()): boolean {
  const m = fund.metrics;
  const age = now - Date.parse(`${m?.nav_date}T00:00:00Z`);
  return fund.is_published && fund.gate_reasons.length === 0 && !!fund.category &&
    m?.method_version === 'catalog_nav_v1' && Number.isFinite(m.nav) && m.nav > 0 &&
    Number.isFinite(m.cagr_1y) && age >= 0 && age < 8 * 86400000;
}

export const getPublishedFunds = cache(async (): Promise<CatalogFund[]> => {
  const db = client();
  const funds: CatalogFund[] = [];
  for (let offset = 0; ; offset += 500) {
    const { data, error } = await db.from('mf_page_catalog').select('*')
      .eq('is_published', true).order('scheme_code').range(offset, offset + 499);
    if (error) throw new Error('Catalog lookup failed', { cause: error });
    funds.push(...(data as CatalogFund[]).filter(f => isEligible(f)));
    if (data.length < 500) break;
  }
  return funds;
});

// Directory discovery must never turn a catalog infrastructure outage into a false empty
// catalog, and callers must be able to tell the two apart: `undefined` denotes an
// infrastructure failure, while an empty array is a definitive "no eligible funds published".
// Collapsing both into `null` previously made a momentary outage indistinguishable from an
// empty catalog, so pages flipped to `noindex` and back on every failed read.
export async function tryGetPublishedFunds(): Promise<CatalogFund[] | undefined> {
  try {
    return await getPublishedFunds();
  } catch (error) {
    console.error('[mf-catalog] public catalog unavailable', {
      message: error instanceof Error ? error.message : 'Unknown catalog error',
    });
    return undefined;
  }
}

// `undefined` denotes an infrastructure failure; `null` remains a definitive missing/ineligible fund.
export async function tryGetPublishedFund(amcSlug: string, fundSlug: string): Promise<CatalogFund | null | undefined> {
  try {
    return await getPublishedFund(amcSlug, fundSlug);
  } catch (error) {
    console.error('[mf-catalog] public fund unavailable', {
      message: error instanceof Error ? error.message : 'Unknown catalog error',
    });
    return undefined;
  }
}

export const getPublishedFund = cache(async (amcSlug: string, fundSlug: string): Promise<CatalogFund | null> => {
  const { data, error } = await client().from('mf_page_catalog').select('*')
    .eq('amc_slug', amcSlug).eq('fund_slug', fundSlug).maybeSingle();
  if (error) throw new Error('Catalog lookup failed', { cause: error });
  return data && isEligible(data as CatalogFund) ? data as CatalogFund : null;
});

/**
 * Where a retired catalog URL should permanently redirect to, if anywhere.
 *
 * `mf_page_catalog` URLs are immutable once published, so a correction is always expressed as a
 * reviewed row in `mf_catalog_url_redirects`. This resolves the old path to the current one so
 * the route can issue a 308 instead of a 404. Returns `null` when the path was never a catalog
 * URL, which is what lets the route distinguish "moved" from "never existed" and still return a
 * real 404 for the latter.
 */
export const getCatalogUrlRedirect = cache(
  async (amcSlug: string, fundSlug: string): Promise<{ amcSlug: string; fundSlug: string } | null> => {
    const { data, error } = await client()
      .from('mf_catalog_url_redirects')
      .select('to_amc_slug,to_fund_slug')
      .eq('from_amc_slug', amcSlug)
      .eq('from_fund_slug', fundSlug)
      .maybeSingle();
    if (error) throw new Error('Catalog redirect lookup failed', { cause: error });
    return data ? { amcSlug: data.to_amc_slug, fundSlug: data.to_fund_slug } : null;
  },
);

export async function tryGetCatalogUrlRedirect(
  amcSlug: string,
  fundSlug: string,
): Promise<{ amcSlug: string; fundSlug: string } | null | undefined> {
  try {
    return await getCatalogUrlRedirect(amcSlug, fundSlug);
  } catch (error) {
    // `undefined` is an infrastructure failure and must not be mistaken for "no redirect",
    // which would render a 404 for a URL that actually moved.
    console.error('[mf-catalog] catalog redirect unavailable', {
      message: error instanceof Error ? error.message : 'Unknown catalog error',
    });
    return undefined;
  }
}

export async function getPublishedAmcs() {
  const funds = await getPublishedFunds();
  return [...new Map(funds.map(f => [f.amc_slug, { slug: f.amc_slug, name: f.amc_name }])).values()];
}
