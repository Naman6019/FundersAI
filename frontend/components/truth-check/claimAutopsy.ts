import type { AtomicClaim, ClaimVerdict } from './types';

export type AutopsyField = {
  key: string;
  label: string;
  value: string;
  numericValue: number | null;
};

export type AutopsyValueRow = {
  entity: string;
  date: string | null;
  fields: AutopsyField[];
  primary: AutopsyField | null;
};

const METRIC_LABELS: Record<string, string> = {
  expense_ratio: 'Expense ratio',
  aum: 'Assets under management',
  cagr: 'CAGR',
  rolling_return: 'Rolling return',
  sharpe_ratio: 'Sharpe ratio',
  max_drawdown: 'Maximum drawdown',
  volatility: 'Volatility',
  riskometer: 'Riskometer',
  benchmark: 'Benchmark',
  fund_manager: 'Fund manager',
  holds_stock: 'Portfolio holding',
  stock_exposure: 'Stock exposure',
  sector_exposure: 'Sector exposure',
  holdings_concentration: 'Top-holdings concentration',
  portfolio_overlap: 'Portfolio overlap',
  investment_objective: 'Investment objective',
};

const OPERATOR_LABELS: Record<string, string> = {
  higher_than: 'is higher than',
  lower_than: 'is lower than',
  equal_to: 'equals',
  contains: 'contains',
  is: 'reported value',
};

const OPERATOR_SYMBOLS: Record<string, string> = {
  higher_than: '>',
  lower_than: '<',
  equal_to: '=',
  contains: 'contains',
  is: '=',
};

const PERCENT_METRICS = new Set([
  'expense_ratio',
  'cagr',
  'rolling_return',
  'max_drawdown',
  'volatility',
  'stock_exposure',
  'sector_exposure',
  'holdings_concentration',
  'portfolio_overlap',
]);

const TECHNICAL_KEYS = new Set(['as_of_date', 'as_of_dates', 'source_fingerprint', 'entities']);

export function titleCase(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function metricLabel(claim: AtomicClaim): string {
  const base = claim.metric ? METRIC_LABELS[claim.metric] || titleCase(claim.metric) : 'Metric not defined';
  const years = claim.statement.match(/\b(\d+)[-\s]?year\b/i)?.[1];
  if (!years || !['cagr', 'rolling_return'].includes(claim.metric || '')) return base;
  return `${years}-year ${base}`;
}

export function operatorLabel(operator: string | null): string {
  return operator ? OPERATOR_LABELS[operator] || titleCase(operator) : 'Operator not defined';
}

export function operatorSymbol(operator: string | null): string {
  return operator ? OPERATOR_SYMBOLS[operator] || titleCase(operator) : '?';
}

export function formatDate(value: string | null): string {
  if (!value) return 'Date unavailable';
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.valueOf())) return value;
  return parsed.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

export function formatMetricValue(metric: string | null, key: string, value: unknown): string {
  if (value === null || value === undefined) return 'Unavailable';
  if (typeof value !== 'number') return String(value);
  const formatted = value.toLocaleString('en-IN', { maximumFractionDigits: 3 });
  if (metric === 'aum' || key.includes('aum')) return `₹${formatted} crore`;
  if (PERCENT_METRICS.has(metric || '') || /return|volatility|drawdown|weight|overlap|exposure|cagr/.test(key)) {
    return `${formatted}%`;
  }
  return formatted;
}

export function extractAutopsyRows(claim: AtomicClaim): AutopsyValueRow[] {
  const rows: AutopsyValueRow[] = [];
  Object.entries(claim.values).forEach(([entity, raw]) => {
    if (TECHNICAL_KEYS.has(entity)) return;
    if (entity === 'total_overlap_weight_pct' && typeof raw === 'number') return;
    if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
      const record = raw as Record<string, unknown>;
      const fields = Object.entries(record)
        .filter(([key, value]) => !TECHNICAL_KEYS.has(key) && (typeof value === 'string' || typeof value === 'number'))
        .map(([key, value]) => ({
          key,
          label: key === 'value' ? metricLabel(claim) : titleCase(key),
          value: formatMetricValue(claim.metric, key, value),
          numericValue: typeof value === 'number' ? value : null,
        }));
      const preferred = fields.find((field) => field.key === 'value')
        || fields.find((field) => field.numericValue !== null)
        || fields[0]
        || null;
      rows.push({ entity, date: typeof record.as_of_date === 'string' ? record.as_of_date : null, fields, primary: preferred });
      return;
    }
    if (typeof raw === 'string' || typeof raw === 'number') {
      const field = {
        key: entity,
        label: metricLabel(claim),
        value: formatMetricValue(claim.metric, entity, raw),
        numericValue: typeof raw === 'number' ? raw : null,
      };
      rows.push({ entity: titleCase(entity), date: null, fields: [field], primary: field });
    }
  });

  if (!rows.length && typeof claim.values.total_overlap_weight_pct === 'number') {
    const value = claim.values.total_overlap_weight_pct;
    const field = {
      key: 'total_overlap_weight_pct',
      label: metricLabel(claim),
      value: formatMetricValue(claim.metric, 'total_overlap_weight_pct', value),
      numericValue: value,
    };
    rows.push({ entity: 'Compared portfolios', date: null, fields: [field], primary: field });
  }
  return rows;
}

