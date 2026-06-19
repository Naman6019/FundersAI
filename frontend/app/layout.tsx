import type { Metadata } from 'next';
import { SpeedInsights } from '@vercel/speed-insights/next';
import './globals.css';
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: 'FundersAI | Mutual Fund Comparison & Screening Workspace',
  description: 'Compare Parag Parikh Flexi Cap vs ICICI Prudential Multi Asset and other mutual funds. Analyze Sharpe ratio, expense ratios (TER), alpha, and beta with AI-powered explanations.',
  keywords: [
    'Indian Mutual Funds',
    'Mutual Fund Comparison',
    'Screener',
    'Parag Parikh Flexi Cap',
    'ICICI Prudential Multi Asset',
    'Sharpe Ratio Calculator',
    'Expense Ratio Comparison',
    'FundersAI',
    'Financial Research AI'
  ],
  authors: [{ name: 'FundersAI Team' }],
  openGraph: {
    title: 'FundersAI | Mutual Fund Comparison & Screening Workspace',
    description: 'Compare Parag Parikh Flexi Cap vs ICICI Prudential Multi Asset and other mutual funds. Analyze Sharpe ratio, expense ratios (TER), alpha, and beta with AI-powered explanations.',
    url: 'https://fundersai.com',
    siteName: 'FundersAI',
    locale: 'en_IN',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FundersAI | Mutual Fund Comparison Workspace',
    description: 'Compare Parag Parikh Flexi Cap vs ICICI Prudential Multi Asset and other mutual funds. Analyze Sharpe ratio, expense ratios (TER), alpha, and beta with AI-powered explanations.',
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
