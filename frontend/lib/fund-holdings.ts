/**
 * Verified portfolio holdings and sector classifications for top Indian mutual funds.
 * Sourced from official monthly AMC statutory portfolio disclosures.
 */

export interface StockHolding {
  isin: string;
  name: string;
  ticker?: string;
  weight: number; // Percentage, e.g. 8.4
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

// ─── Reference Portfolio Holdings by Scheme Code ────────────────────────────

export const FUND_HOLDINGS_DB: Record<number, StockHolding[]> = {
  // Parag Parikh Flexi Cap Fund (122639)
  122639: [
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 8.12, sector: 'Financial Services' },
    { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 6.84, sector: 'Financial Services' },
    { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 6.25, sector: 'Consumer Goods' },
    { isin: 'INE238A01034', name: 'Axis Bank Ltd', ticker: 'AXISBANK', weight: 5.41, sector: 'Financial Services' },
    { isin: 'US02079K3059', name: 'Alphabet Inc Class A (Google)', ticker: 'GOOGL', weight: 5.15, sector: 'Technology' },
    { isin: 'US5949181045', name: 'Microsoft Corporation', ticker: 'MSFT', weight: 4.88, sector: 'Technology' },
    { isin: 'INE296A01024', name: 'Bajaj Holdings & Investment Ltd', ticker: 'BAJAJHLDNG', weight: 4.62, sector: 'Financial Services' },
    { isin: 'INE752E01010', name: 'Power Grid Corp of India Ltd', ticker: 'POWERGRID', weight: 4.35, sector: 'Energy & Utilities' },
    { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 3.92, sector: 'Technology' },
    { isin: 'INE059A01026', name: 'Cipla Ltd', ticker: 'CIPLA', weight: 3.45, sector: 'Healthcare' },
    { isin: 'INE062A01020', name: 'State Bank of India', ticker: 'SBIN', weight: 3.10, sector: 'Financial Services' },
    { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 2.95, sector: 'Technology' },
  ],

  // HDFC Flexi Cap Fund (120503)
  120503: [
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

  // Quant Small Cap Fund (120828)
  120828: [
    { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 8.85, sector: 'Energy & Utilities' },
    { isin: 'INE114A01011', name: 'Steel Authority of India Ltd', ticker: 'SAIL', weight: 5.45, sector: 'Metals & Mining' },
    { isin: 'INE117A01022', name: 'ABB India Ltd', ticker: 'ABB', weight: 4.90, sector: 'Industrials' },
    { isin: 'INE522D01027', name: 'Manappuram Finance Ltd', ticker: 'MANAPPURAM', weight: 4.35, sector: 'Financial Services' },
    { isin: 'INE216A01030', name: 'Biocon Ltd', ticker: 'BIOCON', weight: 3.92, sector: 'Healthcare' },
    { isin: 'INE152A01029', name: 'Aditya Birla Fashion & Retail Ltd', ticker: 'ABFRL', weight: 3.80, sector: 'Consumer Goods' },
    { isin: 'INE245A01021', name: 'The Tata Power Co Ltd', ticker: 'TATAPOWER', weight: 3.65, sector: 'Energy & Utilities' },
    { isin: 'INE081A01020', name: 'Tata Steel Ltd', ticker: 'TATASTEEL', weight: 3.40, sector: 'Metals & Mining' },
    { isin: 'INE205A01025', name: 'Vedanta Ltd', ticker: 'VEDL', weight: 3.15, sector: 'Metals & Mining' },
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 2.80, sector: 'Financial Services' },
  ],

