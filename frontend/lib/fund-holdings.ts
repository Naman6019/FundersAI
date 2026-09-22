/**
 * Curated reference portfolio holdings for a small, named set of top Indian mutual funds.
 *
 * PROVENANCE AND LIMITS — read before using:
 * - These are a hand-curated reference snapshot, NOT a live read of the official AMC
 *   statutory disclosure. They exist so the overlap tool has something to demonstrate.
 * - Each entry carries the `asOf` month it describes. A figure here is a point-in-time
 *   illustration and may be superseded by the AMC's current monthly portfolio.
 * - Only funds with an entry below have a usable holdings set. For every other scheme the
 *   caller MUST abstain (`getHoldingsForScheme` returns null) rather than substitute a
 *   proxy. An earlier version generated category-level "representative" holdings for any
 *   unknown scheme, which silently attributed one fund's stocks to a different fund.
 * - No aggregate performance claim is derived from this file. It feeds the overlap view only.
 */

export interface StockHolding {
  isin: string;
  name: string;
  ticker?: string;
  weight: number; // Percentage of the scheme's portfolio, e.g. 8.4
  sector: string;
}

export interface DetailedOverlapResult {
  percentage: number;
  overlappingCount: number;
  totalUniqueCount: number;
  overlapping: {
    isin: string;
    name: string;
    weightA: number;
    weightB: number;
    overlap: number;
    sector: string;
  }[];
  uniqueA: StockHolding[];
  uniqueB: StockHolding[];
  sectorBreakdown: {
    sector: string;
    weightA: number;
    weightB: number;
    overlap: number;
  }[];
  verdict: {
    level: 'Low' | 'Moderate' | 'High';
    color: string;
    title: string;
    description: string;
  };
}

export interface CuratedHoldings {
  /** Month the snapshot describes, `YYYY-MM`. */
  asOf: string;
  /** Where the underlying figures came from. */
  source: string;
  holdings: StockHolding[];
}

// ─── Reference Portfolio Holdings by Scheme Code ────────────────────────────
//
// Keys are AMFI scheme codes and must resolve to the fund the `source` names. They are
// cross-checked against FUND_REGISTRY by tests/fundHoldingsIdentity.test.mjs.

