/**
 * Static slug registry for P6 indexable fund pages.
 * Maps URL slugs to AMFI scheme codes and vice-versa.
 * Covers a curated shortlist of widely-searched funds across the major AMCs.
 *
 * Every schemeCode below is verified against AMFI's authoritative scheme master
 * (https://portal.amfiindia.com/spages/NAVAll.txt). tests/amfiSchemeIdentity.test.mjs
 * and tests/fixtures/amfi-scheme-identity.json pin each code to the scheme name,
 * plan and option AMFI publishes for it, so a wrong code fails CI.
 * schemeName carries the CURRENT SEBI-mandated name; formerName carries the
 * pre-rename name where a scheme was renamed. fundSlug is frozen for URL stability
 * and may therefore still read as the old name.
 * To add more funds, append an entry to FUND_REGISTRY and a matching fixture row.
 * Never hand-write a scheme code that is not in the fixture.
 */

export interface FundEntry {
  schemeCode: number;
  /** Current SEBI-mandated scheme name. */
  schemeName: string;
  /** Previous name, when the scheme was renamed under SEBI re-categorisation. */
  formerName?: string;
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
    slug: 'quant',
    name: 'Quant Mutual Fund',
    shortName: 'Quant',
    description:
      'Known for its quantitative VLRT dynamic investment framework and high momentum alpha strategies.',
  },
  {
    slug: 'bandhan',
    name: 'Bandhan Mutual Fund',
    shortName: 'Bandhan',
    description:
      'Formerly IDFC Mutual Fund. Managed with strong research frameworks across small-cap and debt funds.',
  },
  {
    slug: 'motilal-oswal',
    name: 'Motilal Oswal Mutual Fund',
    shortName: 'Motilal Oswal',
    description:
      'Known for focused, buy-right-sit-tight equity strategy and growing index fund business.',
  },
  {
    slug: 'tata',
    name: 'Tata Mutual Fund',
    shortName: 'Tata',
    description:
      'Part of the storied Tata Group. Known for disciplined thematic, sectoral, and diversified equity funds.',
  },
];

// ─── Fund registry ──────────────────────────────────────────────────────────
// Every entry is the Direct Plan / Growth Option scheme code.

