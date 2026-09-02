import type { SupabaseClient } from '@supabase/supabase-js';
import { calculateAggregateOverlap, type PortfolioAggregateOverlap } from '@/lib/portfolioAnalytics';
import { schemeDisplayName } from '@/lib/schemeDisplayName';

const NAV_FRESH_DAYS = 3;
const NAV_LAGGING_DAYS = 7;
const HOLDINGS_FRESH_DAYS = 45;
const HOLDINGS_LAGGING_DAYS = 75;

export type PortfolioRow = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
};

export type PortfolioPositionRow = {
  id: string;
  portfolio_id: string;
  scheme_code: number | string;
  units: number | string;
  current_value: number | string;
  position_source?: string | null;
  created_at: string;
  updated_at: string;
};

type CoreSnapshotRow = {
  scheme_code?: number | string | null;
  scheme_name?: string | null;
  plan_type?: string | null;
  option_type?: string | null;
  amc_name?: string | null;
  category?: string | null;
  nav_date?: string | null;
  last_updated?: string | null;
};

type NavCacheRow = {
  scheme_code?: number | string | null;
  last_nav_date?: string | null;
  expires_at?: string | null;
  fetched_at?: string | null;
  updated_at?: string | null;
  source?: string | null;
};

type FamilyMappingRow = {
  scheme_code?: string | null;
  family_id?: string | null;
};

export type PortfolioHoldingRow = {
  scheme_code?: number | string | null;
  family_id?: string | null;
  as_of_date?: string | null;
  security_name?: string | null;
  isin?: string | null;
  sector?: string | null;
  weight_pct?: number | string | null;
  source?: string | null;
};

export type FreshnessStatus = 'fresh' | 'lagging' | 'stale' | 'partial' | 'missing';

export type PositionFreshness = {
  status: FreshnessStatus;
  nav_status: 'fresh' | 'lagging' | 'stale' | 'missing';
  holdings_status: 'fresh' | 'lagging' | 'stale' | 'missing';
  nav_date: string | null;
  holdings_as_of_date: string | null;
  snapshot_last_updated: string | null;
  nav_source: string | null;
  note: string;
};

export type PortfolioPositionView = PortfolioPositionRow & {
  scheme_code: number;
  fund: {
    scheme_name: string | null;
    amc_name: string | null;
    category: string | null;
  };
  holdings_count: number;
  freshness: PositionFreshness;
};

export type PortfolioSnapshot = PortfolioRow & {
  positions: PortfolioPositionView[];
  total_current_value: number;
  aggregate_overlap: PortfolioAggregateOverlap;
  freshness: {
    status: FreshnessStatus;
    positions_with_nav: number;
    positions_with_holdings: number;
    positions_missing_data: number;
    latest_nav_date: string | null;
    latest_holdings_as_of_date: string | null;
  };
  research_boundary: string;
};

