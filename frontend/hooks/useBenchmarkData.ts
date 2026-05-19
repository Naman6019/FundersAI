'use client';

import { useState, useEffect } from 'react';

export interface BenchmarkPoint {
  date: string; // DD-MM-YYYY
  close: number;
}

let cachedData: BenchmarkPoint[] | null = null;
let pendingRequest: Promise<BenchmarkPoint[]> | null = null;

function normalizeToDdMmYyyy(raw: string): string | null {
  if (!raw) return null;
  if (/^\d{2}-\d{2}-\d{4}$/.test(raw)) return raw;
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    const [year, month, day] = raw.split('-');
    return `${day}-${month}-${year}`;
  }
  return null;
}

export function useBenchmarkData() {
  const [data, setData] = useState<BenchmarkPoint[] | null>(cachedData);
  const [loading, setLoading] = useState<boolean>(!cachedData);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cachedData) return;

    if (!pendingRequest) {
      pendingRequest = fetch('/api/quant/stocks/NIFTY/price-history?days=2200')
        .then(res => {
          if (!res.ok) throw new Error('Failed to fetch benchmark data');
          return res.json();
        })
        .then(json => {
          const rows = Array.isArray(json?.price_history) ? json.price_history : [];
          const points: BenchmarkPoint[] = [];

          for (const row of rows) {
            const close = Number(row?.close);
            const rawDate = typeof row?.date === 'string' ? row.date : '';
            const date = normalizeToDdMmYyyy(rawDate);
            if (!Number.isFinite(close) || !date) continue;

            points.push({
              date,
              close
            });
          }

          cachedData = points;
          return points;
        });
    }

    pendingRequest
      .then(points => {
        setData(points);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
        pendingRequest = null; // Reset on failure
      });
  }, []);

  return { data, loading, error };
}