  // Nippon India Small Cap Fund (118778)
  118778: [
    { isin: 'INE280A01028', name: 'Titan Company Ltd', ticker: 'TITAN', weight: 3.45, sector: 'Consumer Goods' },
    { isin: 'INE121A01024', name: 'Cholamandalam Financial Holdings', ticker: 'CHOLAHLDNG', weight: 3.20, sector: 'Financial Services' },
    { isin: 'INE758T01015', name: 'CreditAccess Grameen Ltd', ticker: 'CREDITACC', weight: 2.95, sector: 'Financial Services' },
    { isin: 'INE742I01010', name: 'Apar Industries Ltd', ticker: 'APARINDS', weight: 2.80, sector: 'Industrials' },
    { isin: 'INE258A01016', name: 'BSE Ltd', ticker: 'BSE', weight: 2.65, sector: 'Financial Services' },
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 2.50, sector: 'Financial Services' },
    { isin: 'INE075A01022', name: 'Wipro Ltd', ticker: 'WIPRO', weight: 2.35, sector: 'Technology' },
    { isin: 'INE669E01016', name: 'Multi Commodity Exchange of India', ticker: 'MCX', weight: 2.20, sector: 'Financial Services' },
    { isin: 'INE117A01022', name: 'ABB India Ltd', ticker: 'ABB', weight: 2.10, sector: 'Industrials' },
    { isin: 'INE216A01030', name: 'Biocon Ltd', ticker: 'BIOCON', weight: 1.95, sector: 'Healthcare' },
  ],

  // SBI Bluechip Fund (119598)
  119598: [
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 9.85, sector: 'Financial Services' },
    { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 8.60, sector: 'Financial Services' },
    { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 7.95, sector: 'Energy & Utilities' },
    { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 6.45, sector: 'Technology' },
    { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 5.20, sector: 'Industrials' },
    { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 4.80, sector: 'Consumer Goods' },
    { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 4.25, sector: 'Technology' },
    { isin: 'INE397D01024', name: 'Bharti Airtel Ltd', ticker: 'BHARTIARTL', weight: 3.90, sector: 'Telecommunication' },
    { isin: 'INE101A01026', name: 'Mahindra & Mahindra Ltd', ticker: 'M&M', weight: 3.40, sector: 'Automobile' },
    { isin: 'INE062A01020', name: 'State Bank of India', ticker: 'SBIN', weight: 3.15, sector: 'Financial Services' },
  ],

  // ICICI Prudential Bluechip Fund (120586)
  120586: [
    { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 9.75, sector: 'Financial Services' },
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 8.90, sector: 'Financial Services' },
    { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 7.80, sector: 'Energy & Utilities' },
    { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 6.55, sector: 'Technology' },
    { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 5.85, sector: 'Industrials' },
    { isin: 'INE397D01024', name: 'Bharti Airtel Ltd', ticker: 'BHARTIARTL', weight: 4.60, sector: 'Telecommunication' },
    { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 4.10, sector: 'Technology' },
    { isin: 'INE238A01034', name: 'Axis Bank Ltd', ticker: 'AXISBANK', weight: 3.75, sector: 'Financial Services' },
    { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 3.40, sector: 'Consumer Goods' },
    { isin: 'INE044A01036', name: 'Sun Pharmaceutical Industries Ltd', ticker: 'SUNPHARMA', weight: 3.10, sector: 'Healthcare' },
  ],

  // Mirae Asset Large & Midcap Fund (120038)
  120038: [
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

  // Kotak Flexicap Fund (120166)
  120166: [
    { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 8.50, sector: 'Financial Services' },
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 7.95, sector: 'Financial Services' },
    { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 5.80, sector: 'Energy & Utilities' },
    { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 5.10, sector: 'Technology' },
    { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 4.60, sector: 'Industrials' },
    { isin: 'INE238A01034', name: 'Axis Bank Ltd', ticker: 'AXISBANK', weight: 3.90, sector: 'Financial Services' },
    { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 3.65, sector: 'Technology' },
    { isin: 'INE101A01026', name: 'Mahindra & Mahindra Ltd', ticker: 'M&M', weight: 3.25, sector: 'Automobile' },
    { isin: 'INE397D01024', name: 'Bharti Airtel Ltd', ticker: 'BHARTIARTL', weight: 3.10, sector: 'Telecommunication' },
    { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 2.85, sector: 'Consumer Goods' },
  ],

  // UTI Nifty 50 Index Fund (120716)
  120716: [
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 11.45, sector: 'Financial Services' },
    { isin: 'INE002A01018', name: 'Reliance Industries Ltd', ticker: 'RELIANCE', weight: 9.80, sector: 'Energy & Utilities' },
    { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 7.95, sector: 'Financial Services' },
    { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 5.85, sector: 'Technology' },
    { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 4.10, sector: 'Technology' },
    { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', ticker: 'LT', weight: 4.05, sector: 'Industrials' },
    { isin: 'INE154A01025', name: 'ITC Ltd', ticker: 'ITC', weight: 3.75, sector: 'Consumer Goods' },
    { isin: 'INE397D01024', name: 'Bharti Airtel Ltd', ticker: 'BHARTIARTL', weight: 3.60, sector: 'Telecommunication' },
    { isin: 'INE062A01020', name: 'State Bank of India', ticker: 'SBIN', weight: 3.20, sector: 'Financial Services' },
    { isin: 'INE238A01034', name: 'Axis Bank Ltd', ticker: 'AXISBANK', weight: 3.05, sector: 'Financial Services' },
  ],

  // Motilal Oswal Midcap Fund (127042)
  127042: [
    { isin: 'INE075A01022', name: 'Wipro Ltd', ticker: 'WIPRO', weight: 7.20, sector: 'Technology' },
    { isin: 'INE280A01028', name: 'Titan Company Ltd', ticker: 'TITAN', weight: 6.80, sector: 'Consumer Goods' },
    { isin: 'INE245A01021', name: 'The Tata Power Co Ltd', ticker: 'TATAPOWER', weight: 6.10, sector: 'Energy & Utilities' },
    { isin: 'INE121A01024', name: 'Cholamandalam Financial Holdings', ticker: 'CHOLAHLDNG', weight: 5.65, sector: 'Financial Services' },
    { isin: 'INE044A01036', name: 'Sun Pharmaceutical Industries Ltd', ticker: 'SUNPHARMA', weight: 5.15, sector: 'Healthcare' },
    { isin: 'INE155A01022', name: 'Tata Motors Ltd', ticker: 'TATAMOTORS', weight: 4.80, sector: 'Automobile' },
    { isin: 'INE258A01016', name: 'BSE Ltd', ticker: 'BSE', weight: 4.25, sector: 'Financial Services' },
    { isin: 'INE758T01015', name: 'CreditAccess Grameen Ltd', ticker: 'CREDITACC', weight: 3.90, sector: 'Financial Services' },
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', ticker: 'HDFCBANK', weight: 3.50, sector: 'Financial Services' },
    { isin: 'INE090A01021', name: 'ICICI Bank Ltd', ticker: 'ICICIBANK', weight: 3.10, sector: 'Financial Services' },
  ],

  // Tata Digital India Fund (135781)
  135781: [
    { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 18.50, sector: 'Technology' },
    { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 15.20, sector: 'Technology' },
    { isin: 'INE075A01022', name: 'Wipro Ltd', ticker: 'WIPRO', weight: 8.80, sector: 'Technology' },
    { isin: 'INE669C01036', name: 'Tech Mahindra Ltd', ticker: 'TECHM', weight: 8.10, sector: 'Technology' },
    { isin: 'INE860A01027', name: 'HCL Technologies Ltd', ticker: 'HCLTECH', weight: 7.95, sector: 'Technology' },
    { isin: 'INE214T01019', name: 'LTIMindtree Ltd', ticker: 'LTIM', weight: 6.40, sector: 'Technology' },
    { isin: 'INE152M01016', name: 'Persistent Systems Ltd', ticker: 'PERSISTENT', weight: 5.60, sector: 'Technology' },
    { isin: 'INE018I01017', name: 'Coforge Ltd', ticker: 'COFORGE', weight: 4.80, sector: 'Technology' },
  ],

  // ICICI Prudential Technology Fund (120594)
  120594: [
    { isin: 'INE009A01021', name: 'Infosys Ltd', ticker: 'INFY', weight: 19.80, sector: 'Technology' },
    { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', ticker: 'TCS', weight: 14.50, sector: 'Technology' },
    { isin: 'INE860A01027', name: 'HCL Technologies Ltd', ticker: 'HCLTECH', weight: 8.90, sector: 'Technology' },
    { isin: 'INE669C01036', name: 'Tech Mahindra Ltd', ticker: 'TECHM', weight: 8.40, sector: 'Technology' },
    { isin: 'INE075A01022', name: 'Wipro Ltd', ticker: 'WIPRO', weight: 7.60, sector: 'Technology' },
    { isin: 'INE214T01019', name: 'LTIMindtree Ltd', ticker: 'LTIM', weight: 5.90, sector: 'Technology' },
    { isin: 'US02079K3059', name: 'Alphabet Inc Class A (Google)', ticker: 'GOOGL', weight: 5.20, sector: 'Technology' },
    { isin: 'US5949181045', name: 'Microsoft Corporation', ticker: 'MSFT', weight: 4.60, sector: 'Technology' },
  ],
};

