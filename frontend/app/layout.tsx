import type { Metadata } from 'next';
import { SpeedInsights } from '@vercel/speed-insights/next';
import './globals.css';
import { Geist, Playfair_Display, IBM_Plex_Mono } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({ subsets: ['latin'], variable: '--font-sans' });
const playfair = Playfair_Display({ subsets: ['latin'], variable: '--font-playfair' });
const plexMono = IBM_Plex_Mono({ weight: ['400', '500', '600', '700'], subsets: ['latin'], variable: '--font-plex-mono' });

export const metadata: Metadata = {
  metadataBase: new URL('https://www.fundersai.co.in'),
  title: 'FundersAI | Indian Market Research Workspace',
  description: 'Compare Indian stocks and mutual funds with deterministic metrics, official-source evidence, freshness signals, and visible data limits.',
  keywords: [
    'Indian Mutual Funds',
    'Mutual Fund Comparison',
    'Screener',
    'Indian Stock Research',
    'Mutual Fund Comparison',
    'Official AMC Documents',
    'Research Evidence',
    'FundersAI',
    'Financial Research AI'
  ],
  authors: [{ name: 'FundersAI Team' }],
  openGraph: {
    title: 'FundersAI | Indian Market Research Workspace',
    description: 'Compare Indian stocks and mutual funds with deterministic metrics, official-source evidence, freshness signals, and visible data limits.',
    url: 'https://www.fundersai.co.in',
    siteName: 'FundersAI',
    locale: 'en_IN',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FundersAI | Indian Market Research Workspace',
    description: 'Compare Indian stocks and mutual funds with deterministic metrics, official-source evidence, freshness signals, and visible data limits.',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn("w-full min-w-full font-sans dark", geist.variable, playfair.variable, plexMono.variable)}>
      <body className="w-full min-w-full bg-background text-foreground antialiased selection:bg-primary/20 selection:text-primary-foreground">
        {children}
        <SpeedInsights />
      </body>
    </html>
  );
}
