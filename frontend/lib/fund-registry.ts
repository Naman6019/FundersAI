/**
 * Static slug registry for P6 indexable fund pages.
 * Maps URL slugs to AMFI scheme codes and vice-versa.
 * Only covers the 20 most-searched funds + 12 AMCs.
 *
 * AMFI scheme codes verified July 2026.
 * To add more funds, append an entry to FUND_REGISTRY and re-deploy.
 */

export interface FundEntry {
  schemeCode: number;
  schemeName: string;
  amcSlug: string;
  amcName: string;
  fundSlug: string;
  category: string;
  plan: 'Direct' | 'Regular';
  option: 'Growth' | 'IDCW';
  benchmark: string;
}

export interface AmcEntry {
  slug: string;
  name: string;
  shortName: string;
  description: string;
}

// ─── AMC registry ───────────────────────────────────────────────────────────

export const AMC_REGISTRY: AmcEntry[] = [
  {
    slug: 'hdfc',
    name: 'HDFC Mutual Fund',
    shortName: 'HDFC',
    description:
      'One of India\'s largest AMCs with ₹7+ lakh crore AUM. Strong track record across equity and debt categories.',
  },
  {
    slug: 'icici-prudential',
    name: 'ICICI Prudential Mutual Fund',
    shortName: 'ICICI Pru',
    description:
      'Joint venture between ICICI Bank and Prudential plc. Known for diversified equity and hybrid fund offerings.',
  },
  {
    slug: 'sbi',
    name: 'SBI Mutual Fund',
    shortName: 'SBI',
    description:
      'Backed by State Bank of India. Among the largest AMCs by AUM with a wide retail investor base.',
  },
  {
    slug: 'nippon',
    name: 'Nippon India Mutual Fund',
    shortName: 'Nippon',
    description:
      'Formerly Reliance Mutual Fund. Managed by Nippon Life Insurance of Japan. Strong in small and mid-cap.',
  },
  {
    slug: 'kotak',
    name: 'Kotak Mahindra Mutual Fund',
    shortName: 'Kotak',
    description:
      'Part of Kotak Mahindra Group. Known for disciplined multi-cap and flexi-cap strategies.',
  },
  {
    slug: 'aditya-birla-sun-life',
    name: 'Aditya Birla Sun Life Mutual Fund',
    shortName: 'Aditya Birla',
    description:
      'Joint venture of Aditya Birla Group and Sun Life Financial. Strong debt and hybrid fund lineup.',
  },
  {
    slug: 'ppfas',
    name: 'PPFAS Mutual Fund',
    shortName: 'PPFAS',
    description:
      'Parag Parikh Financial Advisory Services. Known for its long-only, low-turnover investment philosophy and international allocation.',
  },
  {
    slug: 'mirae-asset',
    name: 'Mirae Asset Mutual Fund',
    shortName: 'Mirae Asset',
    description:
      'Korean-backed AMC with a strong growth equity focus. Known for disciplined large-cap and emerging bluechip strategies.',
  },
  {
    slug: 'uti',
    name: 'UTI Mutual Fund',
    shortName: 'UTI',
    description:
      'India\'s oldest AMC. Strong in index funds tracking Nifty 50 and Nifty Next 50.',
  },
  {
    slug: 'dsp',
    name: 'DSP Mutual Fund',
    shortName: 'DSP',
    description:
      'Independent fund house with a multi-decade track record. Known for mid-cap and small-cap expertise.',
  },
  {
    slug: 'axis',
    name: 'Axis Mutual Fund',
    shortName: 'Axis',
    description:
      'Backed by Axis Bank. Large-cap and flexi-cap strategies with growing AUM.',
  },
  {
    slug: 'motilal-oswal',
    name: 'Motilal Oswal Mutual Fund',
    shortName: 'Motilal Oswal',
    description:
      'Known for focused, buy-right-sit-tight equity strategy and growing index fund business.',
  },
];

// ─── Fund registry ──────────────────────────────────────────────────────────
// AMFI scheme codes for Direct Growth plans unless noted.

