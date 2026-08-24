import React from 'react';
import type { FundEntry, AmcEntry } from '@/lib/fund-registry';

interface FundJsonLdProps {
  fund: FundEntry;
  amc?: AmcEntry;
}

export function FundJsonLd({ fund, amc }: FundJsonLdProps) {
  const fundUrl = `https://www.fundersai.co.in/mutual-funds/${fund.amcSlug}/${fund.fundSlug}`;
  const amcUrl = `https://www.fundersai.co.in/mutual-funds/${fund.amcSlug}`;

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
        'feesAndCommissionsSpecification': `Expense ratio and exit load per official ${fund.amcName} SID. Direct plan has zero distributor commission.`,
        'description': `${fund.schemeName} is a ${fund.category} mutual fund offered by ${fund.amcName}. Plan: ${fund.plan}, Option: ${fund.option}, Benchmark: ${fund.benchmark}, AMFI Scheme Code: ${fund.schemeCode}.`,
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
        'mainEntity': [
          {
            '@type': 'Question',
            'name': `What is the benchmark index for ${fund.schemeName}?`,
            'acceptedAnswer': {
              '@type': 'Answer',
              'text': `${fund.schemeName} is benchmarked against ${fund.benchmark} as per official SEBI and AMC Scheme Information Documents (SID).`,
            },
          },
          {
            '@type': 'Question',
            'name': `What is the difference between Direct and Regular plans for this fund?`,
            'acceptedAnswer': {
              '@type': 'Answer',
              'text': `The Direct Plan (${fund.schemeName}) has a lower Total Expense Ratio (TER) because no distributor commissions are paid, resulting in higher compounded returns over the long term compared to Regular plans.`,
            },
          },
          {
            '@type': 'Question',
            'name': `Where is the NAV data for ${fund.schemeName} sourced from?`,
            'acceptedAnswer': {
              '@type': 'Answer',
              'text': `NAV history is sourced directly from official Association of Mutual Funds in India (AMFI) feeds under scheme code ${fund.schemeCode} on every business day.`,
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
            'name': 'Compare',
            'item': 'https://www.fundersai.co.in/mutual-funds',
          },
          {
            '@type': 'ListItem',
            'position': 3,
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

interface CategoryJsonLdProps {
  category: string;
  categorySlug: string;
  fundCount: number;
}

export function CategoryJsonLd({ category, categorySlug, fundCount }: CategoryJsonLdProps) {
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
}

export function ArticleJsonLd({
  title,
  description,
  slug,
  datePublished = '2026-06-01T00:00:00.000Z',
  dateModified = '2026-08-15T00:00:00.000Z',
}: ArticleJsonLdProps) {
  const articleUrl = `https://www.fundersai.co.in/learn/${slug}`;

  const schema = {
    '@context': 'https://schema.org',
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
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

interface DirectoryJsonLdProps {
  funds: FundEntry[];
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
        'mainEntity': {
          '@type': 'ItemList',
          'numberOfItems': funds.length,
          'itemListElement': funds.map((f, i) => ({
            '@type': 'ListItem',
            'position': i + 1,
            'url': `https://www.fundersai.co.in/mutual-funds/${f.amcSlug}/${f.fundSlug}`,
            'name': f.schemeName,
          })),
        },
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

