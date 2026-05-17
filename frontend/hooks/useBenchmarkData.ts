'use client';

import { useState, useEffect } from 'react';

export interface BenchmarkPoint {
  date: string; // DD-MM-YYYY
  close: number;
}

let cachedData: BenchmarkPoint[] | null = null;
let pendingRequest: Promise<BenchmarkPoint[]> | null = null;

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
            const isoDate = typeof row?.date === 'string' ? row.date : '';
            if (!Number.isFinite(close) || !isoDate) continue;

            const parts = isoDate.split('-');
            if (parts.length !== 3) continue;
            const date = `${parts[2]}-${parts[1]}-${parts[0]}`;

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
