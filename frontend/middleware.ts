import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || '';
  const { pathname, search } = request.nextUrl;

  // Case A: If user is on the synthesis subdomain (synthesis.fundersai.co.in or synthesis.localhost:3000)
  if (hostname.startsWith('synthesis.')) {
    // If accessing root of synthesis subdomain, rewrite to the Synthesis Landing Page (/synthesis)
    if (pathname === '/') {
      return NextResponse.rewrite(new URL('/synthesis', request.url));
    }

    // Case A1: the landing page is served at the bare subdomain root, but the underlying
    // route is /synthesis. The sitemap lists the root and the page canonicals to it, while
    // /synthesis returned 200 with the same canonical — a real duplicate URL. Collapse it
    // to the canonical root so only one URL exists for the landing page.
    if (pathname === '/synthesis' || pathname === '/synthesis/') {
      return NextResponse.redirect(new URL(`https://synthesis.fundersai.co.in/${search}`, request.url), 308);
    }

    // Case A2: the subdomain hosts the studio and nothing else. Without this, every www
    // page also renders at 200 here — the same content on two hostnames, which Google
    // either splits authority across or drops as a duplicate. Case B is the mirror of
    // this rule; the two together keep each product on exactly one host.
    // Auth and account routes are excluded: they are noindex and share a session with www.
    const isStudioPath = pathname.startsWith('/synthesis/');
    const isSharedAppPath =
      pathname.startsWith('/auth/') ||
      pathname === '/auth' ||
      pathname.startsWith('/api/') ||
      pathname.startsWith('/_next/');

    if (!isStudioPath && !isSharedAppPath) {
      return NextResponse.redirect(
        new URL(`https://www.fundersai.co.in${pathname}${search}`, request.url),
        308,
      );
    }

    return NextResponse.next();
  }

  // Case B: If user accesses /synthesis or any /synthesis/* subpath on the main domain
  // (www.fundersai.co.in or fundersai.co.in), send it to the subdomain. The whole product
  // must live on one hostname only, or Google sees the same page indexed twice.
  if (hostname.includes('fundersai.co.in') && (pathname === '/synthesis' || pathname.startsWith('/synthesis/'))) {
    // The landing page's canonical is the bare subdomain root, so jump straight there
    // instead of chaining through the subdomain /synthesis (which itself 308s to root).
    const destination = pathname === '/synthesis' || pathname === '/synthesis/'
      ? `https://synthesis.fundersai.co.in/${search}`
      : `https://synthesis.fundersai.co.in${pathname}${search}`;
    return NextResponse.redirect(new URL(destination, request.url), 308);
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
