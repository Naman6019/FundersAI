import type { Metadata } from 'next';
import { SpeedInsights } from '@vercel/speed-insights/next';
import './globals.css';
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

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
  alternates: {
    canonical: '/',
  },
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
    <html lang="en" className={cn("w-full min-w-full", "font-sans", geist.variable)}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400..900;1,400..900&display=swap" rel="stylesheet" />
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
      </head>
      <body className="w-full min-w-full bg-[#050505] antialiased">
        {children}
        <SpeedInsights />
      </body>
    </html>
  );
}
