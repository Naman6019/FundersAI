import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const targetBase = process.env.NODE_ENV === 'development'
      ? 'http://127.0.0.1:8000'
      : process.env.NEXT_PUBLIC_API_URL;
    const proxyRes = await fetch(`${targetBase}/api/funds/research/evaluation`, { cache: 'no-store' });
    return new NextResponse(await proxyRes.text(), {
      status: proxyRes.status,
      headers: { 'Content-Type': proxyRes.headers.get('content-type') || 'application/json' },
    });
  } catch (error) {
    console.error('Fund research evaluation proxy error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
