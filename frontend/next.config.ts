import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async redirects() {
    // Synthesis Studio moved from /reports/* to /synthesis/* so the whole product
    // (marketing splash + tool) lives under one consistent URL namespace.
    return [
      // Retired design prototype (`app/emergent-replica`), deleted in 18a3d4a2 with no
      // successor. Search Console still reports impressions for the URL while it 404s, so a
      // permanent redirect retires it and passes any residual signals to the homepage.
      { source: '/emergent-replica', destination: '/', permanent: true },
      { source: '/reports', destination: '/synthesis', permanent: true },
      { source: '/reports/generate', destination: '/synthesis/generate', permanent: true },
      { source: '/reports/dashboard', destination: '/synthesis/dashboard', permanent: true },
      { source: '/reports/methodology', destination: '/synthesis/methodology', permanent: true },
      { source: '/reports/supported-funds', destination: '/synthesis/supported-funds', permanent: true },
      { source: '/reports/tools/portfolio-overlap', destination: '/tools/portfolio-overlap', permanent: true },
      { source: '/synthesis/tools/portfolio-overlap', destination: '/tools/portfolio-overlap', permanent: true },
      { source: '/reports/vs/:slug', destination: '/synthesis/vs/:slug', permanent: true },
      { source: '/reports/category/:slug', destination: '/synthesis/category/:slug', permanent: true },
    ];
  },
  async headers() {
    return [{
      source: '/:path*',
      headers: [
        { key: 'Content-Security-Policy', value: "frame-ancestors 'none'; base-uri 'self'; object-src 'none'" },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'DENY' },
      ],
    }];
  },
};

export default nextConfig;