export const FUND_REGISTRY: FundEntry[] = [
  // HDFC
  {
    schemeCode: 118955,
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
    schemeCode: 118989,
    schemeName: 'HDFC Mid Cap Fund',
    formerName: 'HDFC Mid-Cap Opportunities Fund',
    amcSlug: 'hdfc',
    amcName: 'HDFC Mutual Fund',
    fundSlug: 'hdfc-mid-cap-opportunities-fund',
    category: 'Mid Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Midcap 150 TRI',
  },
  {
    schemeCode: 130503,
    schemeName: 'HDFC Small Cap Fund',
    amcSlug: 'hdfc',
    amcName: 'HDFC Mutual Fund',
    fundSlug: 'hdfc-small-cap-fund',
    category: 'Small Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Smallcap 250 TRI',
  },
  {
    schemeCode: 119018,
    schemeName: 'HDFC Large Cap Fund',
    formerName: 'HDFC Top 100 Fund',
    amcSlug: 'hdfc',
    amcName: 'HDFC Mutual Fund',
    fundSlug: 'hdfc-top-100-fund',
    category: 'Large Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 100 TRI',
  },
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
    schemeCode: 147481,
    schemeName: 'Parag Parikh ELSS Tax Saver Fund',
    amcSlug: 'ppfas',
    amcName: 'PPFAS Mutual Fund',
    fundSlug: 'parag-parikh-elss-tax-saver-fund',
    category: 'ELSS',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 500 TRI',
  },
  {
    schemeCode: 118834,
    schemeName: 'Mirae Asset Large & Midcap Fund',
    formerName: 'Mirae Asset Emerging Bluechip Fund',
    amcSlug: 'mirae-asset',
    amcName: 'Mirae Asset Mutual Fund',
    fundSlug: 'mirae-asset-emerging-bluechip-fund',
    category: 'Large & Mid Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Large Midcap 250 TRI',
  },
  {
    schemeCode: 118825,
    schemeName: 'Mirae Asset Large Cap Fund',
    amcSlug: 'mirae-asset',
    amcName: 'Mirae Asset Mutual Fund',
    fundSlug: 'mirae-asset-large-cap-fund',
    category: 'Large Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 100 TRI',
  },
  {
    schemeCode: 147445,
    schemeName: 'Mirae Asset Midcap Fund',
    amcSlug: 'mirae-asset',
    amcName: 'Mirae Asset Mutual Fund',
    fundSlug: 'mirae-asset-midcap-fund',
    category: 'Mid Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Midcap 150 TRI',
  },
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
    schemeCode: 119598,
    schemeName: 'SBI Large Cap Fund',
    formerName: 'SBI Bluechip Fund',
    amcSlug: 'sbi',
    amcName: 'SBI Mutual Fund',
    fundSlug: 'sbi-bluechip-fund',
    category: 'Large Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 100 TRI',
  },
  {
    schemeCode: 119835,
    schemeName: 'SBI Contra Fund',
    amcSlug: 'sbi',
    amcName: 'SBI Mutual Fund',
    fundSlug: 'sbi-contra-fund',
    category: 'Flexi Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'BSE 500 TRI',
  },
  {
    schemeCode: 120586,
    schemeName: 'ICICI Prudential Large Cap Fund',
    formerName: 'ICICI Prudential Bluechip Fund',
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
  {
    schemeCode: 120323,
    schemeName: 'ICICI Prudential Value Fund',
    formerName: 'ICICI Prudential Value Discovery Fund',
    amcSlug: 'icici-prudential',
    amcName: 'ICICI Prudential Mutual Fund',
    fundSlug: 'icici-prudential-value-discovery-fund',
    category: 'Flexi Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 500 TRI',
  },
  {
    schemeCode: 118778,
    schemeName: 'Nippon India Small Cap Fund',
    amcSlug: 'nippon',
    amcName: 'Nippon India Mutual Fund',
    fundSlug: 'nippon-india-small-cap-fund',
    category: 'Small Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Smallcap 250 TRI',
  },
  {
    schemeCode: 118668,
    schemeName: 'Nippon India Growth Mid Cap Fund',
    formerName: 'Nippon India Growth Fund',
    amcSlug: 'nippon',
    amcName: 'Nippon India Mutual Fund',
    fundSlug: 'nippon-india-growth-fund',
    category: 'Mid Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Midcap 150 TRI',
  },
  {
    schemeCode: 120828,
    schemeName: 'Quant Small Cap Fund',
    amcSlug: 'quant',
    amcName: 'Quant Mutual Fund',
    fundSlug: 'quant-small-cap-fund',
    category: 'Small Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Smallcap 250 TRI',
  },
  {
    schemeCode: 120823,
    schemeName: 'Quant Multi Cap Fund',
    formerName: 'Quant Active Fund',
    amcSlug: 'quant',
    amcName: 'Quant Mutual Fund',
    fundSlug: 'quant-active-fund',
    category: 'Flexi Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 500 TRI',
  },
  {
    schemeCode: 120166,
    schemeName: 'Kotak Flexicap Fund',
    amcSlug: 'kotak',
    amcName: 'Kotak Mahindra Mutual Fund',
    fundSlug: 'kotak-flexi-cap-fund',
    category: 'Flexi Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'BSE 500 TRI',
  },
  {
    schemeCode: 119775,
    schemeName: 'Kotak Midcap Fund',
    formerName: 'Kotak Emerging Equity Fund',
    amcSlug: 'kotak',
    amcName: 'Kotak Mahindra Mutual Fund',
    fundSlug: 'kotak-emerging-equity-fund',
    category: 'Mid Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Midcap 150 TRI',
  },
  {
    schemeCode: 141925,
    schemeName: 'Axis Flexi Cap Fund',
    amcSlug: 'axis',
    amcName: 'Axis Mutual Fund',
    fundSlug: 'axis-flexi-cap-fund',
    category: 'Flexi Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'BSE 500 TRI',
  },
  {
    schemeCode: 125354,
    schemeName: 'Axis Small Cap Fund',
    amcSlug: 'axis',
    amcName: 'Axis Mutual Fund',
    fundSlug: 'axis-small-cap-fund',
    category: 'Small Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Smallcap 250 TRI',
  },
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
  {
    schemeCode: 127042,
    schemeName: 'Motilal Oswal Midcap Fund',
    amcSlug: 'motilal-oswal',
    amcName: 'Motilal Oswal Mutual Fund',
    fundSlug: 'motilal-oswal-midcap-fund',
    category: 'Mid Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Midcap 150 TRI',
  },
  {
    schemeCode: 147946,
    schemeName: 'Bandhan Small Cap Fund',
    amcSlug: 'bandhan',
    amcName: 'Bandhan Mutual Fund',
    fundSlug: 'bandhan-small-cap-fund',
    category: 'Small Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty Smallcap 250 TRI',
  },
  {
    schemeCode: 135800,
    schemeName: 'Tata Digital India Fund',
    amcSlug: 'tata',
    amcName: 'Tata Mutual Fund',
    fundSlug: 'tata-digital-india-fund',
    category: 'Sectoral/Thematic',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty IT TRI',
  },
  {
    schemeCode: 119528,
    schemeName: 'Aditya Birla Sun Life Large Cap Fund',
    formerName: 'Aditya Birla Sun Life Frontline Equity Fund',
    amcSlug: 'aditya-birla-sun-life',
    amcName: 'Aditya Birla Sun Life Mutual Fund',
    fundSlug: 'aditya-birla-sun-life-frontline-equity-fund',
    category: 'Large Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'Nifty 100 TRI',
  },
  {
    schemeCode: 119071,
    schemeName: 'DSP Midcap Fund',
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

export function getFundByFundSlug(fundSlug: string): FundEntry | undefined {
  return FUND_REGISTRY.find((f) => f.fundSlug === fundSlug);
}

/**
 * Registry entries grouped by AMC, largest family first.
 * Identity only (code / current name / former name / category) — the registry
 * deliberately carries no NAV, returns or expense-ratio figures, because those
 * are point-in-time values that must come from a live source, never from a
 * hardcoded literal.
 */
export function getFundsGroupedByAmc(): Array<{ amcName: string; funds: FundEntry[] }> {
  const groups = new Map<string, FundEntry[]>();
  for (const fund of FUND_REGISTRY) {
    const bucket = groups.get(fund.amcName);
    if (bucket) bucket.push(fund);
    else groups.set(fund.amcName, [fund]);
  }
  return [...groups.entries()]
    .map(([amcName, funds]) => ({ amcName, funds }))
    .sort((a, b) => b.funds.length - a.funds.length || a.amcName.localeCompare(b.amcName));
}

/**
 * Shortlist shown in fund pickers when no live scheme list is available.
 * Stored as slugs so the scheme codes and names always resolve through
 * FUND_REGISTRY and stay covered by the AMFI identity test.
 */
export const POPULAR_FUND_SLUGS: readonly string[] = [
  'parag-parikh-flexi-cap-fund',
  'hdfc-flexi-cap-fund',
  'hdfc-top-100-fund',
  'quant-small-cap-fund',
  'quant-active-fund',
  'nippon-india-small-cap-fund',
  'sbi-small-cap-fund',
  'sbi-contra-fund',
  'icici-prudential-bluechip-fund',
  'axis-small-cap-fund',
  'mirae-asset-large-cap-fund',
  'uti-nifty-50-index-fund',
];

export function getPopularFunds(): FundEntry[] {
  return POPULAR_FUND_SLUGS.map(getFundByFundSlug).filter(
    (f): f is FundEntry => f !== undefined,
  );
}

/**
 * Registry peers for a given scheme, same category first. Used to offer
 * comparison targets; never claims to be a ranked or personalised suggestion.
 */
export function getPeerFunds(schemeCode: number, limit = 3): FundEntry[] {
  const self = getFundBySchemeCode(schemeCode);
  const others = FUND_REGISTRY.filter((f) => f.schemeCode !== schemeCode);
  if (!self) return others.slice(0, limit);
  const sameCategory = others.filter((f) => f.category === self.category);
  const rest = others.filter((f) => f.category !== self.category);
  return [...sameCategory, ...rest].slice(0, limit);
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

export function categorySlug(category: string): string {
  return category
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/\//g, '-')
    .replace(/\s+/g, '-');
}

export function getCategoryBySlug(slug: string): (typeof CATEGORY_LIST)[number] | undefined {
  return CATEGORY_LIST.find((cat) => categorySlug(cat) === slug);
}

export interface ComparePair {
  pair: string;
  fundSlugA: string;
  amcSlugA: string;
  fundSlugB: string;
  amcSlugB: string;
}

export const COMPARE_PAIRS: ComparePair[] = [
  {
    pair: 'hdfc-flexi-cap-fund-vs-parag-parikh-flexi-cap-fund',
    amcSlugA: 'hdfc',
    fundSlugA: 'hdfc-flexi-cap-fund',
    amcSlugB: 'ppfas',
    fundSlugB: 'parag-parikh-flexi-cap-fund',
  },
  {
    pair: 'nippon-india-small-cap-fund-vs-sbi-small-cap-fund',
    amcSlugA: 'nippon',
    fundSlugA: 'nippon-india-small-cap-fund',
    amcSlugB: 'sbi',
    fundSlugB: 'sbi-small-cap-fund',
  },
  {
    pair: 'mirae-asset-emerging-bluechip-fund-vs-hdfc-mid-cap-opportunities-fund',
    amcSlugA: 'mirae-asset',
    fundSlugA: 'mirae-asset-emerging-bluechip-fund',
    amcSlugB: 'hdfc',
    fundSlugB: 'hdfc-mid-cap-opportunities-fund',
  },
  {
    pair: 'icici-prudential-bluechip-fund-vs-sbi-bluechip-fund',
    amcSlugA: 'icici-prudential',
    fundSlugA: 'icici-prudential-bluechip-fund',
    amcSlugB: 'sbi',
    fundSlugB: 'sbi-bluechip-fund',
  },
];
