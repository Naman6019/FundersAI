import type { MetadataRoute } from 'next';
import {
  AMC_REGISTRY,
  FUND_REGISTRY,
  CATEGORY_LIST,
  categorySlug,
  COMPARE_PAIRS,
  SYNTHESIS_VS_SLUGS,
} from '@/lib/fund-registry';

const BASE_URL = 'https://www.fundersai.co.in';

// Stable baseline release timestamp to prevent lastmod churn on uncached crawler fetches.
// Because lastmod is pinned, changeFrequency must not claim 'daily' — a fixed lastmod paired
// with a daily hint is self-contradictory and Google discards the pair.
const RELEASE_DATE = new Date('2026-08-15T00:00:00.000Z');

export default function sitemap(): MetadataRoute.Sitemap {
  const routes: MetadataRoute.Sitemap = [];

  // 1. Core Institutional & Marketing Pages (www.fundersai.co.in)
  const corePages: { path: string; priority: number; changeFrequency: MetadataRoute.Sitemap[number]['changeFrequency'] }[] = [
    { path: '', priority: 1.0, changeFrequency: 'weekly' },
    { path: '/research', priority: 0.95, changeFrequency: 'weekly' },
    { path: '/how-it-works', priority: 0.9, changeFrequency: 'weekly' },
    { path: '/intelligence', priority: 0.9, changeFrequency: 'weekly' },
    { path: '/pricing', priority: 0.95, changeFrequency: 'weekly' },
    { path: '/data-trust', priority: 0.9, changeFrequency: 'weekly' },
    { path: '/sample', priority: 0.8, changeFrequency: 'monthly' },
    { path: '/methodology', priority: 0.9, changeFrequency: 'monthly' },
    { path: '/methodology/data-sources', priority: 0.85, changeFrequency: 'monthly' },
    { path: '/methodology/formulas', priority: 0.85, changeFrequency: 'monthly' },
    { path: '/methodology/resolution', priority: 0.85, changeFrequency: 'monthly' },
    { path: '/methodology/guardrails', priority: 0.85, changeFrequency: 'monthly' },
    { path: '/about', priority: 0.7, changeFrequency: 'monthly' },
    { path: '/tools', priority: 0.95, changeFrequency: 'weekly' },
    { path: '/tools/portfolio-overlap', priority: 0.95, changeFrequency: 'weekly' },
    { path: '/tools/sip-calculator', priority: 0.95, changeFrequency: 'weekly' },
    { path: '/contact', priority: 0.6, changeFrequency: 'monthly' },
    { path: '/privacy', priority: 0.4, changeFrequency: 'monthly' },
    { path: '/terms', priority: 0.4, changeFrequency: 'monthly' },
  ];

  for (const page of corePages) {
    routes.push({
      url: `${BASE_URL}${page.path}`,
      lastModified: RELEASE_DATE,
      changeFrequency: page.changeFrequency,
      priority: page.priority,
    });
  }

  // 2. Educational & Research Guides (/learn)
  const learnSlugs = [
    'pe-ratio',
    'mutual-fund-comparison',
    'alpha-beta-sharpe',
    'large-cap-vs-flexi-cap',
    'reading-stock-fundamentals',
  ];

  routes.push({
    url: `${BASE_URL}/learn`,
    lastModified: RELEASE_DATE,
    changeFrequency: 'weekly',
    priority: 0.9,
  });

  for (const slug of learnSlugs) {
    routes.push({
      url: `${BASE_URL}/learn/${slug}`,
      lastModified: RELEASE_DATE,
      changeFrequency: 'monthly',
      priority: 0.85,
    });
  }

  // 3. Mutual Fund Directory Hub & High-Value SEO Entities
  // 3a. Hub Page
  routes.push({
    url: `${BASE_URL}/mutual-funds`,
    lastModified: RELEASE_DATE,
    changeFrequency: 'weekly',
    priority: 0.95,
  });

  // 3b. SEBI Category Pages
  for (const cat of CATEGORY_LIST) {
    routes.push({
      url: `${BASE_URL}/mutual-funds/category/${categorySlug(cat)}`,
      lastModified: RELEASE_DATE,
      changeFrequency: 'weekly',
      priority: 0.9,
    });
  }

  // 3c. AMC Hub Pages
  for (const amc of AMC_REGISTRY) {
    routes.push({
      url: `${BASE_URL}/mutual-funds/${amc.slug}`,
      lastModified: RELEASE_DATE,
      changeFrequency: 'weekly',
      priority: 0.85,
    });
  }

  // 3d. Individual Scheme Factsheets
  for (const fund of FUND_REGISTRY) {
    routes.push({
      url: `${BASE_URL}/mutual-funds/${fund.amcSlug}/${fund.fundSlug}`,
      lastModified: RELEASE_DATE,
      changeFrequency: 'weekly',
      priority: 0.85,
    });
  }

  // 3e. Head-to-Head Comparison Hub & Pages
  routes.push({
    url: `${BASE_URL}/compare`,
    lastModified: RELEASE_DATE,
    changeFrequency: 'weekly',
    priority: 0.9,
  });

  for (const cp of COMPARE_PAIRS) {
    routes.push({
      url: `${BASE_URL}/compare/${cp.pair}`,
      lastModified: RELEASE_DATE,
      changeFrequency: 'weekly',
      priority: 0.85,
    });
  }

  // 4. Synthesis Studio (synthesis.fundersai.co.in)
  //
  // Cross-host entries in a sitemap served from www are only honoured when Google can tie
  // the hosts together: synthesis.fundersai.co.in must be a verified property (or covered by
  // a fundersai.co.in domain property), and its robots.txt must point at this sitemap — it
  // does, since app/robots.ts is served on both hosts.
  //
  // Only indexable studio pages belong here. The generate and dashboard routes are noindex
  // session surfaces, and the landing page is listed at the URL its canonical names (the bare
  // subdomain root, which middleware rewrites) so the sitemap and the canonical agree.
  const SYNTHESIS_URL = 'https://synthesis.fundersai.co.in';

  routes.push({
    url: SYNTHESIS_URL,
    lastModified: RELEASE_DATE,
    changeFrequency: 'weekly',
    priority: 0.95,
  });

  for (const path of ['/synthesis/methodology', '/synthesis/supported-funds']) {
    routes.push({
      url: `${SYNTHESIS_URL}${path}`,
      lastModified: RELEASE_DATE,
      changeFrequency: 'monthly',
      priority: 0.8,
    });
  }

  for (const slug of SYNTHESIS_VS_SLUGS) {
    routes.push({
      url: `${SYNTHESIS_URL}/synthesis/vs/${slug}`,
      lastModified: RELEASE_DATE,
      changeFrequency: 'weekly',
      priority: 0.75,
    });
  }

  for (const cat of CATEGORY_LIST) {
    routes.push({
      url: `${SYNTHESIS_URL}/synthesis/category/${categorySlug(cat)}`,
      lastModified: RELEASE_DATE,
      changeFrequency: 'weekly',
      priority: 0.7,
    });
  }

  return routes;
}
