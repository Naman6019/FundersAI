import React from 'react';
import type { FundEntry } from '@/lib/fund-registry';

/**
 * The union of what the static registry and the live catalog can each supply. Everything
 * except identity is optional, because the catalog carries live NAV/CAGR while the registry
 * carries benchmark and former name. Emitting only fields we actually hold keeps the graph
 * free of invented figures — the research-only invariant forbids asserting them.
 */
export interface FundJsonLdFund {
  schemeCode: number | string;
  schemeName: string;
  amcSlug: string;
  amcName: string;
  fundSlug: string;
  category: string;
  plan?: string;
  option?: string;
  benchmark?: string;
  formerName?: string;
  metrics?: {
    nav?: number | null;
    nav_date?: string | null;
    cagr_1y?: number | null;
    cagr_3y?: number | null;
    cagr_5y?: number | null;
    history_start?: string | null;
    observation_count?: number | null;
  };
}

function pct(value: number | null | undefined): string | null {
  return typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(2)}%` : null;
}

/**
 * Questions and answers built only from held data. Returns are annualised CAGR computed by
 * FundersAI from AMFI NAV under `catalog_nav_v1`; a window with incomplete history is
 * omitted rather than extrapolated. Every answer here is also rendered visibly on the page —
 * FAQ markup whose text is absent from the page is ineligible for rich results.
 */
export function fundFaqs(fund: FundJsonLdFund): Array<{ q: string; a: string }> {
  const m = fund.metrics;
  const faqs: Array<{ q: string; a: string }> = [];
  const code = String(fund.schemeCode);

  if (fund.benchmark) {
    faqs.push({
      q: `What is the benchmark index for ${fund.schemeName}?`,
      a: `${fund.schemeName} is benchmarked against ${fund.benchmark} as per official SEBI and AMC Scheme Information Documents (SID).`,
    });
  }

  if (fund.formerName) {
    faqs.push({
      q: `Is ${fund.schemeName} the same as ${fund.formerName}?`,
      a: `Yes. ${fund.formerName} was the fund's earlier name. It was renamed to ${fund.schemeName} under SEBI's re-categorisation rules, and the AMFI scheme code ${code} is unchanged, so NAV history is continuous across the rename.`,
    });
  }

  const cagrParts = ([
    ['1 year', m?.cagr_1y],
    ['3 years', m?.cagr_3y],
    ['5 years', m?.cagr_5y],
  ] as const)
    .map(([label, value]) => (pct(value) ? `${label}: ${pct(value)}` : null))
    .filter(Boolean);

  if (cagrParts.length > 0) {
    faqs.push({
      q: `What are the annualised returns for ${fund.schemeName}?`,
      a: `Annualised returns (CAGR) calculated by FundersAI from AMFI NAV history as of ${m?.nav_date}: ${cagrParts.join(', ')}. Each window requires full history coverage, so a period with insufficient data is omitted rather than estimated. Past performance does not guarantee future returns.`,
    });
  }

  faqs.push({
    q: `What is the difference between Direct and Regular plans for this fund?`,
    a: `The Direct Plan has a lower Total Expense Ratio (TER) because no distributor commission is paid, which compounds into higher returns over the long term compared to the Regular plan of the same scheme.`,
  });

  faqs.push({
    q: `Where is the NAV data for ${fund.schemeName} sourced from?`,
    a: `NAV history is sourced from the official Association of Mutual Funds in India (AMFI) feed under scheme code ${code}, updated every business day.`,
  });

  return faqs;
}

export function FundJsonLd({ fund }: { fund: FundJsonLdFund }) {
  const fundUrl = `https://www.fundersai.co.in/mutual-funds/${fund.amcSlug}/${fund.fundSlug}`;
  const amcUrl = `https://www.fundersai.co.in/mutual-funds/${fund.amcSlug}`;
  const m = fund.metrics;

  // Identity only. Metrics live in the FAQ answers and description, because FinancialProduct
  // defines no returns property and inventing one would be a fabricated claim.
  const facts = [
    `SEBI category: ${fund.category}`,
    fund.plan ? `Plan: ${fund.plan}` : null,
    fund.option ? `Option: ${fund.option}` : null,
    fund.benchmark ? `Benchmark: ${fund.benchmark}` : null,
    `AMFI Scheme Code: ${fund.schemeCode}`,
  ].filter(Boolean);

  const performance =
    m?.nav != null && m?.nav_date
      ? ` NAV ${m.nav.toFixed(4)} as of ${m.nav_date}.${pct(m.cagr_1y) ? ` Annualised 1Y return ${pct(m.cagr_1y)}.` : ''}`
      : '';

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'FinancialProduct',
        '@id': `${fundUrl}/#product`,
        'name': fund.schemeName,
        'url': fundUrl,
        'category': fund.category,
        'provider': {
          '@type': 'FinancialService',
          '@id': `${amcUrl}/#organization`,
          'name': fund.amcName,
          'url': amcUrl,
        },
        'feesAndCommissionsSpecification': `Expense ratio and exit load are set out in the official ${fund.amcName} Scheme Information Document. ${fund.plan === 'Direct' ? 'The Direct plan pays no distributor commission.' : 'The Regular plan includes distributor commission in its expense ratio.'}`,
        'description': `${fund.schemeName} is a ${fund.category} mutual fund offered by ${fund.amcName}.${fund.formerName ? ` It was formerly named ${fund.formerName}.` : ''} ${facts.join(', ')}.${performance} Figures are deterministic calculations from official AMFI sources, presented for research only.`,
      },
      {
        '@type': 'BreadcrumbList',
        '@id': `${fundUrl}/#breadcrumb`,
        'itemListElement': [
          {
            '@type': 'ListItem',
            'position': 1,
            'name': 'Home',
            'item': 'https://www.fundersai.co.in',
          },
          {
            '@type': 'ListItem',
            'position': 2,
            'name': 'Mutual Funds',
            'item': 'https://www.fundersai.co.in/mutual-funds',
          },
          {
            '@type': 'ListItem',
            'position': 3,
            'name': fund.amcName,
            'item': amcUrl,
          },
          {
            '@type': 'ListItem',
            'position': 4,
            'name': fund.schemeName,
            'item': fundUrl,
          },
        ],
      },
      {
        '@type': 'FAQPage',
        '@id': `${fundUrl}/#faq`,
        'mainEntity': fundFaqs(fund).map((faq) => ({
          '@type': 'Question',
          'name': faq.q,
          'acceptedAnswer': { '@type': 'Answer', 'text': faq.a },
        })),
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

interface CompareJsonLdProps {
  fundA: FundEntry;
  fundB: FundEntry;
  pair: string;
}

export function CompareJsonLd({ fundA, fundB, pair }: CompareJsonLdProps) {
  const compareUrl = `https://www.fundersai.co.in/compare/${pair}`;

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebPage',
        '@id': `${compareUrl}/#webpage`,
        'url': compareUrl,
        'name': `${fundA.schemeName} vs ${fundB.schemeName} Comparison`,
        'description': `Side-by-side comparison of ${fundA.schemeName} and ${fundB.schemeName} with CAGR, Sharpe ratio, expense ratios, portfolio overlap, and risk metrics.`,
      },
      {
        '@type': 'BreadcrumbList',
        '@id': `${compareUrl}/#breadcrumb`,
        'itemListElement': [
          {
            '@type': 'ListItem',
            'position': 1,
            'name': 'Home',
            'item': 'https://www.fundersai.co.in',
          },
          {
            '@type': 'ListItem',
            'position': 2,
            'name': 'Mutual Funds',
            'item': 'https://www.fundersai.co.in/mutual-funds',
          },
          {
            '@type': 'ListItem',
            'position': 3,
            'name': 'Compare',
            'item': 'https://www.fundersai.co.in/compare',
          },
          {
            '@type': 'ListItem',
            'position': 4,
            'name': `${fundA.schemeName} vs ${fundB.schemeName}`,
            'item': compareUrl,
          },
        ],
      },
      {
        '@type': 'FAQPage',
        '@id': `${compareUrl}/#faq`,
        'mainEntity': [
          {
            '@type': 'Question',
            'name': `How do ${fundA.schemeName} and ${fundB.schemeName} compare in terms of category?`,
            'acceptedAnswer': {
              '@type': 'Answer',
              'text': `${fundA.schemeName} belongs to the ${fundA.category} category (Benchmark: ${fundA.benchmark}), while ${fundB.schemeName} belongs to the ${fundB.category} category (Benchmark: ${fundB.benchmark}).`,
            },
          },
          {
            '@type': 'Question',
            'name': `Which fund has a lower expense ratio between the two?`,
            'acceptedAnswer': {
              '@type': 'Answer',
              'text': `Expense ratios are published monthly in official AMC factsheets. Direct plans for both ${fundA.amcName} and ${fundB.amcName} offer lower TER compared to regular plans. Inspect the side-by-side table on FundersAI for current figures.`,
            },
          },
        ],
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

/**
 * Canonical listing shape for directory and category ItemLists. Deliberately decoupled from
 * `CatalogFund`'s snake_case so the schema component does not depend on the data layer, and
 * so a registry row can be listed without a translation step.
 */
export interface DirectoryListingFund {
  schemeName: string;
  amcSlug: string;
  fundSlug: string;
  category: string;
}

function itemList(ownerUrl: string, funds: DirectoryListingFund[]) {
  return {
    '@type': 'ItemList',
    '@id': `${ownerUrl}/#itemlist`,
    'numberOfItems': funds.length,
    'itemListElement': funds.map((f, i) => ({
      '@type': 'ListItem',
      'position': i + 1,
      'url': `https://www.fundersai.co.in/mutual-funds/${f.amcSlug}/${f.fundSlug}`,
      'name': f.schemeName,
    })),
  };
}

interface CategoryJsonLdProps {
  category: string;
  categorySlug: string;
  fundCount: number;
  /** Catalog rows to list as ItemList children. Optional: the header graph stands alone. */
  funds?: DirectoryListingFund[];
}

export function CategoryJsonLd({ category, categorySlug, fundCount, funds = [] }: CategoryJsonLdProps) {
  const categoryUrl = `https://www.fundersai.co.in/mutual-funds/category/${categorySlug}`;

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'CollectionPage',
        '@id': `${categoryUrl}/#collection`,
        'url': categoryUrl,
        'name': `${category} Mutual Funds in India`,
        'description': `Directory of ${category} mutual funds in India. Includes ${fundCount} indexed funds with deterministic metrics from AMFI and AMC disclosures.`,
        ...(funds.length > 0 ? { 'mainEntity': itemList(categoryUrl, funds) } : {}),
      },
      {
        '@type': 'BreadcrumbList',
        '@id': `${categoryUrl}/#breadcrumb`,
        'itemListElement': [
          {
            '@type': 'ListItem',
            'position': 1,
            'name': 'Home',
            'item': 'https://www.fundersai.co.in',
          },
          {
            '@type': 'ListItem',
            'position': 2,
            'name': 'Mutual Funds',
            'item': 'https://www.fundersai.co.in/mutual-funds',
          },
          {
            '@type': 'ListItem',
            'position': 3,
            'name': `${category} Funds`,
            'item': categoryUrl,
          },
        ],
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

interface ArticleJsonLdProps {
  title: string;
  description: string;
  slug: string;
  datePublished?: string;
  dateModified?: string;
  /**
   * Questions rendered visibly on the page. Google requires FAQ text to be present in the
   * page body, so pass the same array the component renders rather than a separate copy.
   */
  faqs?: Array<{ q: string; a: string }>;
}

export function ArticleJsonLd({
  title,
  description,
  slug,
  datePublished = '2026-06-01T00:00:00.000Z',
  dateModified = '2026-09-22T00:00:00.000Z',
  faqs = [],
}: ArticleJsonLdProps) {
  const articleUrl = `https://www.fundersai.co.in/learn/${slug}`;

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'TechArticle',
        '@id': `${articleUrl}/#article`,
        'headline': title,
        'description': description,
        'url': articleUrl,
        'datePublished': datePublished,
        'dateModified': dateModified,
        'inLanguage': 'en-IN',
        'publisher': {
          '@type': 'Organization',
          '@id': 'https://www.fundersai.co.in/#organization',
          'name': 'FundersAI',
          'url': 'https://www.fundersai.co.in',
        },
        'author': {
          '@type': 'Organization',
          'name': 'FundersAI Research Team',
        },
      },
      ...(faqs.length > 0
        ? [
            {
              '@type': 'FAQPage',
              '@id': `${articleUrl}/#faq`,
              'mainEntity': faqs.map((faq) => ({
                '@type': 'Question',
                'name': faq.q,
                'acceptedAnswer': { '@type': 'Answer', 'text': faq.a },
              })),
            },
          ]
        : []),
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

interface DirectoryJsonLdProps {
  funds: DirectoryListingFund[];
}

export function DirectoryJsonLd({ funds }: DirectoryJsonLdProps) {
  const directoryUrl = 'https://www.fundersai.co.in/mutual-funds';

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'CollectionPage',
        '@id': `${directoryUrl}/#collection`,
        'url': directoryUrl,
        'name': 'Indian Mutual Funds Screener & Directory | FundersAI',
        'description': 'Browse and filter Indian mutual funds by AMC house, SEBI category, and deterministic risk-adjusted return metrics.',
        'mainEntity': itemList(directoryUrl, funds),
      },
      {
        '@type': 'BreadcrumbList',
        '@id': `${directoryUrl}/#breadcrumb`,
        'itemListElement': [
          {
            '@type': 'ListItem',
            'position': 1,
            'name': 'Home',
            'item': 'https://www.fundersai.co.in',
          },
          {
            '@type': 'ListItem',
            'position': 2,
            'name': 'Mutual Funds',
            'item': directoryUrl,
          },
        ],
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

// ─── Comparison Index Schema Generator ──────────────────────────────────────

interface CompareIndexJsonLdProps {
  comparisons: { pair: string; nameA: string; nameB: string }[];
}

export function CompareIndexJsonLd({ comparisons }: CompareIndexJsonLdProps) {
  const indexUrl = 'https://www.fundersai.co.in/compare';

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'CollectionPage',
        '@id': `${indexUrl}/#collection`,
        'url': indexUrl,
        'name': 'Mutual Fund Head-to-Head Comparisons | FundersAI',
        'description': 'Side-by-side comparisons of Indian mutual funds — CAGR, Sharpe ratio, max drawdown, expense ratio, AUM, and portfolio overlap from official AMC sources.',
        'mainEntity': {
          '@type': 'ItemList',
          'numberOfItems': comparisons.length,
          'itemListElement': comparisons.map((c, i) => ({
            '@type': 'ListItem',
            'position': i + 1,
            'url': `${indexUrl}/${c.pair}`,
            'name': `${c.nameA} vs ${c.nameB}`,
          })),
        },
      },
      {
        '@type': 'BreadcrumbList',
        '@id': `${indexUrl}/#breadcrumb`,
        'itemListElement': [
          {
            '@type': 'ListItem',
            'position': 1,
            'name': 'Home',
            'item': 'https://www.fundersai.co.in',
          },
          {
            '@type': 'ListItem',
            'position': 2,
            'name': 'Compare',
            'item': indexUrl,
          },
        ],
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

// ─── Tool / WebApplication Schema Generator ─────────────────────────────────

interface ToolFaq {
  q: string;
  a: string;
}

interface ToolJsonLdProps {
  name: string;
  description: string;
  url: string;
  applicationCategory?: string;
  faqs?: ToolFaq[];
}

export function ToolJsonLd({
  name,
  description,
  url,
  applicationCategory = 'FinanceApplication',
  faqs = [],
}: ToolJsonLdProps) {
  const schema: Record<string, unknown> = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebApplication',
        '@id': `${url}/#software`,
        'name': name,
        'url': url,
        'description': description,
        'applicationCategory': applicationCategory,
        'operatingSystem': 'All',
        'browserRequirements': 'Requires JavaScript. Requires HTML5.',
        'offers': {
          '@type': 'Offer',
          'price': '0',
          'priceCurrency': 'INR',
        },
        'publisher': {
          '@type': 'Organization',
          'name': 'FundersAI',
          'url': 'https://www.fundersai.co.in',
        },
      },
      {
        '@type': 'BreadcrumbList',
        '@id': `${url}/#breadcrumb`,
        'itemListElement': [
          {
            '@type': 'ListItem',
            'position': 1,
            'name': 'Home',
            'item': 'https://www.fundersai.co.in',
          },
          {
            '@type': 'ListItem',
            'position': 2,
            'name': 'Tools',
            'item': 'https://www.fundersai.co.in/tools',
          },
          {
            '@type': 'ListItem',
            'position': 3,
            'name': name,
            'item': url,
          },
        ],
      },
      ...(faqs.length > 0
        ? [
            {
              '@type': 'FAQPage',
              '@id': `${url}/#faq`,
              'mainEntity': faqs.map((faq) => ({
                '@type': 'Question',
                'name': faq.q,
                'acceptedAnswer': {
                  '@type': 'Answer',
                  'text': faq.a,
                },
              })),
            },
          ]
        : []),
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