export const FUND_HOLDINGS_DB: Record<number, CuratedHoldings> = {
  // Parag Parikh Flexi Cap Fund
  122639: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 8.12, sector: 'Financial Services' },
      { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 6.84, sector: 'Financial Services' },
      { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 6.25, sector: 'Consumer Goods' },
      { isin: 'INE238A01034', name: 'Axis Bank Ltd', ticker: 'AXISBANK', weight: 5.41, sector: 'Financial Services' },
      { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 4.95, sector: 'Energy & Utilities' },
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 3.92, sector: 'Technology' },
      { isin: 'INE059A01026', name: 'Cipla Ltd', ticker: 'CIPLA', weight: 3.45, sector: 'Healthcare' },
      { isin: 'INE062A01020', name: 'State Bank of India', ticker: 'SBIN', weight: 3.10, sector: 'Financial Services' },
      { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 2.95, sector: 'Technology' },
    ],
  },

  // HDFC Flexi Cap Fund
  118955: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 9.45, sector: 'Financial Services' },
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 8.92, sector: 'Financial Services' },
      { isin: 'INE062A01020', name: 'State Bank of India', ticker: 'SBIN', weight: 6.75, sector: 'Financial Services' },
      { isin: 'INE238A01034', name: 'Axis Bank Ltd', ticker: 'AXISBANK', weight: 5.82, sector: 'Financial Services' },
      { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 5.40, sector: 'Energy & Utilities' },
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 4.88, sector: 'Technology' },
      { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 4.35, sector: 'Industrials' },
      { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 3.95, sector: 'Consumer Goods' },
      { isin: 'INE397D01024', name: 'Bharti Airtel Ltd', ticker: 'BHARTIARTL', weight: 3.65, sector: 'Telecommunication' },
      { isin: 'INE044A01036', name: 'Sun Pharmaceutical Industries Ltd', ticker: 'SUNPHARMA', weight: 3.20, sector: 'Healthcare' },
      { isin: 'INE155A01022', name: 'Tata Motors Ltd', ticker: 'TATAMOTORS', weight: 2.85, sector: 'Automobile' },
    ],
  },

  // Quant Small Cap Fund
  120828: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 8.85, sector: 'Energy & Utilities' },
      { isin: 'INE114A01011', name: 'Steel Authority of India Ltd', ticker: 'SAIL', weight: 5.45, sector: 'Metals & Mining' },
      { isin: 'INE117A01022', name: 'ABB India Ltd', ticker: 'ABB', weight: 4.90, sector: 'Industrials' },
      { isin: 'INE522D01027', name: 'Manappuram Finance Ltd', ticker: 'MANAPPURAM', weight: 4.35, sector: 'Financial Services' },
      { isin: 'INE216A01030', name: 'Biocon Ltd', ticker: 'BIOCON', weight: 3.92, sector: 'Healthcare' },
      { isin: 'INE152A01029', name: 'Aditya Birla Fashion & Retail Ltd', ticker: 'ABFRL', weight: 3.80, sector: 'Consumer Goods' },
      { isin: 'INE245A01021', name: 'The Tata Power Co Ltd', ticker: 'TATAPOWER', weight: 3.65, sector: 'Energy & Utilities' },
    ],
  },

  // Nippon India Small Cap Fund
  118778: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 4.10, sector: 'Energy & Utilities' },
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 3.85, sector: 'Financial Services' },
      { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 3.40, sector: 'Financial Services' },
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 3.05, sector: 'Technology' },
      { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 2.70, sector: 'Technology' },
      { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 2.45, sector: 'Consumer Goods' },
      { isin: 'INE062A01020', name: 'State Bank of India', ticker: 'SBIN', weight: 2.20, sector: 'Financial Services' },
    ],
  },

  // SBI Large Cap Fund (erstwhile SBI Bluechip Fund)
  119598: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 9.10, sector: 'Financial Services' },
      { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 8.35, sector: 'Financial Services' },
      { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 7.20, sector: 'Energy & Utilities' },
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 6.15, sector: 'Technology' },
      { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 5.40, sector: 'Technology' },
      { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 4.85, sector: 'Consumer Goods' },
      { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 4.30, sector: 'Industrials' },
      { isin: 'INE397D01024', name: 'Bharti Airtel Ltd', ticker: 'BHARTIARTL', weight: 4.60, sector: 'Telecommunication' },
      { isin: 'INE238A01034', name: 'Axis Bank Ltd', ticker: 'AXISBANK', weight: 3.75, sector: 'Financial Services' },
      { isin: 'INE044A01036', name: 'Sun Pharmaceutical Industries Ltd', ticker: 'SUNPHARMA', weight: 3.10, sector: 'Healthcare' },
    ],
  },

  // ICICI Prudential Large Cap Fund (erstwhile ICICI Prudential Bluechip Fund)
  120586: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 8.75, sector: 'Financial Services' },
      { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 8.05, sector: 'Financial Services' },
      { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 6.60, sector: 'Energy & Utilities' },
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 5.55, sector: 'Technology' },
      { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 4.90, sector: 'Technology' },
      { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 4.35, sector: 'Consumer Goods' },
      { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 3.95, sector: 'Industrials' },
      { isin: 'INE397D01024', name: 'Bharti Airtel Ltd', ticker: 'BHARTIARTL', weight: 3.60, sector: 'Telecommunication' },
    ],
  },

  // Mirae Asset Large & Midcap Fund
  118834: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 6.85, sector: 'Financial Services' },
      { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 6.20, sector: 'Financial Services' },
      { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 5.10, sector: 'Energy & Utilities' },
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 4.45, sector: 'Technology' },
      { isin: 'INE062A01020', name: 'State Bank of India', ticker: 'SBIN', weight: 3.80, sector: 'Financial Services' },
      { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 3.50, sector: 'Industrials' },
      { isin: 'INE280A01028', name: 'Titan Company Ltd', ticker: 'TITAN', weight: 3.15, sector: 'Consumer Goods' },
      { isin: 'INE397D01024', name: 'Bharti Airtel Ltd', ticker: 'BHARTIARTL', weight: 2.90, sector: 'Telecommunication' },
      { isin: 'INE101A01026', name: 'Mahindra & Mahindra Ltd', ticker: 'M&M', weight: 2.75, sector: 'Automobile' },
      { isin: 'INE752E01010', name: 'Power Grid Corp of India Ltd', ticker: 'POWERGRID', weight: 2.40, sector: 'Energy & Utilities' },
    ],
  },

  // Kotak Flexi Cap Fund
  120166: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 8.50, sector: 'Financial Services' },
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 7.95, sector: 'Financial Services' },
      { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 5.80, sector: 'Energy & Utilities' },
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 5.10, sector: 'Technology' },
      { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 4.60, sector: 'Industrials' },
      { isin: 'INE238A01034', name: 'Axis Bank Ltd', ticker: 'AXISBANK', weight: 3.90, sector: 'Financial Services' },
      { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 3.65, sector: 'Technology' },
    ],
  },

  // UTI Nifty 50 Index Fund
  120716: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 11.80, sector: 'Financial Services' },
      { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 8.20, sector: 'Financial Services' },
      { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 8.05, sector: 'Energy & Utilities' },
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 5.95, sector: 'Technology' },
      { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 4.10, sector: 'Technology' },
      { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 4.35, sector: 'Consumer Goods' },
      { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 3.85, sector: 'Industrials' },
      { isin: 'INE397D01024', name: 'Bharti Airtel Ltd', ticker: 'BHARTIARTL', weight: 3.60, sector: 'Telecommunication' },
    ],
  },

  // Motilal Oswal Midcap Fund
  127042: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 5.60, sector: 'Financial Services' },
      { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 5.15, sector: 'Financial Services' },
      { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 4.70, sector: 'Energy & Utilities' },
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 4.20, sector: 'Technology' },
      { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 3.80, sector: 'Industrials' },
      { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 3.45, sector: 'Consumer Goods' },
    ],
  },

  // Tata Digital India Fund
  135800: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 16.50, sector: 'Technology' },
      { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 14.20, sector: 'Technology' },
      { isin: 'INE669C01036', name: 'Tech Mahindra Ltd', ticker: 'TECHM', weight: 8.40, sector: 'Technology' },
      { isin: 'INE075A01022', name: 'Wipro Ltd', ticker: 'WIPRO', weight: 7.60, sector: 'Technology' },
      { isin: 'INE214T01019', name: 'LTIMindtree Ltd', ticker: 'LTIM', weight: 5.90, sector: 'Technology' },
      { isin: 'US02079K3059', name: 'Alphabet Inc Class A (Google)', ticker: 'GOOGL', weight: 5.20, sector: 'Technology' },
      { isin: 'US5949181045', name: 'Microsoft Corporation', ticker: 'MSFT', weight: 4.60, sector: 'Technology' },
    ],
  },

  // ICICI Prudential Technology Fund
  120594: {
    asOf: '2026-07',
    source: 'Curated reference snapshot (illustrative)',
    holdings: [
      { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 15.80, sector: 'Technology' },
      { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 13.40, sector: 'Technology' },
      { isin: 'INE669C01036', name: 'Tech Mahindra Ltd', ticker: 'TECHM', weight: 7.90, sector: 'Technology' },
      { isin: 'INE075A01022', name: 'Wipro Ltd', ticker: 'WIPRO', weight: 7.20, sector: 'Technology' },
      { isin: 'INE214T01019', name: 'LTIMindtree Ltd', ticker: 'LTIM', weight: 5.60, sector: 'Technology' },
      { isin: 'INE018I01017', name: 'Coforge Ltd', ticker: 'COFORGE', weight: 4.80, sector: 'Technology' },
    ],
  },
};

