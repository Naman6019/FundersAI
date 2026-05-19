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
  return clean || 'UNKNOWN';
}

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
    .select('scheme_code,amc_name,nav_date,aum,expense_ratio,alpha,beta,sharpe_ratio,benchmark')
    .limit(20000);
  const coreRows = coreRes.data || [];

  const holdingsRes = await supabase
    .from('mutual_fund_holdings')
    .select('scheme_code')
    .limit(50000);
  const holdingsRows = holdingsRes.data || [];
  const sectorRes = await supabase
    .from('mutual_fund_sectors')
    .select('scheme_code')
    .limit(50000);
  const sectorRows = sectorRes.data || [];

  const docsRes = await supabase
    .from('mf_raw_documents')
    .select('id,amc_code,source_document_type,source_url,parse_status,validation_issues,downloaded_at,parsed_at')
    .limit(30000);
  const docsRows = docsRes.data || [];

  const holdingsSet = new Set(holdingsRows.map((row) => String(row.scheme_code || '').trim()).filter(Boolean));
  const sectorSet = new Set(sectorRows.map((row) => String(row.scheme_code || '').trim()).filter(Boolean));
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
    stale_nav_count: number;
    missing_ter_count: number;
    parser_failed_docs: number;
    factsheet_files: number;
    portfolio_disclosure_files: number;
    latest_parser_at: string | null;
  };

  const map = new Map<string, Bucket>();
  for (const row of coreRows) {
    const amc = normalizeAmcCode(row.amc_name || '');
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
        stale_nav_count: 0,
        missing_ter_count: 0,
        parser_failed_docs: 0,
        factsheet_files: 0,
        portfolio_disclosure_files: 0,
        latest_parser_at: null,
      };

    const schemeCode = String(row.scheme_code || '').trim();
    bucket.total_funds += 1;
    if (row.nav_date) bucket.funds_with_nav += 1;
    if (row.nav_date && row.nav_date < staleCutoff) bucket.stale_nav_count += 1;
    if (row.aum !== null && row.aum !== undefined) bucket.funds_with_aum += 1;
    if (row.expense_ratio !== null && row.expense_ratio !== undefined) bucket.funds_with_ter += 1;
    if (row.expense_ratio === null || row.expense_ratio === undefined) bucket.missing_ter_count += 1;
    if (schemeCode && holdingsSet.has(schemeCode)) bucket.funds_with_holdings += 1;
    if (schemeCode && sectorSet.has(schemeCode)) bucket.funds_with_sector_allocation += 1;
    if (schemeCode && sectorSet.has(schemeCode)) bucket.funds_with_asset_allocation += 1; // TODO: add dedicated asset allocation table when available.
    if (row.alpha !== null || row.beta !== null || row.sharpe_ratio !== null) bucket.funds_with_ratios += 1;
    if (row.benchmark) bucket.funds_with_benchmark += 1;

    map.set(amc, bucket);
  }

  for (const doc of docsRows) {
    const amc = normalizeAmcCode(doc.amc_code || '');
    const bucket = map.get(amc);
    if (!bucket) continue;
    const docType = String(doc.source_document_type || '').toLowerCase();
    const parseStatus = String(doc.parse_status || '').toLowerCase();
    if (docType === 'factsheet') bucket.factsheet_files += 1;
    if (docType === 'portfolio_disclosure') bucket.portfolio_disclosure_files += 1;
    if (parseStatus === 'failed') bucket.parser_failed_docs += 1;
    const parserAt = String(doc.parsed_at || doc.downloaded_at || '');
    if (parserAt && (!bucket.latest_parser_at || parserAt > bucket.latest_parser_at)) {
      bucket.latest_parser_at = parserAt;
    }
  }

  const rows = Array.from(map.values()).map((bucket) => {
    const total = Math.max(bucket.total_funds, 1);
    const ratiosCoverage = bucket.funds_with_ratios / total;
    const holdingsCoverage = bucket.funds_with_holdings / total;
    const terCoverage = bucket.funds_with_ter / total;
    const navCoverage = bucket.funds_with_nav / total;
    const avgCoverage = (ratiosCoverage + holdingsCoverage + terCoverage + navCoverage) / 4;
    const coverage_percentage = Math.round(avgCoverage * 100);

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
    .filter((doc) => String(doc.parse_status || '').toLowerCase() === 'needs_review')
    .map((doc) => {
      const parsedAt = String(doc.parsed_at || '');
      const downloadedAt = String(doc.downloaded_at || '');
      return {
        id: String(doc.id || ''),
        amc: normalizeAmcCode(doc.amc_code || ''),
        source_document_type: String(doc.source_document_type || ''),
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
    pipeline_focus: {
      active_current: ['PPFAS', 'ICICI'],
      note: 'Current MVP pipeline is strongest on PPFAS and ICICI while broader AMC coverage is being expanded.',
    },
    todo_notes: [
      'TODO: dedicated asset allocation coverage needs a normalized table.',
    ],
  });
}
