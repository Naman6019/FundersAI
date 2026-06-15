import { NextResponse } from 'next/server';
import { requireAdminFromRequest } from '@/lib/admin/server';

type CoverageFilter =
  | 'all'
  | 'fully-covered'
  | 'partial'
  | 'stale'
  | 'missing-ter'
  | 'missing-holdings'
  | 'missing-ratios'
  | 'parser-failing';

function normalizeFilter(value: string | null): CoverageFilter {
  const raw = String(value || 'all').toLowerCase();
  const allowed: CoverageFilter[] = [
    'all',
    'fully-covered',
    'partial',
    'stale',
    'missing-ter',
    'missing-holdings',
    'missing-ratios',
    'parser-failing',
  ];
  return allowed.includes(raw as CoverageFilter) ? (raw as CoverageFilter) : 'all';
}

function normalizeAmcCode(name: string): string {
  const clean = String(name || '').trim().toUpperCase();
  if (clean.includes('PARAG') || clean.includes('PPFAS')) return 'PPFAS';
  if (clean.includes('ICICI')) return 'ICICI';
  if (clean.includes('HDFC')) return 'HDFC';
  if (clean.includes('SBI')) return 'SBI';
  if (clean.includes('AXIS')) return 'AXIS';
  return clean || 'UNKNOWN';
}

function monthValue(value: unknown): string | null {
  const raw = String(value || '').trim();
  if (!raw) return null;
  if (/^\d{4}-\d{2}/.test(raw)) return raw.slice(0, 7);
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? null : date.toISOString().slice(0, 7);
}

function latestMonth(current: string | null, value: unknown): string | null {
  const month = monthValue(value);
  if (!month) return current;
  return !current || month > current ? month : current;
}

