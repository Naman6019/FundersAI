export type DataHealthMetric = {
  label: string;
  status: string;
  note?: string | null;
  last_updated?: string | null;
};

export type DataHealthPipeline = {
  source_table?: string;
  total_documents?: number;
  parsed_count?: number;
  pending_count?: number;
  failed_count?: number;
  needs_review_count?: number;
  skipped_count?: number;
  last_downloaded_at?: string | null;
  last_parse_attempt_at?: string | null;
  last_success_at?: string | null;
  last_failure_at?: string | null;
};

export type AmcParserQuality = {
  amc: string;
  latest_factsheet_month?: string | null;
  latest_holdings_month?: string | null;
  total_funds?: number;
  ter_count?: number;
  benchmark_count?: number;
  risk_label_count?: number;
  ter_coverage?: number;
  benchmark_coverage?: number;
  risk_label_coverage?: number;
  parse_review_count?: number;
  holdings_source_note?: string | null;
};

export type DataHealthPayload = {
  status: string;
  source?: string;
  checked_at?: string | null;
  metrics: DataHealthMetric[];
  pipeline?: DataHealthPipeline;
  amc_parser_quality?: AmcParserQuality[];
};

export const DEFAULT_DATA_HEALTH: DataHealthMetric[] = [
  { label: 'MF NAV', status: 'Checking', note: 'Checking the latest expected business-day NAV.' },
  { label: 'AUM / TER', status: 'Checking', note: 'Checking stored AUM and expense-ratio coverage.' },
  { label: 'Risk metrics', status: 'Checking', note: 'Checking stored risk-metric coverage.' },
  { label: 'AMC docs', status: 'Checking', note: 'Checking official-document parsing and indexing.' },
];

export const STATUS_GLOSSARY: Record<string, string> = {
  Fresh: 'The latest expected business-day data is available.',
  Synced: 'The stored enrichment is within its expected update window.',
  Ready: 'Enough current structured data is available for this calculation.',
  Indexed: 'The latest available official documents were parsed and indexed.',
  Checking: 'FundersAI is reading the current stored status.',
  Processing: 'New material is being acquired, parsed, reviewed, or indexed.',
  Lagging: 'Data exists but is behind its expected update window.',
  Partial: 'Some expected fields or documents are available and others are missing.',
  Stale: 'The latest available data is outside its accepted freshness window.',
  Missing: 'No usable stored data was found for this label.',
  Error: 'The status or underlying data could not be read.',
};

const HEALTHY = new Set(['fresh', 'synced', 'ready', 'indexed']);
const IN_PROGRESS = new Set(['checking', 'processing']);
const ATTENTION = new Set(['lagging', 'partial']);
const UNAVAILABLE = new Set(['stale', 'missing', 'error']);

export type StatusSeverity = 'healthy' | 'in_progress' | 'attention' | 'unavailable' | 'neutral';

export function statusSeverity(status: string): StatusSeverity {
  const normalized = String(status || '').trim().toLowerCase();
  if (HEALTHY.has(normalized)) return 'healthy';
  if (IN_PROGRESS.has(normalized)) return 'in_progress';
  if (ATTENTION.has(normalized)) return 'attention';
  if (UNAVAILABLE.has(normalized)) return 'unavailable';
  return 'neutral';
}

export function statusColorClass(status: string): string {
  switch (statusSeverity(status)) {
    case 'healthy':
      return 'text-emerald-300';
    case 'in_progress':
      return 'text-sky-300';
    case 'attention':
      return 'text-amber-300';
    case 'unavailable':
      return 'text-rose-300';
    default:
      return 'text-slate-300';
  }
}

export function statusDotClass(status: string): string {
  switch (statusSeverity(status)) {
    case 'healthy':
      return 'bg-emerald-300';
    case 'in_progress':
      return 'bg-sky-300';
    case 'attention':
      return 'bg-amber-300';
    case 'unavailable':
      return 'bg-rose-300';
    default:
      return 'bg-slate-400';
  }
}

export function statusExplanation(status: string): string {
  const normalized = String(status || '').trim().toLowerCase();
  const key = Object.keys(STATUS_GLOSSARY).find((candidate) => candidate.toLowerCase() === normalized);
  return key ? STATUS_GLOSSARY[key] : 'No standard explanation is available for this status.';
}

export function mergeDataHealthMetrics(metrics: unknown): DataHealthMetric[] {
  const incoming = Array.isArray(metrics)
    ? metrics.filter((item): item is DataHealthMetric => Boolean(item && typeof item === 'object' && 'label' in item))
    : [];
  const byLabel = new Map(incoming.map((item) => [String(item.label), item]));
  return DEFAULT_DATA_HEALTH.map((fallback) => ({ ...fallback, ...(byLabel.get(fallback.label) || {}) }));
}

export function dataHealthSummary(metrics: DataHealthMetric[]): {
  label: string;
  status: string;
  severity: StatusSeverity;
} {
  const nav = metrics.find((metric) => metric.label === 'MF NAV');
  if (nav && ['attention', 'unavailable'].includes(statusSeverity(nav.status))) {
    return { label: `MF NAV ${nav.status.toLowerCase()}`, status: nav.status, severity: statusSeverity(nav.status) };
  }

  const affected = metrics.find((metric) => metric.label !== 'MF NAV' && statusSeverity(metric.status) === 'unavailable')
    || metrics.find((metric) => metric.label !== 'MF NAV' && statusSeverity(metric.status) === 'attention')
    || metrics.find((metric) => metric.label !== 'MF NAV' && statusSeverity(metric.status) === 'in_progress');
  if (affected) {
    return {
      label: `${affected.label} ${affected.status.toLowerCase()}`,
      status: affected.status,
      severity: statusSeverity(affected.status),
    };
  }

  if (nav?.status) {
    return { label: 'Data healthy', status: nav.status, severity: statusSeverity(nav.status) };
  }
  return { label: 'Checking data', status: 'Checking', severity: 'in_progress' };
}

