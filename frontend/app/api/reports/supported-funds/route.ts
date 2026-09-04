import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

const FALLBACK_FUNDS_BY_AMC = [
  {
    amc_name: "PPFAS Mutual Fund (Parag Parikh)",
    schemes: [
      { scheme_code: 119551, scheme_name: "Parag Parikh Flexi Cap Fund", category: "Flexi Cap", return_3y: 18.4, nav: 93.36, expense_ratio: 0.55 },
      { scheme_code: 148974, scheme_name: "Parag Parikh Tax Saver Fund", category: "ELSS Tax Saver", return_3y: 17.2, nav: 28.45, expense_ratio: 0.65 },
      { scheme_code: 143241, scheme_name: "Parag Parikh Liquid Fund", category: "Liquid Debt", return_3y: 6.8, nav: 1245.10, expense_ratio: 0.16 },
      { scheme_code: 149112, scheme_name: "Parag Parikh Dynamic Asset Allocation Fund", category: "Hybrid", return_3y: 11.5, nav: 12.40, expense_ratio: 0.40 }
    ]
  },
  {
    amc_name: "HDFC Mutual Fund",
    schemes: [
      { scheme_code: 122639, scheme_name: "HDFC Flexi Cap Fund", category: "Flexi Cap", return_3y: 21.2, nav: 1745.20, expense_ratio: 0.82 },
      { scheme_code: 100122, scheme_name: "HDFC Top 100 Fund", category: "Large Cap", return_3y: 16.8, nav: 1045.50, expense_ratio: 1.05 },
      { scheme_code: 105754, scheme_name: "HDFC Mid-Cap Opportunities Fund", category: "Mid Cap", return_3y: 24.5, nav: 185.40, expense_ratio: 0.78 },
      { scheme_code: 118989, scheme_name: "HDFC Small Cap Fund", category: "Small Cap", return_3y: 26.1, nav: 142.10, expense_ratio: 0.68 },
      { scheme_code: 100120, scheme_name: "HDFC Balanced Advantage Fund", category: "Hybrid", return_3y: 19.4, nav: 425.60, expense_ratio: 0.75 },
      { scheme_code: 100128, scheme_name: "HDFC Large and Mid Cap Fund", category: "Large & Mid Cap", return_3y: 20.8, nav: 310.20, expense_ratio: 0.88 }
    ]
  },
  {
    amc_name: "Quant Mutual Fund",
    schemes: [
      { scheme_code: 120828, scheme_name: "Quant Small Cap Fund", category: "Small Cap", return_3y: 32.4, nav: 245.80, expense_ratio: 0.64 },
      { scheme_code: 120823, scheme_name: "Quant Active Fund", category: "Multi Cap", return_3y: 22.8, nav: 612.40, expense_ratio: 0.58 },
      { scheme_code: 120825, scheme_name: "Quant Flexi Cap Fund", category: "Flexi Cap", return_3y: 25.6, nav: 104.20, expense_ratio: 0.59 },
      { scheme_code: 120827, scheme_name: "Quant Mid Cap Fund", category: "Mid Cap", return_3y: 29.8, nav: 214.60, expense_ratio: 0.62 },
      { scheme_code: 120822, scheme_name: "Quant Infrastructure Fund", category: "Sectoral", return_3y: 34.5, nav: 42.80, expense_ratio: 0.72 }
    ]
  },
  {
    amc_name: "Nippon India Mutual Fund",
    schemes: [
      { scheme_code: 113177, scheme_name: "Nippon India Small Cap Fund", category: "Small Cap", return_3y: 28.7, nav: 184.20, expense_ratio: 0.69 },
      { scheme_code: 100378, scheme_name: "Nippon India Growth Fund", category: "Mid Cap", return_3y: 23.1, nav: 3410.50, expense_ratio: 0.85 },
      { scheme_code: 100374, scheme_name: "Nippon India Large Cap Fund", category: "Large Cap", return_3y: 19.8, nav: 84.10, expense_ratio: 0.79 },
      { scheme_code: 100382, scheme_name: "Nippon India Multi Cap Fund", category: "Multi Cap", return_3y: 24.2, nav: 245.90, expense_ratio: 0.88 }
    ]
  },
  {
    amc_name: "SBI Mutual Fund",
    schemes: [
      { scheme_code: 125497, scheme_name: "SBI Small Cap Fund", category: "Small Cap", return_3y: 22.4, nav: 168.40, expense_ratio: 0.71 },
      { scheme_code: 100412, scheme_name: "SBI Bluechip Fund", category: "Large Cap", return_3y: 14.9, nav: 94.50, expense_ratio: 0.84 },
      { scheme_code: 100416, scheme_name: "SBI Magnum Midcap Fund", category: "Mid Cap", return_3y: 23.8, nav: 210.40, expense_ratio: 0.92 },
      { scheme_code: 119598, scheme_name: "SBI Focused Equity Fund", category: "Focused", return_3y: 16.4, nav: 312.10, expense_ratio: 0.78 }
    ]
  },
  {
    amc_name: "ICICI Prudential Mutual Fund",
    schemes: [
      { scheme_code: 100356, scheme_name: "ICICI Prudential Bluechip Fund", category: "Large Cap", return_3y: 17.5, nav: 108.40, expense_ratio: 0.91 },
      { scheme_code: 120586, scheme_name: "ICICI Prudential Value Discovery Fund", category: "Value", return_3y: 24.2, nav: 384.60, expense_ratio: 0.72 },
      { scheme_code: 100360, scheme_name: "ICICI Prudential Large & Mid Cap Fund", category: "Large & Mid Cap", return_3y: 21.4, nav: 742.10, expense_ratio: 0.86 },
      { scheme_code: 105756, scheme_name: "ICICI Prudential Smallcap Fund", category: "Small Cap", return_3y: 25.1, nav: 84.90, expense_ratio: 0.75 }
    ]
  },
  {
    amc_name: "Kotak Mutual Fund",
    schemes: [
      { scheme_code: 105758, scheme_name: "Kotak Emerging Equity Fund", category: "Mid Cap", return_3y: 21.8, nav: 124.50, expense_ratio: 0.65 },
      { scheme_code: 100424, scheme_name: "Kotak Flexi Cap Fund", category: "Flexi Cap", return_3y: 16.4, nav: 74.20, expense_ratio: 0.68 },
      { scheme_code: 102657, scheme_name: "Kotak Small Cap Fund", category: "Small Cap", return_3y: 22.9, nav: 245.10, expense_ratio: 0.62 },
      { scheme_code: 100420, scheme_name: "Kotak Bluechip Fund", category: "Large Cap", return_3y: 15.8, nav: 512.40, expense_ratio: 0.81 }
    ]
  },
  {
    amc_name: "Axis Mutual Fund",
    schemes: [
      { scheme_code: 112323, scheme_name: "Axis Long Term Equity Fund", category: "ELSS Tax Saver", return_3y: 12.8, nav: 84.10, expense_ratio: 0.73 },
      { scheme_code: 107223, scheme_name: "Axis Small Cap Fund", category: "Small Cap", return_3y: 20.5, nav: 104.50, expense_ratio: 0.54 },
      { scheme_code: 107576, scheme_name: "Axis Midcap Fund", category: "Mid Cap", return_3y: 18.2, nav: 98.40, expense_ratio: 0.52 },
      { scheme_code: 100432, scheme_name: "Axis Bluechip Fund", category: "Large Cap", return_3y: 11.4, nav: 54.20, expense_ratio: 0.65 }
    ]
  }
];

