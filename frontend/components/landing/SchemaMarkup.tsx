import React from 'react';

export default function SchemaMarkup() {
  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        '@id': 'https://www.fundersai.co.in/#organization',
        'name': 'FundersAI',
        'url': 'https://www.fundersai.co.in',
        'logo': {
          '@type': 'ImageObject',
          '@id': 'https://www.fundersai.co.in/#logo',
          'url': 'https://www.fundersai.co.in/logo.png',
          'contentUrl': 'https://www.fundersai.co.in/logo.png',
          'width': 912,
          'height': 912,
          'caption': 'FundersAI',
        },
      },
      {
        '@type': 'WebSite',
        '@id': 'https://www.fundersai.co.in/#website',
        'name': 'FundersAI',
        'alternateName': 'FundersAI Research Workspace',
        'url': 'https://www.fundersai.co.in',
        'publisher': {
          '@id': 'https://www.fundersai.co.in/#organization',
        },
      },
      {
        '@type': 'SoftwareApplication',
        '@id': 'https://www.fundersai.co.in/#software',
        'name': 'FundersAI',
        'url': 'https://www.fundersai.co.in',
        'applicationCategory': 'FinanceApplication',
        'operatingSystem': 'All',
        'description': 'Research-first workspace for comparing Indian stocks and mutual funds with deterministic metrics, official-source evidence, and visible data limits.',
        'publisher': {
          '@id': 'https://www.fundersai.co.in/#organization',
        },
        'offers': {
          '@type': 'Offer',
          'price': '0',
          'priceCurrency': 'INR',
        },
      },
      {
        '@type': 'FAQPage',
        '@id': 'https://www.fundersai.co.in/#faq',
        'mainEntity': [
          {
            '@type': 'Question',
            'name': 'How do I compare Indian mutual funds side-by-side?',
            'acceptedAnswer': {
              '@type': 'Answer',
              'text': 'FundersAI provides a side-by-side research canvas for comparing available NAV, returns, risk, cost, holdings, and freshness data. Missing fields remain visible as limitations.',
            },
          },
          {
            '@type': 'Question',
            'name': 'Does FundersAI provide investment advisory or recommendations?',
            'acceptedAnswer': {
              '@type': 'Answer',
              'text': 'No. FundersAI is a research-only workspace. It does not provide buy, sell, or hold recommendations, and users should verify information independently.',
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
