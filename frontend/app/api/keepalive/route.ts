import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

export async function GET(request: Request) {
  try {
    const limited = await enforceRateLimit(request, 'data-health');
    if (limited) return limited;

    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`, {
      headers: {
        'X-Forwarded-For': getClientIp(request),
      },
    })
    return Response.json({ ok: true })
  } catch (error) {
    return Response.json({ ok: false, error: String(error) }, { status: 500 })
  }
}
