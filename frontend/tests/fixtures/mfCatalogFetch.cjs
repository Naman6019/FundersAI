// Loaded only by mfCatalogHttpSmoke.mjs in its child Next.js process.
const originalFetch = global.fetch;
global.fetch = async (input, init) => {
  const url = new URL(typeof input === 'string' ? input : input.url || input.toString());
  if (!url.pathname.endsWith('/rest/v1/mf_page_catalog')) return originalFetch(input, init);
  const amc = url.searchParams.get('amc_slug');
  const slug = url.searchParams.get('fund_slug');
  if (amc === 'eq.outage') return Response.json({ message: 'Synthetic database outage' }, { status: 503 });
  const fund = { scheme_code: '120503', amc_slug: 'hdfc', fund_slug: 'hdfc-flexi-cap-fund',
    scheme_name: 'Synthetic Catalog Fund Direct Growth', amc_name: 'HDFC Mutual Fund', category: 'Flexi Cap',
    is_published: true, gate_reasons: [], metrics: { method_version: 'catalog_nav_v1', nav: 123.45,
      nav_date: new Date().toISOString().slice(0, 10), history_start: '2020-01-01', observation_count: 1500,
      cagr_1y: 10, cagr_3y: null, cagr_5y: null } };
  if (slug === 'eq.rejected') return Response.json([{ ...fund, is_published: false }]);
  if (slug && slug !== 'eq.hdfc-flexi-cap-fund') return Response.json([]);
  return Response.json([fund]);
};
