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
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
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

export const getPublishedFund = cache(async (amcSlug: string, fundSlug: string): Promise<CatalogFund | null> => {
  const { data, error } = await client().from('mf_page_catalog').select('*')
    .eq('amc_slug', amcSlug).eq('fund_slug', fundSlug).maybeSingle();
  if (error) throw new Error('Catalog lookup failed', { cause: error });
  return data && isEligible(data as CatalogFund) ? data as CatalogFund : null;
});

export async function getPublishedAmcs() {
  const funds = await getPublishedFunds();
  return [...new Map(funds.map(f => [f.amc_slug, { slug: f.amc_slug, name: f.amc_name }])).values()];
}
