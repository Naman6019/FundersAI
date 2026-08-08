import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || '';
  const { pathname } = request.nextUrl;

  // Case A: If user is on the synthesis subdomain (synthesis.fundersai.co.in or synthesis.localhost:3000)
  if (hostname.startsWith('synthesis.')) {
    // If accessing root of synthesis subdomain, rewrite to the Synthesis Landing Page (/reports)
    if (pathname === '/') {
      return NextResponse.rewrite(new URL('/reports', request.url));
    }
    return NextResponse.next();
  }

  // Case B: If user accesses /synthesis on the main domain (www.fundersai.co.in or fundersai.co.in)
  if (hostname.includes('fundersai.co.in') && pathname === '/synthesis') {
    return NextResponse.redirect(new URL('https://synthesis.fundersai.co.in', request.url), 308);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)',
  ],
};
