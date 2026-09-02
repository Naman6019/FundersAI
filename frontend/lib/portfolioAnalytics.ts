export type PortfolioAnalyticsPosition = {
  id: string;
  current_value: number | string;
};

export type PortfolioAnalyticsHolding = {
  isin?: string | null;
  security_name?: string | null;
  sector?: string | null;
  weight_pct?: number | string | null;
};

export type PortfolioAggregateOverlap = {
  coverage_status: 'unavailable' | 'partial' | 'available';
  position_count: number;
  positions_with_holdings: number;
  positions_without_holdings: number;
  total_current_value: number;
  covered_current_value: number;
  uncovered_current_value: number;
  total_overlap_exposure: number;
  total_overlap_percent: number | null;
  covered_overlap_percent: number | null;
  common_holding_count: number;
  top_common_holdings: Array<{
    isin: string | null;
    name: string;
    sector: string | null;
    fund_count: number;
    portfolio_exposure: number | null;
    overlap_exposure: number | null;
    overlap_exposure_value: number;
  }>;
};

function toNumber(value: unknown): number {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function holdingKey(row: PortfolioAnalyticsHolding): string | null {
  const isin = String(row.isin || '').trim().toUpperCase();
  if (isin && !['N/A', 'NA', 'NONE', 'NULL'].includes(isin)) return `isin:${isin}`;
  const name = String(row.security_name || '').trim().toLowerCase().replace(/\s+/g, ' ');
  return name ? `name:${name}` : null;
}

function hasUsableHoldingRows(rows: PortfolioAnalyticsHolding[]): boolean {
  return rows.some((row) => holdingKey(row) && toNumber(row.weight_pct) > 0);
}

/**
 * Calculates duplicated underlying exposure from the latest stored holdings.
 * A stock's duplicated exposure is total fund exposure minus its largest
 * single-fund contribution, so three funds do not create pairwise over-counting.
 */
export function calculateAggregateOverlap(
  positionRows: PortfolioAnalyticsPosition[] = [],
  holdingsByPosition: Record<string, PortfolioAnalyticsHolding[]> = {},
): PortfolioAggregateOverlap {
  const positions = Array.isArray(positionRows) ? positionRows : [];
  const assets = new Map<string, {
    isin: string | null;
    name: string;
    sector: string | null;
    contributions: Map<string, number>;
  }>();
  let totalCurrentValue = 0;
  let coveredCurrentValue = 0;

  for (const position of positions) {
    const positionId = String(position.id || '');
    const currentValue = Math.max(toNumber(position.current_value), 0);
    totalCurrentValue += currentValue;

    const rows = Array.isArray(holdingsByPosition[positionId]) ? holdingsByPosition[positionId] : [];
    const combined = new Map<string, {
      key: string;
      isin: string | null;
      name: string;
      sector: string | null;
      weight_pct: number;
    }>();
    for (const row of rows) {
      const key = holdingKey(row);
      const weight = toNumber(row.weight_pct);
      if (!key || weight <= 0) continue;
      const previous = combined.get(key);
      combined.set(key, {
        key,
        isin: row.isin || previous?.isin || null,
        name: row.security_name || previous?.name || 'Unclassified holding',
        sector: row.sector || previous?.sector || null,
        weight_pct: (previous?.weight_pct || 0) + weight,
      });
    }

    if (combined.size > 0) coveredCurrentValue += currentValue;
    for (const row of combined.values()) {
      const exposure = currentValue * row.weight_pct / 100;
      const asset = assets.get(row.key) || {
        isin: row.isin,
        name: row.name,
        sector: row.sector,
        contributions: new Map<string, number>(),
      };
      asset.contributions.set(positionId, (asset.contributions.get(positionId) || 0) + exposure);
      assets.set(row.key, asset);
    }
  }

  const commonHoldings: PortfolioAggregateOverlap['top_common_holdings'] = [];
  let totalOverlapExposure = 0;
  for (const asset of assets.values()) {
    if (asset.contributions.size < 2) continue;
    const exposures = [...asset.contributions.values()];
    const totalExposure = exposures.reduce((sum, value) => sum + value, 0);
    const largestSingleFundExposure = Math.max(...exposures);
    const overlapExposure = Math.max(totalExposure - largestSingleFundExposure, 0);
    totalOverlapExposure += overlapExposure;
    commonHoldings.push({
      isin: asset.isin,
      name: asset.name,
      sector: asset.sector,
      fund_count: asset.contributions.size,
      portfolio_exposure: totalCurrentValue > 0 ? (totalExposure / totalCurrentValue) * 100 : null,
      overlap_exposure: totalCurrentValue > 0 ? (overlapExposure / totalCurrentValue) * 100 : null,
      overlap_exposure_value: overlapExposure,
    });
  }

  commonHoldings.sort((a, b) => b.overlap_exposure_value - a.overlap_exposure_value);
  const missingPositionCount = positions.filter((position) => {
    const rows = holdingsByPosition[String(position.id || '')];
    return !Array.isArray(rows) || !hasUsableHoldingRows(rows);
  }).length;

  return {
    coverage_status: positions.length === 0 ? 'unavailable' : missingPositionCount > 0 ? 'partial' : 'available',
    position_count: positions.length,
    positions_with_holdings: positions.length - missingPositionCount,
    positions_without_holdings: missingPositionCount,
    total_current_value: totalCurrentValue,
    covered_current_value: coveredCurrentValue,
    uncovered_current_value: Math.max(totalCurrentValue - coveredCurrentValue, 0),
    total_overlap_exposure: totalOverlapExposure,
    total_overlap_percent: totalCurrentValue > 0 ? (totalOverlapExposure / totalCurrentValue) * 100 : null,
    covered_overlap_percent: coveredCurrentValue > 0 ? (totalOverlapExposure / coveredCurrentValue) * 100 : null,
    common_holding_count: commonHoldings.length,
    top_common_holdings: commonHoldings.slice(0, 20),
  };
}
