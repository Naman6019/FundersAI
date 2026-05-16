import PremiumLandingPage from '@/components/landing/PremiumLandingPage';

export const revalidate = 60;

type TickerItem = {
  symbol: string;
  name: string;
  price: number | null;
  change_pct: number | null;
  date: string | null;
};

const tickerUrl = () => {
  const base =
    process.env.NODE_ENV === 'development'
      ? 'http://127.0.0.1:8000'
      : process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL;

  return base ? `${base}/api/quant/stocks/nifty50/ticker` : null;
};

const getTickerItems = async (): Promise<TickerItem[]> => {
  const url = tickerUrl();
  if (!url) return [];

  try {
    const response = await fetch(url, {
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(6000),
    });
    if (!response.ok) return [];
    const data = await response.json();
    return Array.isArray(data.items) ? data.items : [];
  } catch {
    return [];
  }
};

export default async function LandingPage() {
  const tickerItems = await getTickerItems();
  return <PremiumLandingPage tickerItems={tickerItems} />;
}