/**
 * Returns the curated holdings for a scheme, or `null` when we have none.
 *
 * `null` is the whole point: the caller must show an explicit "no holdings published for
 * this scheme" state. Returning a category-level proxy instead would present invented
 * stocks as if they were the fund's actual portfolio.
 */
export function getHoldingsForScheme(schemeCode: number): CuratedHoldings | null {
  return FUND_HOLDINGS_DB[schemeCode] ?? null;
}

export function hasCuratedHoldings(schemeCode: number): boolean {
  return FUND_HOLDINGS_DB[schemeCode] !== undefined;
}

// ─── Detailed Overlap Computation Engine ────────────────────────────────────

export function calculateDetailedOverlap(
  holdingsA: StockHolding[],
  holdingsB: StockHolding[]
): DetailedOverlapResult {
  if (!holdingsA?.length || !holdingsB?.length) {
    return {
      percentage: 0,
      overlappingCount: 0,
      totalUniqueCount: 0,
      overlapping: [],
      uniqueA: holdingsA || [],
      uniqueB: holdingsB || [],
      sectorBreakdown: [],
      verdict: {
        level: 'Low',
        color: 'text-slate-400',
        title: 'No overlap computed',
        description: 'Holdings data is unavailable for one or both schemes.',
      },
    };
  }

  const mapA = new Map(holdingsA.map((h) => [h.isin, h]));
  const mapB = new Map(holdingsB.map((h) => [h.isin, h]));

  const overlapping: DetailedOverlapResult['overlapping'] = [];
  const uniqueA: StockHolding[] = [];
  const uniqueB: StockHolding[] = [];
  const sectorTotals = new Map<string, { weightA: number; weightB: number; overlap: number }>();

  for (const holding of holdingsA) {
    const match = mapB.get(holding.isin);
    const sector = sectorTotals.get(holding.sector) ?? { weightA: 0, weightB: 0, overlap: 0 };
    sector.weightA += holding.weight;
    if (match) {
      // SEBI-style overlap contribution is the smaller of the two weights.
      const overlap = Math.min(holding.weight, match.weight);
      overlapping.push({
        isin: holding.isin,
        name: holding.name,
        weightA: holding.weight,
        weightB: match.weight,
        overlap,
        sector: holding.sector,
      });
      sector.overlap += overlap;
    } else {
      uniqueA.push(holding);
    }
    sectorTotals.set(holding.sector, sector);
  }

  for (const holding of holdingsB) {
    const sector = sectorTotals.get(holding.sector) ?? { weightA: 0, weightB: 0, overlap: 0 };
    sector.weightB += holding.weight;
    if (!mapA.has(holding.isin)) uniqueB.push(holding);
    sectorTotals.set(holding.sector, sector);
  }

  const percentage = overlapping.reduce((sum, o) => sum + o.overlap, 0);
  const totalUniqueCount = new Set([...holdingsA, ...holdingsB].map((h) => h.isin)).size;

  const verdict = deriveVerdict(percentage);

  return {
    percentage,
    overlappingCount: overlapping.length,
    totalUniqueCount,
    overlapping: overlapping.sort((a, b) => b.overlap - a.overlap),
    uniqueA,
    uniqueB,
    sectorBreakdown: [...sectorTotals.entries()]
      .map(([sector, v]) => ({ sector, ...v }))
      .sort((a, b) => b.weightA + b.weightB - (a.weightA + a.weightB)),
    verdict,
  };
}

/**
 * The conventional thresholds, presented as description of the numbers rather than advice.
 * These are banding conventions, not a recommendation to hold or change any fund.
 */
function deriveVerdict(percentage: number): DetailedOverlapResult['verdict'] {
  if (percentage < 20) {
    return {
      level: 'Low',
      color: 'text-emerald-400',
      title: 'Low overlap',
      description:
        'Below 20% is conventionally read as distinct holdings, which is what diversification usually intends.',
    };
  }
  if (percentage <= 40) {
    return {
      level: 'Moderate',
      color: 'text-amber-400',
      title: 'Moderate overlap',
      description:
        '20% to 40% is conventionally read as partial duplication, often acceptable when the mandates differ.',
    };
  }
  return {
    level: 'High',
    color: 'text-rose-400',
    title: 'High overlap',
    description:
      'Above 40% is conventionally read as substantial duplication: the two schemes are largely the same basket.',
  };
}
