import React from 'react';

export default function SchemaMarkup() {
  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'SoftwareApplication',
        '@id': 'https://fundersai.com/#software',
        'name': 'FundersAI',
        'url': 'https://fundersai.com',
        'applicationCategory': 'FinanceApplication',
        'operatingSystem': 'All',
        'description': 'Institutional-grade Indian mutual fund screening and side-by-side comparison workspace with explainable AI analysis.',
        'offers': {
          '@type': 'Offer',
          'price': '0',
          'priceCurrency': 'INR',
        },
      },
      {
        '@type': 'FAQPage',
        '@id': 'https://fundersai.com/#faq',
        'mainEntity': [
          {
            '@type': 'Question',
            'name': 'How do I compare Indian mutual funds side-by-side?',
            'acceptedAnswer': {
              '@type': 'Answer',
              'text': 'FundersAI provides a side-by-side research canvas where you can pick funds like Parag Parikh Flexi Cap and ICICI Prudential Multi Asset, overlay their NAV performance, and compare Sharpe ratios, expense ratios, alpha, and beta values.',
            },
          },
          {
            '@type': 'Question',
            'name': 'Does FundersAI provide investment advisory or recommendations?',
            'acceptedAnswer': {
              '@type': 'Answer',
              'text': 'No. FundersAI is designed as an objective, institutional-grade research platform. We operate under strict research-only guardrails and do not provide buy, sell, or hold recommendations.',
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
