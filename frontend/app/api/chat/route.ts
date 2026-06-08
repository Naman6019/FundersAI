import { NextResponse } from 'next/server';
import { getUserContext } from '@/lib/auth/server';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

function trimForHistory(value: unknown): string {
  return String(value || '').slice(0, 20000);
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const userContext = await getUserContext(req);
    const limited = await enforceRateLimit(req, 'chat', userContext ? {
      identifier: userContext.user.id,
      tier: userContext.profile.tier,
      role: userContext.profile.role,
    } : {});
    if (limited) return limited;

    const TARGET = process.env.NODE_ENV === 'development'
      ? 'http://127.0.0.1:8000/api/chat'
      : `${process.env.NEXT_PUBLIC_API_URL}/api/chat`;
    
    console.log(`Proxying chat request to: ${TARGET}`);

    const proxyRes = await fetch(TARGET, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': getClientIp(req),
      },
      body: JSON.stringify(body),
    });

    if (!proxyRes.ok) {
        const errorText = await proxyRes.text();
        console.error(`Upstream Error (${proxyRes.status}):`, errorText);
        return NextResponse.json({ error: 'Upstream Error' }, { status: proxyRes.status });
    }
    
    const data = await proxyRes.json();
    if (userContext) {
      const nowMs = Date.now();
      const rows = [
        {
          user_id: userContext.user.id,
          role: 'user',
          content: trimForHistory(body.query),
          created_at: new Date(nowMs).toISOString(),
          metadata: {
            asset_type: body.asset_type || null,
            research_depth: body.research_depth || null,
            comparison_view_mode: body.comparison_view_mode || null,
          },
        },
        {
          user_id: userContext.user.id,
          role: 'system',
          content: trimForHistory(data.answer),
          created_at: new Date(nowMs + 1).toISOString(),
          metadata: {
            system_action: data.system_action || null,
            has_quant_data: Boolean(data.quant_data),
          },
        },
      ].filter((row) => row.content.trim().length > 0);

      if (rows.length > 0) {
        const { error } = await userContext.supabaseAdmin.from('chat_messages').insert(rows);
        if (error) console.error('Chat history write failed:', error);
      }
    }

    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Chat Proxy Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