function comparisonPhrase(operator: string | null, verdict: ClaimVerdict): string {
  const relation = operator === 'higher_than'
    ? 'greater than'
    : operator === 'lower_than'
      ? 'less than'
      : 'equal to';
  return verdict === 'supported' ? `is ${relation}` : `is not ${relation}`;
}

export function verdictTitle(claim: AtomicClaim): string {
  if (claim.status === 'clarification_required') return 'A definition is needed';
  if (claim.status === 'entity_resolution_required') return 'Fund identity needs confirmation';
  if (claim.status === 'unsupported') return 'Outside the supported research scope';
  if (claim.operator === 'is' && claim.verdict === 'supported') return 'Value found in the cited evidence';
  if (claim.verdict === 'supported') return claim.freshness === 'current' ? 'Supported by current cited evidence' : 'Supported for the cited period';
  if (claim.verdict === 'contradicted') return claim.freshness === 'current' ? 'Contradicted by current cited evidence' : 'Contradicted for the cited period';
  if (claim.verdict === 'mixed') return 'The cited evidence is mixed';
  return 'Not verifiable from available evidence';
}

export function buildExplanation(claim: AtomicClaim, rows: AutopsyValueRow[]): string {
  if (claim.clarification) return claim.clarification.prompt;
  if (claim.status !== 'evaluated') return claim.limitations[0] || 'This statement cannot be evaluated under the current evidence rules.';
  if (claim.verdict === 'unverifiable') return claim.limitations[0] || 'The available evidence is not sufficient for a deterministic verdict.';

  const dated = rows.filter((row) => row.date);
  const dateText = dated.length
    ? ` dated ${Array.from(new Set(dated.map((row) => formatDate(row.date)))).join(' and ')}`
    : '';
  const numericRows = rows.filter((row) => row.primary?.numericValue !== null && row.primary?.numericValue !== undefined);
  if (numericRows.length >= 2 && ['higher_than', 'lower_than', 'equal_to'].includes(claim.operator || '')) {
    const [first, second] = numericRows;
    return `Cited evidence${dateText} shows ${first.primary?.value} for ${first.entity} and ${second.primary?.value} for ${second.entity}. Because ${first.primary?.value} ${comparisonPhrase(claim.operator, claim.verdict)} ${second.primary?.value}, the claim is ${claim.verdict} for that cited period.`;
  }
  if (claim.metric === 'holds_stock' && rows[0]) {
    const holding = rows[0].fields.find((field) => field.key === 'holding')?.value;
    const weight = rows[0].fields.find((field) => field.key === 'weight_pct')?.value;
    return `The cited holdings disclosure${dateText} lists ${holding || 'the named security'}${weight ? ` at ${weight}` : ''} in ${rows[0].entity}. The claim is supported for that disclosure period.`;
  }
  if (rows[0]?.primary) {
    return `The cited evidence${dateText} reports ${metricLabel(claim).toLowerCase()} for ${rows[0].entity} as ${rows[0].primary.value}. This is a historical evidence lookup, not a recommendation.`;
  }
  return claim.limitations[0] || 'The result follows the displayed deterministic rule and cited evidence.';
}

export function comparisonRule(claim: AtomicClaim, rows: AutopsyValueRow[]): { rule: string; difference: string | null } {
  const numericRows = rows.filter((row) => row.primary?.numericValue !== null && row.primary?.numericValue !== undefined);
  if (numericRows.length < 2 || !['higher_than', 'lower_than', 'equal_to'].includes(claim.operator || '')) {
    const first = rows[0];
    return { rule: first?.primary ? `${first.entity}: ${first.primary.value}` : 'No deterministic comparison completed', difference: null };
  }
  const [first, second] = numericRows;
  const difference = Math.abs((first.primary?.numericValue || 0) - (second.primary?.numericValue || 0));
  const formattedDifference = formatMetricValue(claim.metric, 'difference', difference);
  return {
    rule: `${first.primary?.value} ${operatorSymbol(claim.operator)} ${second.primary?.value}`,
    difference: PERCENT_METRICS.has(claim.metric || '') ? `${formattedDifference.replace('%', '')} percentage points` : formattedDifference,
  };
}

export function freshnessMessage(claim: AtomicClaim): string {
  const dates = Array.from(new Set(claim.evidence.map((item) => item.as_of_date).filter((value): value is string => Boolean(value))));
  const suffix = dates.length ? ` The newest cited evidence is from ${formatDate(dates.sort().at(-1) || null)}.` : '';
  if (claim.freshness === 'stale') {
    const date = dates.sort().at(-1);
    return `Stale evidence — today's relationship is not confirmed.${date ? ` The data is as of ${formatDate(date)}.` : ''} Fund performance changes over time.`;
  }
  if (claim.freshness === 'unknown') return `Evidence freshness could not be established.${suffix}`;
  return `Evidence is current under the metric's freshness policy.${suffix}`;
}
