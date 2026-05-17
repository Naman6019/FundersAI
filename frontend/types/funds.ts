export type DailyReturn = number;
export type FundPeriod = '1M' | '3M' | '6M' | '1Y' | '3Y' | '5Y';
export type CagrPeriod = '1Y' | '3Y' | '5Y';
export type MetricValue = string | number | null | undefined;

export type NavPoint = {
  date: string;
  nav: string;
};

export type RebasedNavPoint = NavPoint & {
  normalized: number;
};

export interface MFChartPoint {
  date: string;
  value: number;
}

export type FundReturns = Record<FundPeriod, number | null>;
export type FundCagrReturns = Record<CagrPeriod, number | null>;

export interface FundMeta {
  fund_house: string;
  scheme_type: string;
  scheme_category: string;
  scheme_code: number | string;
  scheme_name: string;
}

export interface FundDetails {
  scheme_code?: number | string | null;
  scheme_name?: string | null;
  fund_house?: string | null;
  category?: string | null;
  sub_category?: string | null;
  nav?: number | string | null;
  nav_date?: string | null;
  aum?: number | string | null;
  expense_ratio?: number | string | null;
  exit_load?: string | null;
  benchmark?: string | null;
  [key: string]: unknown;
}

export interface FundRiskMetrics {
  sharpeRatio?: number | null;
  sortinoRatio?: number | null;
  stdDev?: number | null;
  maxDrawdown?: number | null;
  beta?: number | null;
  alpha?: number | null;
  alpha_vs_nifty?: number | null;
  [key: string]: string | number | boolean | null | undefined;
}

export interface FundDataResponse {
  meta: FundMeta;
  data: NavPoint[];
  status: string;
  details?: FundDetails;
  returns?: Partial<FundReturns>;
  riskMetrics?: FundRiskMetrics | null;
  coverage?: Record<string, unknown>;
  freshness?: Record<string, unknown>;
}

export interface MFDetailApiResponse {
  details: FundDetails;
  returns?: Partial<FundCagrReturns>;
  riskMetrics?: FundRiskMetrics | null;
  chartData?: MFChartPoint[];
  fullData?: MFChartPoint[];
  historyCoverage?: Record<string, unknown>;
  freshness?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface SearchResultItem {
  id: string;
  type: 'MUTUAL_FUND' | 'STOCK';
  displayName: string;
  subLabel: string;
  identifier: string;
}

export interface FundHolding {
  isin?: string | null;
  name?: string | null;
  weight?: number | null;
  [key: string]: unknown;
}

export interface FundOverlapItem {
  isin: string;
  name: string;
  weightA: number;
  weightB: number;
  overlap: number;
}

export interface CanvasPayload {
  quant_data?: unknown;
  comparison?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface FundMetrics {
  returns: FundReturns;
  cagr: FundCagrReturns;
  alpha: number | null;
  beta: number | null;
  sharpe: number | null;
  stdDev: number | null;
}
