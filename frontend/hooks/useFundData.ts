import { useState, useEffect } from 'react';
import { FundDataResponse, MFChartPoint, MFDetailApiResponse } from '../types/funds';

const globalCache = new Map<string, FundDataResponse>();
const pendingRequests = new Map<string, Promise<FundDataResponse>>();

function isValidMFPayload(payload: unknown): payload is MFDetailApiResponse {
  if (!payload || typeof payload !== 'object') return false;
  const candidate = payload as MFDetailApiResponse;
  return Boolean(candidate.details) && Array.isArray(candidate.chartData);
}

export function useFundData(schemeCode: string | null) {
  const [data, setData] = useState<FundDataResponse | null>(schemeCode ? (globalCache.get(schemeCode) || null) : null);
  const [loading, setLoading] = useState<boolean>(schemeCode ? !globalCache.has(schemeCode) : false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!schemeCode) return;
    let isMounted = true;

    if (globalCache.has(schemeCode)) {
      const cached = globalCache.get(schemeCode)!;
      Promise.resolve().then(() => {
        if (!isMounted) return;
        setData(cached);
        setLoading(false);
        setError(null);
      });
      return () => {
        isMounted = false;
      };
    }

    Promise.resolve().then(() => {
      if (!isMounted) return;
      setData(null);
      setLoading(true);
      setError(null);
    });

    if (!pendingRequests.has(schemeCode)) {
      const p = fetch(`/api/mf/${schemeCode}`)
        .then(async res => {
          if (!res.ok) {
            const body = await res.text();
            let message = body || `Failed to fetch data for ${schemeCode}`;
            try {
              const parsed = JSON.parse(body);
              message = parsed?.detail || parsed?.error || message;
            } catch {}
            throw new Error(message);
          }
          return res.json();
        })
        .then((json: unknown) => {
          if (!isValidMFPayload(json)) {
            throw new Error(`Failed to fetch data for ${schemeCode}`);
          }

          // Map local API response to existing FundDataResponse type
          const rawHistory: MFChartPoint[] = (json.fullData || json.chartData || []) as MFChartPoint[];
          const formatted: FundDataResponse = {
            meta: {
              fund_house: String(json.details.fund_house || ''),
              scheme_type: String(json.details.category || ''),
              scheme_category: String(json.details.sub_category || ''),
              scheme_code: json.details.scheme_code ?? '',
              scheme_name: String(json.details.scheme_name || '')
            },
            data: rawHistory.map((d) => ({
              date: d.date,
              nav: d.value.toString()
            })),
            status: 'ok',
            details: json.details,
            returns: json.returns,
            riskMetrics: json.riskMetrics,
            coverage: json.historyCoverage,
            freshness: json.freshness
          };
          globalCache.set(schemeCode, formatted);
          return formatted;
        })
        .finally(() => {
          pendingRequests.delete(schemeCode);
        });
      pendingRequests.set(schemeCode, p);
    }

    pendingRequests.get(schemeCode)!
      .then(json => {
        if (isMounted) {
          setData(json);
          setLoading(false);
        }
      })
      .catch(err => {
        if (isMounted) {
          setError(err?.message || `Failed to fetch data for ${schemeCode}`);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [schemeCode]);

  return { 
    navData: data?.data || null, 
    meta: data?.meta || null, 
    details: data?.details || null,
    returns: data?.returns || null,
    riskMetrics: data?.riskMetrics || null,
    coverage: data?.coverage || null,
    freshness: data?.freshness || null,
    loading, 
    error 
  };
}