function asNumber(value: unknown): number {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function codeString(value: unknown): string {
  return String(value ?? '').trim();
}

function parseDate(value: unknown): Date | null {
  if (!value) return null;
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function dateOnly(value: unknown): string | null {
  const raw = String(value ?? '').trim();
  return /^\d{4}-\d{2}-\d{2}/.test(raw) ? raw.slice(0, 10) : null;
}

function ageInDays(value: string | null, now: Date): number | null {
  const parsed = parseDate(value);
  if (!parsed) return null;
  return Math.max(0, (now.getTime() - parsed.getTime()) / 86_400_000);
}

function classifyAge(
  value: string | null,
  now: Date,
  freshDays: number,
  laggingDays: number,
): 'fresh' | 'lagging' | 'stale' | 'missing' {
  const age = ageInDays(value, now);
  if (age === null) return 'missing';
  if (age <= freshDays) return 'fresh';
  if (age <= laggingDays) return 'lagging';
  return 'stale';
}

export function classifyPortfolioFreshness(
  navDate: string | null,
  holdingsDate: string | null,
  now = new Date(),
): PositionFreshness {
  const navStatus = classifyAge(navDate, now, NAV_FRESH_DAYS, NAV_LAGGING_DAYS);
  const holdingsStatus = classifyAge(holdingsDate, now, HOLDINGS_FRESH_DAYS, HOLDINGS_LAGGING_DAYS);
  let status: FreshnessStatus = 'fresh';
  if (navStatus === 'missing' && holdingsStatus === 'missing') status = 'missing';
  else if (navStatus === 'stale' || holdingsStatus === 'stale') status = 'stale';
  else if (navStatus === 'missing' || holdingsStatus === 'missing') status = 'partial';
  else if (navStatus === 'lagging' || holdingsStatus === 'lagging') status = 'lagging';

  const note = status === 'fresh'
    ? 'Stored NAV and holdings dates are within the phase 1 display windows.'
    : status === 'lagging'
      ? 'Stored data exists but one source is behind its display window.'
      : status === 'stale'
        ? 'Stored data is outside its display window; verify the source dates before interpreting overlap.'
        : status === 'partial'
          ? 'One source is available and another is missing.'
          : 'No usable stored NAV or holdings date was found.';

  return {
    status,
    nav_status: navStatus,
    holdings_status: holdingsStatus,
    nav_date: navDate,
    holdings_as_of_date: holdingsDate,
    snapshot_last_updated: null,
    nav_source: null,
    note,
  };
}

async function readRows<T>(query: PromiseLike<{ data: T[] | null; error: unknown }>): Promise<T[]> {
  try {
    const response = await query;
    return response.error ? [] : response.data || [];
  } catch {
    return [];
  }
}

function latestHoldings(rows: PortfolioHoldingRow[]): PortfolioHoldingRow[] {
  if (!rows.length) return [];
  const datedRows = rows.filter((row) => dateOnly(row.as_of_date));
  if (!datedRows.length) return rows;
  const latest = datedRows.reduce((max, row) => {
    const date = dateOnly(row.as_of_date) || '';
    return date > max ? date : max;
  }, '');
  return datedRows.filter((row) => dateOnly(row.as_of_date) === latest);
}

function aggregateStatus(statuses: FreshnessStatus[]): FreshnessStatus {
  if (!statuses.length) return 'missing';
  if (statuses.every((status) => status === 'missing')) return 'missing';
  if (statuses.includes('stale')) return 'stale';
  if (statuses.includes('missing') || statuses.includes('partial')) return 'partial';
  if (statuses.includes('lagging')) return 'lagging';
  return 'fresh';
}

export async function buildPortfolioSnapshots(
  portfolios: PortfolioRow[],
  positions: PortfolioPositionRow[],
  supabaseAdmin: SupabaseClient,
  now = new Date(),
): Promise<PortfolioSnapshot[]> {
  const codes = [...new Set(positions.map((position) => codeString(position.scheme_code)).filter(Boolean))];
  const numericCodes = codes.map((code) => Number(code)).filter((code) => Number.isInteger(code) && code > 0);
  if (!codes.length) {
    return portfolios.map((portfolio) => ({
      ...portfolio,
      positions: [],
      total_current_value: 0,
      aggregate_overlap: calculateAggregateOverlap([], {}),
      freshness: {
        status: 'missing',
        positions_with_nav: 0,
        positions_with_holdings: 0,
        positions_missing_data: 0,
        latest_nav_date: null,
        latest_holdings_as_of_date: null,
      },
      research_boundary: 'Manual position snapshot only. Overlap is a read-only research signal from stored holdings, not an investment recommendation.',
    }));
  }

  const [coreRows, navCacheRows, familyRows, directHoldingRows] = await Promise.all([
    readRows<CoreSnapshotRow>(supabaseAdmin
      .from('mutual_fund_core_snapshot')
      .select('scheme_code,scheme_name,plan_type,option_type,amc_name,category,nav_date,last_updated')
      .in('scheme_code', codes)),
    readRows<NavCacheRow>(supabaseAdmin
      .from('nav_api_cache')
      .select('scheme_code,last_nav_date,expires_at,fetched_at,updated_at,source')
      .in('scheme_code', codes)),
    readRows<FamilyMappingRow>(supabaseAdmin
      .from('mutual_fund_family_mapping')
      .select('scheme_code,family_id')
      .in('scheme_code', codes)),
    readRows<PortfolioHoldingRow>(supabaseAdmin
      .from('mutual_fund_holdings')
      .select('scheme_code,family_id,as_of_date,security_name,isin,sector,weight_pct,source')
      .in('scheme_code', numericCodes)
      .order('as_of_date', { ascending: false })
      .limit(5000)),
  ]);

  const familyIds = [...new Set(familyRows.map((row) => String(row.family_id || '').trim()).filter(Boolean))];
  const familyHoldingRows = familyIds.length
    ? await readRows<PortfolioHoldingRow>(supabaseAdmin
      .from('mutual_fund_holdings')
      .select('scheme_code,family_id,as_of_date,security_name,isin,sector,weight_pct,source')
      .in('family_id', familyIds)
      .order('as_of_date', { ascending: false })
      .limit(5000))
    : [];

  const coreByCode = new Map(coreRows.map((row) => [codeString(row.scheme_code), row]));
  const cacheByCode = new Map(navCacheRows.map((row) => [codeString(row.scheme_code), row]));
  const familyByCode = new Map(familyRows.map((row) => [codeString(row.scheme_code), String(row.family_id || '')]));
  const positionsByPortfolio = new Map<string, PortfolioPositionRow[]>();

  for (const position of positions) {
    const list = positionsByPortfolio.get(position.portfolio_id) || [];
    list.push(position);
    positionsByPortfolio.set(position.portfolio_id, list);
  }

  return portfolios.map((portfolio) => {
    const portfolioPositions = positionsByPortfolio.get(portfolio.id) || [];
    const holdingsByPosition: Record<string, PortfolioHoldingRow[]> = {};
    const positionViews = portfolioPositions.map((position) => {
      const code = codeString(position.scheme_code);
      const familyId = familyByCode.get(code);
      const familyCandidates = familyId
        ? familyHoldingRows.filter((row) => String(row.family_id || '') === familyId)
        : [];
      const directCandidates = directHoldingRows.filter((row) => codeString(row.scheme_code) === code);
      const candidates = familyCandidates.length ? familyCandidates : directCandidates;
      const holdings = latestHoldings(candidates);
      holdingsByPosition[position.id] = holdings;

      const core = coreByCode.get(code);
      const cache = cacheByCode.get(code);
      const navDate = dateOnly(cache?.last_nav_date) || dateOnly(core?.nav_date);
      const holdingsDate = holdings.reduce<string | null>((latest, row) => {
        const value = dateOnly(row.as_of_date);
        return value && (!latest || value > latest) ? value : latest;
      }, null);
      const freshness = classifyPortfolioFreshness(navDate, holdingsDate, now);
      freshness.snapshot_last_updated = core?.last_updated || cache?.updated_at || null;
      freshness.nav_source = cache?.source || 'FundersAI stored snapshot';

      return {
        ...position,
        scheme_code: Number(code),
        units: asNumber(position.units),
        current_value: asNumber(position.current_value),
        fund: {
          scheme_name: core ? schemeDisplayName(core) : null,
          amc_name: core?.amc_name || null,
          category: core?.category || null,
        },
        holdings_count: holdings.length,
        freshness,
      };
    });

    const aggregateOverlap = calculateAggregateOverlap(positionViews, holdingsByPosition);
    const freshnessStatuses = positionViews.map((position) => position.freshness.status);
    const latestNavDate = positionViews.reduce<string | null>((latest, position) => {
      const value = position.freshness.nav_date;
      return value && (!latest || value > latest) ? value : latest;
    }, null);
    const latestHoldingsDate = positionViews.reduce<string | null>((latest, position) => {
      const value = position.freshness.holdings_as_of_date;
      return value && (!latest || value > latest) ? value : latest;
    }, null);

    return {
      ...portfolio,
      positions: positionViews,
      total_current_value: aggregateOverlap.total_current_value,
      aggregate_overlap: aggregateOverlap,
      freshness: {
        status: aggregateStatus(freshnessStatuses),
        positions_with_nav: positionViews.filter((position) => position.freshness.nav_date).length,
        positions_with_holdings: positionViews.filter((position) => position.holdings_count > 0).length,
        positions_missing_data: positionViews.filter((position) => position.freshness.status === 'missing').length,
        latest_nav_date: latestNavDate,
        latest_holdings_as_of_date: latestHoldingsDate,
      },
      research_boundary: 'Manual position snapshot only. Overlap is a read-only research signal from stored holdings, not an investment recommendation.',
    };
  });
}