export async function GET() {
  try {
    const { data: dbData, error } = await supabase
      .from('mutual_fund_core_snapshot')
      .select('scheme_code, scheme_name, amc_name, category, return_3y, nav, expense_ratio')
      .limit(1000);

    if (error || !dbData || dbData.length === 0) {
      console.warn("Using fallback AMC schemes because Supabase query returned empty/error:", error?.message);
      return NextResponse.json({ amcGroups: FALLBACK_FUNDS_BY_AMC, source: 'fallback' });
    }

    // Group DB data by AMC
    type SchemeRow = (typeof dbData)[number];
    const groupsMap: Record<string, SchemeRow[]> = {};
    dbData.forEach(row => {
      const amc = row.amc_name?.trim() || "Other Mutual Funds";
      if (!groupsMap[amc]) groupsMap[amc] = [];
      groupsMap[amc].push(row);
    });

    const amcGroups = Object.entries(groupsMap)
      .map(([amc_name, schemes]) => ({ amc_name, schemes }))
      .sort((a, b) => b.schemes.length - a.schemes.length);

    return NextResponse.json({ amcGroups, source: 'supabase' });
  } catch (err: unknown) {
    console.error("API error in supported-funds route:", err);
    return NextResponse.json({ amcGroups: FALLBACK_FUNDS_BY_AMC, source: 'fallback' });
  }
}
