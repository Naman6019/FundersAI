'use client';

import { createContext, ReactNode, useContext } from 'react';
import { useDataHealth } from '@/hooks/useDataHealth';

type DataHealthContextValue = ReturnType<typeof useDataHealth>;

const DataHealthContext = createContext<DataHealthContextValue | null>(null);

export function DataHealthProvider({ children }: { children: ReactNode }) {
  const value = useDataHealth();
  return <DataHealthContext.Provider value={value}>{children}</DataHealthContext.Provider>;
}

export function useDataHealthContext(): DataHealthContextValue {
  const value = useContext(DataHealthContext);
  if (!value) throw new Error('useDataHealthContext must be used inside DataHealthProvider.');
  return value;
}

