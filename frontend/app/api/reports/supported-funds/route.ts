import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';
import { getFundsGroupedByAmc } from '@/lib/fund-registry';

/**
 * Offline fallback for the supported-funds directory.
 *
 * Identity only. Every scheme code and name is resolved from FUND_REGISTRY,
 * which is pinned to AMFI's scheme master by tests/amfiSchemeIdentity.test.mjs.
 * This route deliberately ships NO return_3y / nav / expense_ratio values in the
 * fallback: those are point-in-time figures that only the live snapshot can
 * supply, and inventing plausible ones would present fabricated numbers as
 * fund data. Callers get `source: 'registry-fallback'` plus a notice and are
 * expected to disclose that performance figures are unavailable.
 */
const FALLBACK_NOTICE =
  'Live fund data is unavailable, so this list falls back to our verified AMFI ' +
  'scheme registry. Scheme codes and names are accurate; NAV, 3-year returns and ' +
  'expense ratios are not shown because we do not have current values for them.';

function buildRegistryFallback() {
  return getFundsGroupedByAmc().map(({ amcName, funds }) => ({
    amc_name: amcName,
    schemes: funds.map((fund) => ({
      scheme_code: fund.schemeCode,
      scheme_name: fund.schemeName,
      former_scheme_name: fund.formerName ?? null,
      category: fund.category,
      // No return_3y / nav / expense_ratio: unknown offline, and we disclose
      // missing data rather than substituting plausible-looking values.
    })),
  }));
}

export async function GET() {
  try {
    const { data: dbData, error } = await supabase
      .from('mutual_fund_core_snapshot')
      .select('scheme_code, scheme_name, amc_name, category, return_3y, nav, expense_ratio')
      .limit(1000);

    if (error || !dbData || dbData.length === 0) {
      console.warn(
        'Falling back to the AMFI scheme registry because the Supabase query returned empty/error:',
        error?.message,
      );
      return NextResponse.json({
        amcGroups: buildRegistryFallback(),
        source: 'registry-fallback',
        metricsAvailable: false,
        notice: FALLBACK_NOTICE,
      });
    }

    // Group DB data by AMC
    type SchemeRow = (typeof dbData)[number];
    const groupsMap: Record<string, SchemeRow[]> = {};
    dbData.forEach((row) => {
      const amc = row.amc_name?.trim() || 'Other Mutual Funds';
      if (!groupsMap[amc]) groupsMap[amc] = [];
      groupsMap[amc].push(row);
    });

    const amcGroups = Object.entries(groupsMap)
      .map(([amc_name, schemes]) => ({ amc_name, schemes }))
      .sort((a, b) => b.schemes.length - a.schemes.length);

    return NextResponse.json({ amcGroups, source: 'supabase', metricsAvailable: true });
  } catch (err) {
    console.error('API error in supported-funds route:', err);
    return NextResponse.json({
      amcGroups: buildRegistryFallback(),
      source: 'registry-fallback',
      metricsAvailable: false,
      notice: FALLBACK_NOTICE,
    });
  }
}
