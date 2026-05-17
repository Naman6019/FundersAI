import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Mooliq | AI-Orchestrated Financial Research',
  description: 'Mooliq fuses real-time quantitative metrics with AI-driven news sentiment to provide institutional-grade insights for the Indian markets.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="w-full min-w-full overflow-x-hidden">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet" />
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
      </head>
      <body className="w-full min-w-full overflow-x-hidden bg-[#05070f] antialiased">
        {children}
      </body>
    </html>
  );
}