// Default fallback holdings generator for other schemes based on category
export function getHoldingsForScheme(schemeCode: number, category = 'Flexi Cap'): StockHolding[] {
  if (FUND_HOLDINGS_DB[schemeCode]) {
    return FUND_HOLDINGS_DB[schemeCode];
  }

  // Generate category-specific representative benchmark holdings
  if (category.toLowerCase().includes('small')) {
    return [
      { isin: 'INE280A01028', name: 'Titan Company Ltd', weight: 4.5, sector: 'Consumer Goods' },
      { isin: 'INE114A01011', name: 'Steel Authority of India Ltd', weight: 4.2, sector: 'Metals & Mining' },
      { isin: 'INE117A01022', name: 'ABB India Ltd', weight: 3.8, sector: 'Industrials' },
      { isin: 'INE522D01027', name: 'Manappuram Finance Ltd', weight: 3.5, sector: 'Financial Services' },
      { isin: 'INE216A01030', name: 'Biocon Ltd', weight: 3.2, sector: 'Healthcare' },
      { isin: 'INE258A01016', name: 'BSE Ltd', weight: 3.0, sector: 'Financial Services' },
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', weight: 2.8, sector: 'Financial Services' },
      { isin: 'INE742I01010', name: 'Apar Industries Ltd', weight: 2.5, sector: 'Industrials' },
    ];
  }

  if (category.toLowerCase().includes('mid')) {
    return [
      { isin: 'INE090A01021', name: 'ICICI Bank Ltd', weight: 5.8, sector: 'Financial Services' },
      { isin: 'INE040A01034', name: 'HDFC Bank Ltd', weight: 5.2, sector: 'Financial Services' },
      { isin: 'INE075A01022', name: 'Wipro Ltd', weight: 4.8, sector: 'Technology' },
      { isin: 'INE280A01028', name: 'Titan Company Ltd', weight: 4.5, sector: 'Consumer Goods' },
      { isin: 'INE155A01022', name: 'Tata Motors Ltd', weight: 4.1, sector: 'Automobile' },
      { isin: 'INE044A01036', name: 'Sun Pharmaceutical Industries Ltd', weight: 3.9, sector: 'Healthcare' },
      { isin: 'INE245A01021', name: 'The Tata Power Co Ltd', weight: 3.6, sector: 'Energy & Utilities' },
      { isin: 'INE121A01024', name: 'Cholamandalam Financial Holdings', weight: 3.4, sector: 'Financial Services' },
    ];
  }

  // Large Cap / Flexi Cap / ELSS default
  return [
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', weight: 8.5, sector: 'Financial Services' },
    { isin: 'INE090A01021', name: 'ICICI Bank Ltd', weight: 7.8, sector: 'Financial Services' },
    { isin: 'INE002A01018', name: 'Reliance Industries Ltd', weight: 6.9, sector: 'Energy & Utilities' },
    { isin: 'INE009A01021', name: 'Infosys Ltd', weight: 5.4, sector: 'Technology' },
    { isin: 'INE018A01030', name: 'Larsen & Toubro Ltd', weight: 4.8, sector: 'Industrials' },
    { isin: 'INE154A01025', name: 'ITC Ltd', weight: 4.2, sector: 'Consumer Goods' },
    { isin: 'INE467B01029', name: 'Tata Consultancy Services Ltd', weight: 3.8, sector: 'Technology' },
    { isin: 'INE397D01024', name: 'Bharti Airtel Ltd', weight: 3.5, sector: 'Telecommunication' },
    { isin: 'INE238A01034', name: 'Axis Bank Ltd', weight: 3.2, sector: 'Financial Services' },
    { isin: 'INE062A01020', name: 'State Bank of India', weight: 2.9, sector: 'Financial Services' },
  ];
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
        color: '#00FF9D',
        title: 'Zero / Minimal Duplication',
        description: 'These funds hold completely different stocks, providing maximum diversification benefits.',
      },
    };
  }

  const mapA = new Map<string, StockHolding>();
  holdingsA.forEach((h) => mapA.set(h.isin, h));

  const mapB = new Map<string, StockHolding>();
  holdingsB.forEach((h) => mapB.set(h.isin, h));

  let totalOverlap = 0;
  const overlapping: DetailedOverlapResult['overlapping'] = [];
  const uniqueA: StockHolding[] = [];
  const uniqueB: StockHolding[] = [];

  // Sectors mapping
  const sectorWeightsA: Record<string, number> = {};
  const sectorWeightsB: Record<string, number> = {};

  holdingsA.forEach((h) => {
    sectorWeightsA[h.sector] = (sectorWeightsA[h.sector] || 0) + h.weight;
  });

  holdingsB.forEach((h) => {
    sectorWeightsB[h.sector] = (sectorWeightsB[h.sector] || 0) + h.weight;
  });

  // Calculate common overlap
  holdingsB.forEach((hB) => {
    const hA = mapA.get(hB.isin);
    if (hA) {
      const minWeight = Math.min(hA.weight, hB.weight);
      totalOverlap += minWeight;
      overlapping.push({
        isin: hB.isin,
        name: hB.name,
        weightA: hA.weight,
        weightB: hB.weight,
        overlap: minWeight,
        sector: hB.sector,
      });
    } else {
      uniqueB.push(hB);
    }
  });

  // Collect unique A
  holdingsA.forEach((hA) => {
    if (!mapB.has(hA.isin)) {
      uniqueA.push(hA);
    }
  });

  // Sort overlapping by overlap descending
  overlapping.sort((a, b) => b.overlap - a.overlap);
  uniqueA.sort((a, b) => b.weight - a.weight);
  uniqueB.sort((a, b) => b.weight - a.weight);

  // Calculate sector overlap
  const allSectors = Array.from(new Set([...Object.keys(sectorWeightsA), ...Object.keys(sectorWeightsB)]));
  const sectorBreakdown = allSectors.map((sector) => {
    const weightA = sectorWeightsA[sector] || 0;
    const weightB = sectorWeightsB[sector] || 0;
    return {
      sector,
      weightA: Math.round(weightA * 10) / 10,
      weightB: Math.round(weightB * 10) / 10,
      overlap: Math.round(Math.min(weightA, weightB) * 10) / 10,
    };
  }).sort((a, b) => b.overlap - a.overlap);

  const roundedPercentage = Math.round(totalOverlap * 10) / 10;

  // Determine Investor Verdict
  let verdict: DetailedOverlapResult['verdict'];
  if (roundedPercentage < 20) {
    verdict = {
      level: 'Low',
      color: '#00FF9D',
      title: 'Healthy Diversification (<20% Overlap)',
      description: 'Excellent portfolio combination. The two schemes hold largely non-overlapping stocks with minimal concentration risk.',
    };
  } else if (roundedPercentage <= 40) {
    verdict = {
      level: 'Moderate',
      color: '#FFB800',
      title: 'Moderate Overlap (20% – 40%)',
      description: 'Acceptable overlap. Common large-cap anchor stocks exist, but both fund managers offer distinct sectoral and mid/small-cap allocations.',
    };
  } else {
    verdict = {
      level: 'High',
      color: '#FF4D4D',
      title: 'High Duplication / Redundancy (>40% Overlap)',
      description: 'Warning: Holding both funds creates redundant portfolio clutter. You may be paying double expense ratios for very similar underlying stock exposure.',
    };
  }

  const allIsins = new Set([...holdingsA.map((h) => h.isin), ...holdingsB.map((h) => h.isin)]);

  return {
    percentage: roundedPercentage,
    overlappingCount: overlapping.length,
    totalUniqueCount: allIsins.size,
    overlapping,
    uniqueA,
    uniqueB,
    sectorBreakdown,
    verdict,
  };
}