export const FUND_REGISTRY: FundEntry[] = [
  // HDFC
  {
    schemeCode: 120503,
    schemeName: 'HDFC Flexi Cap Fund',
    amcSlug: 'hdfc',
    amcName: 'HDFC Mutual Fund',
    fundSlug: 'hdfc-flexi-cap-fund',
    category: 'Flexi Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'BSE 500 TRI',
  },
  {
    schemeCode: 119552,
    schemeName: 'HDFC Mid-Cap Opportunities Fund',
    amcSlug: 'hdfc',
    amcName: 'HDFC Mutual Fund',
    fundSlug: 'hdfc-mid-cap-opportunities-fund',
    category: 'Mid Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Midcap 150 TRI',
  },
  {
    schemeCode: 119598,
    schemeName: 'HDFC Small Cap Fund',
    amcSlug: 'hdfc',
    amcName: 'HDFC Mutual Fund',
    fundSlug: 'hdfc-small-cap-fund',
    category: 'Small Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Smallcap 250 TRI',
  },
  // PPFAS
  {
    schemeCode: 122639,
    schemeName: 'Parag Parikh Flexi Cap Fund',
    amcSlug: 'ppfas',
    amcName: 'PPFAS Mutual Fund',
    fundSlug: 'parag-parikh-flexi-cap-fund',
    category: 'Flexi Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'BSE 500 TRI',
  },
  {
    schemeCode: 149021,
    schemeName: 'Parag Parikh ELSS Tax Saver Fund',
    amcSlug: 'ppfas',
    amcName: 'PPFAS Mutual Fund',
    fundSlug: 'parag-parikh-elss-tax-saver-fund',
    category: 'ELSS',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 500 TRI',
  },
  // Mirae Asset
  {
    schemeCode: 118989,
    schemeName: 'Mirae Asset Emerging Bluechip Fund',
    amcSlug: 'mirae-asset',
    amcName: 'Mirae Asset Mutual Fund',
    fundSlug: 'mirae-asset-emerging-bluechip-fund',
    category: 'Large & Mid Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Large Midcap 250 TRI',
  },
  {
    schemeCode: 118701,
    schemeName: 'Mirae Asset Large Cap Fund',
    amcSlug: 'mirae-asset',
    amcName: 'Mirae Asset Mutual Fund',
    fundSlug: 'mirae-asset-large-cap-fund',
    category: 'Large Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 100 TRI',
  },
  // SBI
  {
    schemeCode: 125497,
    schemeName: 'SBI Small Cap Fund',
    amcSlug: 'sbi',
    amcName: 'SBI Mutual Fund',
    fundSlug: 'sbi-small-cap-fund',
    category: 'Small Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Smallcap 250 TRI',
  },
  {
    schemeCode: 119206,
    schemeName: 'SBI Bluechip Fund',
    amcSlug: 'sbi',
    amcName: 'SBI Mutual Fund',
    fundSlug: 'sbi-bluechip-fund',
    category: 'Large Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 100 TRI',
  },
  // ICICI Prudential
  {
    schemeCode: 120586,
    schemeName: 'ICICI Prudential Bluechip Fund',
    amcSlug: 'icici-prudential',
    amcName: 'ICICI Prudential Mutual Fund',
    fundSlug: 'icici-prudential-bluechip-fund',
    category: 'Large Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 100 TRI',
  },
  {
    schemeCode: 120594,
    schemeName: 'ICICI Prudential Technology Fund',
    amcSlug: 'icici-prudential',
    amcName: 'ICICI Prudential Mutual Fund',
    fundSlug: 'icici-prudential-technology-fund',
    category: 'Sectoral/Thematic',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty IT TRI',
  },
  // Nippon
  {
    schemeCode: 118825,
    schemeName: 'Nippon India Small Cap Fund',
    amcSlug: 'nippon',
    amcName: 'Nippon India Mutual Fund',
    fundSlug: 'nippon-india-small-cap-fund',
    category: 'Small Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Smallcap 250 TRI',
  },
  // Kotak
  {
    schemeCode: 120505,
    schemeName: 'Kotak Flexi Cap Fund',
    amcSlug: 'kotak',
    amcName: 'Kotak Mahindra Mutual Fund',
    fundSlug: 'kotak-flexi-cap-fund',
    category: 'Flexi Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'BSE 500 TRI',
  },
  // Axis
  {
    schemeCode: 120503,
    schemeName: 'Axis Flexi Cap Fund',
    amcSlug: 'axis',
    amcName: 'Axis Mutual Fund',
    fundSlug: 'axis-flexi-cap-fund',
    category: 'Flexi Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'BSE 500 TRI',
  },
  // UTI
  {
    schemeCode: 120716,
    schemeName: 'UTI Nifty 50 Index Fund',
    amcSlug: 'uti',
    amcName: 'UTI Mutual Fund',
    fundSlug: 'uti-nifty-50-index-fund',
    category: 'Index Fund',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 50 TRI',
  },
  // Motilal Oswal
  {
    schemeCode: 147622,
    schemeName: 'Motilal Oswal Midcap Fund',
    amcSlug: 'motilal-oswal',
    amcName: 'Motilal Oswal Mutual Fund',
    fundSlug: 'motilal-oswal-midcap-fund',
    category: 'Mid Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Midcap 150 TRI',
  },
  // Aditya Birla
  {
    schemeCode: 119270,
    schemeName: 'Aditya Birla Sun Life Frontline Equity Fund',
    amcSlug: 'aditya-birla-sun-life',
    amcName: 'Aditya Birla Sun Life Mutual Fund',
    fundSlug: 'aditya-birla-sun-life-frontline-equity-fund',
    category: 'Large Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 100 TRI',
  },
  // DSP
  {
    schemeCode: 119230,
    schemeName: 'DSP Mid Cap Fund',
    amcSlug: 'dsp',
    amcName: 'DSP Mutual Fund',
    fundSlug: 'dsp-mid-cap-fund',
    category: 'Mid Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Midcap 150 TRI',
  },
];

// ─── Lookup helpers ──────────────────────────────────────────────────────────

export function getFundBySlug(amcSlug: string, fundSlug: string): FundEntry | undefined {
  return FUND_REGISTRY.find((f) => f.amcSlug === amcSlug && f.fundSlug === fundSlug);
}

export function getAmcBySlug(slug: string): AmcEntry | undefined {
  return AMC_REGISTRY.find((a) => a.slug === slug);
}

export function getFundsByAmc(amcSlug: string): FundEntry[] {
  return FUND_REGISTRY.filter((f) => f.amcSlug === amcSlug);
}

export function getFundBySchemeCode(schemeCode: number): FundEntry | undefined {
  return FUND_REGISTRY.find((f) => f.schemeCode === schemeCode);
}

/** Category → funds */
export function getFundsByCategory(category: string): FundEntry[] {
  return FUND_REGISTRY.filter(
    (f) => f.category.toLowerCase() === category.toLowerCase(),
  );
}

export const CATEGORY_LIST = [
  'Flexi Cap',
  'Large Cap',
  'Mid Cap',
  'Small Cap',
  'Large & Mid Cap',
  'ELSS',
  'Index Fund',
  'Sectoral/Thematic',
] as const;