function normalizeSchemeName(name: string): string {
  return String(name || '')
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\b(direct|regular|growth|plan|option)\b/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function addCoverageName(map: Map<string, Set<string>>, amc: string, schemeName: string) {
  const normalizedAmc = normalizeAmcCode(amc);
  const normalizedName = normalizeSchemeName(schemeName);
  if (!normalizedName) return;
  const names = map.get(normalizedAmc) || new Set<string>();
  names.add(normalizedName);
  map.set(normalizedAmc, names);
}

function hasCoverageName(map: Map<string, Set<string>>, amc: string, schemeName: string): boolean {
  const normalizedName = normalizeSchemeName(schemeName);
  if (!normalizedName) return false;
  const names = map.get(normalizeAmcCode(amc));
  if (!names) return false;
  if (names.has(normalizedName)) return true;
  return Array.from(names).some((name) => name.includes(normalizedName) || normalizedName.includes(name));
}

const ACTION_WORKFLOW_ORDER = [
  {
    order: 1,
    label: 'Daily disclosure sync',
    schedule: '10:00 IST, Monday-Friday',
    action: 'Ingest latest AMC factsheet and portfolio documents.',
  },
  {
    order: 2,
    label: 'Pending parser pass',
    schedule: 'After daily sync',
    action: 'Parse pending and needs_reparse documents for PPFAS, ICICI, HDFC, SBI, Axis.',
  },
  {
    order: 3,
    label: 'Parser retry loop',
    schedule: 'Every 6 hours',
    action: 'Retry cooled-down needs_review and failed rows in order: Axis, SBI, HDFC, ICICI, PPFAS.',
  },
  {
    order: 4,
    label: 'Admin triage',
    schedule: 'As needed',
    action: 'Reparse real documents, skip irrelevant documents, and resolve only verified manual approvals.',
  },
];

export async function GET(request: Request) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  const supabase = auth.context.supabaseAdmin;
  if (!supabase) {
    return NextResponse.json({ error: 'Supabase service role key is missing' }, { status: 500 });
  }

  const { searchParams } = new URL(request.url);
  const filter = normalizeFilter(searchParams.get('filter'));

  const coreRes = await supabase
    .from('mutual_fund_core_snapshot')
    .select('scheme_code,scheme_name,amc_name,nav_date,aum,expense_ratio,alpha,beta,sharpe_ratio,benchmark,risk_level')
    .limit(20000);
  const coreRows = coreRes.data || [];

  const holdingsRes = await supabase
    .from('mutual_fund_holdings')
    .select('scheme_code,as_of_date')
    .limit(50000);
  const holdingsRows = holdingsRes.data || [];
  const sectorRes = await supabase
    .from('mutual_fund_sectors')
    .select('scheme_code')
    .limit(50000);
  const sectorRows = sectorRes.data || [];

  const nativeSchemesRes = await supabase
    .from('mf_schemes')
    .select('id,amc_code,scheme_name')
    .limit(50000);
  const nativeSchemes = nativeSchemesRes.data || [];
  const nativeSchemeById = new Map(
    nativeSchemes.map((row) => [
      String(row.id || ''),
      {
        amc: normalizeAmcCode(row.amc_code || ''),
        schemeName: String(row.scheme_name || ''),
      },
    ])
  );

  const nativeHoldingsRes = await supabase
    .from('mf_scheme_holdings')
    .select('scheme_id,sector,report_month')
    .limit(50000);
  const nativeHoldingsRows = nativeHoldingsRes.data || [];

  const docsRes = await supabase
    .from('mf_raw_documents')
    .select('id,amc_code,source_document_type,source_url,parse_status,validation_issues,report_month,downloaded_at,parsed_at')
    .limit(30000);
  const docsRows = docsRes.data || [];

  const reviewQueueRes = await supabase
    .from('mf_parse_review_queue')
    .select('amc_code,status,report_month')
    .limit(30000);
  const reviewQueueRows = reviewQueueRes.data || [];

  const holdingsSet = new Set(holdingsRows.map((row) => String(row.scheme_code || '').trim()).filter(Boolean));
  const sectorSet = new Set(sectorRows.map((row) => String(row.scheme_code || '').trim()).filter(Boolean));
  const nativeHoldingsByAmc = new Map<string, Set<string>>();
  const nativeSectorByAmc = new Map<string, Set<string>>();
  for (const row of nativeHoldingsRows) {
    const scheme = nativeSchemeById.get(String(row.scheme_id || ''));
    if (!scheme) continue;
    addCoverageName(nativeHoldingsByAmc, scheme.amc, scheme.schemeName);
    if (String(row.sector || '').trim()) addCoverageName(nativeSectorByAmc, scheme.amc, scheme.schemeName);
  }
  const staleCutoff = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

  type Bucket = {
    amc: string;
    total_funds: number;
    funds_with_nav: number;
    funds_with_aum: number;
    funds_with_ter: number;
    funds_with_holdings: number;
    funds_with_sector_allocation: number;
    funds_with_asset_allocation: number;
    funds_with_ratios: number;
    funds_with_benchmark: number;
    funds_with_risk_label: number;
    stale_nav_count: number;
    missing_ter_count: number;
    parser_failed_docs: number;
    skipped_docs: number;
    parse_review_count: number;
    factsheet_files: number;
    portfolio_disclosure_files: number;
    latest_factsheet_month: string | null;
    latest_holdings_month: string | null;
    latest_parser_at: string | null;
    ter_coverage: number;
    benchmark_coverage: number;
    risk_label_coverage: number;
    holdings_source_note: string | null;
  };

  const map = new Map<string, Bucket>();
  const schemeAmcByCode = new Map<string, string>();
  for (const row of coreRows) {
    const amc = normalizeAmcCode(row.amc_name || '');
    const schemeCode = String(row.scheme_code || '').trim();
    if (schemeCode) schemeAmcByCode.set(schemeCode, amc);
    const bucket =
      map.get(amc) ||
      {
        amc,
        total_funds: 0,
        funds_with_nav: 0,
        funds_with_aum: 0,
        funds_with_ter: 0,
        funds_with_holdings: 0,
        funds_with_sector_allocation: 0,
        funds_with_asset_allocation: 0,
        funds_with_ratios: 0,
        funds_with_benchmark: 0,
        funds_with_risk_label: 0,
        stale_nav_count: 0,
        missing_ter_count: 0,
        parser_failed_docs: 0,
        skipped_docs: 0,
        parse_review_count: 0,
        factsheet_files: 0,
        portfolio_disclosure_files: 0,
        latest_factsheet_month: null,
        latest_holdings_month: null,
        latest_parser_at: null,
        ter_coverage: 0,
        benchmark_coverage: 0,
        risk_label_coverage: 0,
        holdings_source_note: amc === 'AXIS' ? 'Axis holdings use AMC factsheet % of NAV rows, not ISIN-backed rows.' : null,
      };

    bucket.total_funds += 1;
    if (row.nav_date) bucket.funds_with_nav += 1;
    if (row.nav_date && row.nav_date < staleCutoff) bucket.stale_nav_count += 1;
    if (row.aum !== null && row.aum !== undefined) bucket.funds_with_aum += 1;
    if (row.expense_ratio !== null && row.expense_ratio !== undefined) bucket.funds_with_ter += 1;
    if (row.expense_ratio === null || row.expense_ratio === undefined) bucket.missing_ter_count += 1;
    if ((schemeCode && holdingsSet.has(schemeCode)) || hasCoverageName(nativeHoldingsByAmc, amc, row.scheme_name || '')) bucket.funds_with_holdings += 1;
    if ((schemeCode && sectorSet.has(schemeCode)) || hasCoverageName(nativeSectorByAmc, amc, row.scheme_name || '')) bucket.funds_with_sector_allocation += 1;
    if ((schemeCode && sectorSet.has(schemeCode)) || hasCoverageName(nativeSectorByAmc, amc, row.scheme_name || '')) bucket.funds_with_asset_allocation += 1; // TODO: add dedicated asset allocation table when available.
    if (row.alpha !== null || row.beta !== null || row.sharpe_ratio !== null) bucket.funds_with_ratios += 1;
    if (row.benchmark) bucket.funds_with_benchmark += 1;
    if (row.risk_level) bucket.funds_with_risk_label += 1;

    map.set(amc, bucket);
  }

  for (const row of holdingsRows) {
    const amc = schemeAmcByCode.get(String(row.scheme_code || '').trim());
    if (!amc) continue;
    const bucket = map.get(amc);
    if (!bucket) continue;
    bucket.latest_holdings_month = latestMonth(bucket.latest_holdings_month, row.as_of_date);
  }

  for (const row of nativeHoldingsRows) {
    const scheme = nativeSchemeById.get(String(row.scheme_id || ''));
    if (!scheme) continue;
    const bucket = map.get(scheme.amc);
    if (!bucket) continue;
    bucket.latest_holdings_month = latestMonth(bucket.latest_holdings_month, row.report_month);
  }

  for (const doc of docsRows) {
    const amc = normalizeAmcCode(doc.amc_code || '');
    const bucket = map.get(amc);
    if (!bucket) continue;
    const docType = String(doc.source_document_type || '').toLowerCase();
    const parseStatus = String(doc.parse_status || '').toLowerCase();
    if (docType === 'factsheet') {
      bucket.factsheet_files += 1;
      if (parseStatus === 'parsed') bucket.latest_factsheet_month = latestMonth(bucket.latest_factsheet_month, doc.report_month || doc.parsed_at || doc.downloaded_at);
    }
    if (docType === 'portfolio_disclosure') {
      bucket.portfolio_disclosure_files += 1;
      if (parseStatus === 'parsed') bucket.latest_holdings_month = latestMonth(bucket.latest_holdings_month, doc.report_month || doc.parsed_at || doc.downloaded_at);
    }
    if (docType === 'factsheet' && parseStatus === 'parsed' && amc === 'AXIS') {
      bucket.latest_holdings_month = latestMonth(bucket.latest_holdings_month, doc.report_month || doc.parsed_at || doc.downloaded_at);
    }
    if (parseStatus === 'failed') bucket.parser_failed_docs += 1;
    if (parseStatus.startsWith('skipped')) bucket.skipped_docs += 1;
    const parserAt = String(doc.parsed_at || doc.downloaded_at || '');
    if (parserAt && (!bucket.latest_parser_at || parserAt > bucket.latest_parser_at)) {
      bucket.latest_parser_at = parserAt;
    }
  }

  for (const row of reviewQueueRows) {
    const amc = normalizeAmcCode(row.amc_code || '');
    const bucket = map.get(amc);
    if (!bucket) continue;
    const status = String(row.status || '').toLowerCase();
    if (!status || status === 'pending_review' || status === 'needs_review' || status === 'failed') bucket.parse_review_count += 1;
  }

  const rows = Array.from(map.values()).map((bucket) => {
    const total = Math.max(bucket.total_funds, 1);
    const ratiosCoverage = bucket.funds_with_ratios / total;
    const holdingsCoverage = bucket.funds_with_holdings / total;
    const terCoverage = bucket.funds_with_ter / total;
    const navCoverage = bucket.funds_with_nav / total;
    const avgCoverage = (ratiosCoverage + holdingsCoverage + terCoverage + navCoverage) / 4;
    const coverage_percentage = Math.round(avgCoverage * 100);
    const ter_coverage = Math.round(terCoverage * 100);
    const benchmark_coverage = Math.round((bucket.funds_with_benchmark / total) * 100);
    const risk_label_coverage = Math.round((bucket.funds_with_risk_label / total) * 100);

    let parser_status = 'Active';
    if (bucket.parser_failed_docs > 0) parser_status = 'Failing';
    else if (!bucket.latest_parser_at) parser_status = 'Planned';

    let freshness_status = 'Fresh';
    if (bucket.stale_nav_count > 0) freshness_status = 'Stale';
    if (bucket.funds_with_nav === 0) freshness_status = 'Planned';

    let status = 'Partial';
    if (bucket.total_funds === 0) status = 'Planned';
    else if (bucket.parser_failed_docs > 0) status = 'Failing';
    else if (coverage_percentage >= 85 && freshness_status === 'Fresh') status = 'Active';
    else if (freshness_status === 'Stale') status = 'Stale';

    return {
      ...bucket,
      parser_status,
      freshness_status,
      coverage_percentage,
      ter_coverage,
      benchmark_coverage,
      risk_label_coverage,
      status,
    };
  });

  const filtered = rows.filter((row) => {
    if (filter === 'all') return true;
    if (filter === 'fully-covered') return row.coverage_percentage >= 85;
    if (filter === 'partial') return row.coverage_percentage < 85 && row.status !== 'Failing';
    if (filter === 'stale') return row.freshness_status === 'Stale';
    if (filter === 'missing-ter') return row.missing_ter_count > 0;
    if (filter === 'missing-holdings') return row.funds_with_holdings < row.total_funds;
    if (filter === 'missing-ratios') return row.funds_with_ratios < row.total_funds;
    if (filter === 'parser-failing') return row.parser_status === 'Failing';
    return true;
  });

  const needsReviewEntries = docsRows
    .filter((doc) => ['needs_review', 'failed'].includes(String(doc.parse_status || '').toLowerCase()))
    .map((doc) => {
      const parsedAt = String(doc.parsed_at || '');
      const downloadedAt = String(doc.downloaded_at || '');
      return {
        id: String(doc.id || ''),
        amc: normalizeAmcCode(doc.amc_code || ''),
        source_document_type: String(doc.source_document_type || ''),
        parse_status: String(doc.parse_status || ''),
        source_url: String(doc.source_url || ''),
        validation_issues: Array.isArray(doc.validation_issues) ? doc.validation_issues : [],
        parsed_at: parsedAt || null,
        downloaded_at: downloadedAt || null,
        latest_at: parsedAt || downloadedAt || null,
      };
    })
    .sort((a, b) => String(b.latest_at || '').localeCompare(String(a.latest_at || '')))
    .slice(0, 200);

  return NextResponse.json({
    status: 'ok',
    checked_at: new Date().toISOString(),
    filter,
    rows: filtered.sort((a, b) => a.amc.localeCompare(b.amc)),
    needs_review_entries: needsReviewEntries,
    action_workflow_order: ACTION_WORKFLOW_ORDER,
    pipeline_focus: {
      active_current: ['PPFAS', 'ICICI', 'HDFC', 'SBI', 'AXIS'],
      note: 'Current parser pipeline is active for PPFAS, ICICI, HDFC, SBI, and Axis. Axis holdings are % of NAV factsheet rows, not ISIN-backed rows.',
    },
    todo_notes: [
      'TODO: dedicated asset allocation coverage needs a normalized table.',
    ],
  });
}
