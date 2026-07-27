'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  DataHealthPayload,
  DEFAULT_DATA_HEALTH,
  mergeDataHealthMetrics,
} from '@/lib/dataHealth';

const DEFAULT_PAYLOAD: DataHealthPayload = {
  status: 'checking',
  source: 'pending',
  checked_at: null,
  metrics: DEFAULT_DATA_HEALTH,
  pipeline: {},
  amc_parser_quality: [],
};

export function useDataHealth(pollIntervalMs = 60_000) {
  const [data, setData] = useState<DataHealthPayload>(DEFAULT_PAYLOAD);
  const [lastSuccessfulCheck, setLastSuccessfulCheck] = useState<string | null>(null);
  const [lastAttemptedCheck, setLastAttemptedCheck] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setIsRefreshing(true);
    setError(null);
    setLastAttemptedCheck(new Date().toISOString());

    try {
      const response = await fetch('/api/data-health', {
        cache: 'no-store',
        signal: controller.signal,
      });
      if (!response.ok) throw new Error('Data status could not be refreshed.');
      const payload = await response.json() as Partial<DataHealthPayload>;
      const next: DataHealthPayload = {
        status: String(payload.status || 'degraded'),
        source: typeof payload.source === 'string' ? payload.source : undefined,
        checked_at: typeof payload.checked_at === 'string' ? payload.checked_at : new Date().toISOString(),
        metrics: mergeDataHealthMetrics(payload.metrics),
        pipeline: payload.pipeline && typeof payload.pipeline === 'object' ? payload.pipeline : {},
        amc_parser_quality: Array.isArray(payload.amc_parser_quality) ? payload.amc_parser_quality : [],
      };
      setData(next);
      setLastSuccessfulCheck(next.checked_at || new Date().toISOString());
    } catch (refreshError) {
      if (refreshError instanceof DOMException && refreshError.name === 'AbortError') return;
      setError(refreshError instanceof Error ? refreshError.message : 'Data status could not be refreshed.');
    } finally {
      if (!controller.signal.aborted) setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;
    const initialRefreshTimer = setTimeout(() => void refresh(), 0);

    const stopTimer = () => {
      if (timer) clearInterval(timer);
      timer = null;
    };
    const startTimer = () => {
      stopTimer();
      if (document.visibilityState !== 'visible') return;
      timer = setInterval(() => void refresh(), pollIntervalMs);
    };
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        void refresh();
        startTimer();
      } else {
        stopTimer();
      }
    };

    startTimer();
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      clearTimeout(initialRefreshTimer);
      stopTimer();
      abortRef.current?.abort();
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [pollIntervalMs, refresh]);

  return {
    data,
    error,
    isRefreshing,
    lastAttemptedCheck,
    lastSuccessfulCheck,
    refresh,
  };
}
