import { NextResponse } from 'next/server';
import { randomUUID } from 'crypto';
import { getUserContext } from '@/lib/auth/server';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';
import {
  estimateChatTokens,
  finalizeAiUsage,
  reserveAiTokens,
  tokenLimitsEnabled,
  type TokenReservation,
  type TokenUsage,
} from '@/lib/billing/tokenBudgets';

function trimForHistory(value: unknown): string {
  return String(value || '').slice(0, 20000);
}

export async function POST(req: Request) {
  let tokenReservation: TokenReservation | null = null;
  let userContext: Awaited<ReturnType<typeof getUserContext>> = null;
  try {
    const body = await req.json();
    userContext = await getUserContext(req);
    const limited = await enforceRateLimit(req, 'chat', userContext ? {
      identifier: userContext.user.id,
      tier: userContext.profile.tier,
      role: userContext.profile.role,
    } : {});
    if (limited) return limited;

    if (userContext && tokenLimitsEnabled()) {
      const requestId = randomUUID();
      const estimatedTokens = estimateChatTokens(body);
      tokenReservation = await reserveAiTokens(userContext.supabaseAdmin, {
        userId: userContext.user.id,
        tier: userContext.profile.tier,
        role: userContext.profile.role,
        requestId,
        estimatedTokens,
        feature: 'chat',
        provider: 'openrouter',
        model: process.env.OPENROUTER_MODEL || null,
      });

      if (!tokenReservation.allowed) {
        return NextResponse.json(
          {
            error: 'token_budget_exceeded',
            daily_limit: tokenReservation.dailyLimit,
            monthly_limit: tokenReservation.monthlyLimit,
            daily_remaining: tokenReservation.dailyRemaining,
            monthly_remaining: tokenReservation.monthlyRemaining,
          },
          { status: 429 },
        );
      }
    }

    const TARGET = process.env.NODE_ENV === 'development'
      ? 'http://127.0.0.1:8000/api/chat'
      : `${process.env.NEXT_PUBLIC_API_URL}/api/chat`;

    console.log(`Proxying chat request to: ${TARGET}`);

    const proxyRes = await fetch(TARGET, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': getClientIp(req),
        ...(userContext ? {
          'X-User-Id': userContext.user.id,
          'X-User-Tier': userContext.profile.tier,
        } : {}),
        ...(process.env.CHAT_INTERNAL_PROXY_KEY ? {
          'X-Internal-Proxy-Key': process.env.CHAT_INTERNAL_PROXY_KEY,
        } : {}),
      },
      body: JSON.stringify(body),
    });

    if (!proxyRes.ok) {
        const errorText = await proxyRes.text();
        console.error(`Upstream Error (${proxyRes.status}):`, errorText);
        if (tokenReservation && userContext) {
          await finalizeAiUsage(userContext.supabaseAdmin, {
            requestId: tokenReservation.requestId,
            success: false,
            errorMessage: `upstream_error:${proxyRes.status}`,
          });
        }
        return NextResponse.json({ error: 'Upstream Error' }, { status: proxyRes.status });
    }

    const data = await proxyRes.json();
    const usage = (data?._usage || null) as TokenUsage | null;
    if (data && typeof data === 'object' && '_usage' in data) {
      delete data._usage;
    }

    if (tokenReservation && userContext) {
      await finalizeAiUsage(userContext.supabaseAdmin, {
        requestId: tokenReservation.requestId,
        usage,
        success: true,
      });
    }

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
            explanation_mode: body.explanation_mode || null,
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
            conversation_context: data.conversation_context || null,
            has_quant_data: Boolean(data.quant_data),
            source_freshness: data.source_freshness || null,
            data_quality: data.data_quality || null,
            risk_analysis: data.risk_analysis || null,
            confidence: data.confidence || null,
            trace_id: data.trace_id || null,
            coverage_status: data.coverage_status || null,
            model_status: data.model_status || null,
            status_flag: data.status_flag || null,
            resolution: data.resolution || null,
            explanation_mode: data.explanation_mode || body.explanation_mode || null,
            answer_mode: data.answer_mode || null,
            news_context_status: data.news_context_status || null,
            sources: data.sources || null,
            reasoning_summary: data.reasoning_summary || null,
          },
        },
      ].filter((row) => row.content.trim().length > 0);

      if (rows.length > 0 && body.session_id) {
        const rowsWithSession = rows.map(r => ({ ...r, session_id: body.session_id }));
        const { error } = await userContext.supabaseAdmin.from('ai_chat_messages').insert(rowsWithSession);
        if (error) console.error('Chat history write failed:', error);

        // Update session's updated_at
        await userContext.supabaseAdmin
          .from('ai_chat_sessions')
          .update({ updated_at: new Date(nowMs + 1).toISOString() })
          .eq('id', body.session_id);
      }
    }

    return NextResponse.json(data);

  } catch (error) {
    console.error('Chat Proxy Error:', error);
    if (tokenReservation && userContext) {
      try {
        await finalizeAiUsage(userContext.supabaseAdmin, {
          requestId: tokenReservation.requestId,
          success: false,
          errorMessage: error instanceof Error ? error.message.slice(0, 500) : 'chat_proxy_error',
        });
      } catch (usageError) {
        console.error('AI usage finalization failed:', usageError);
      }
    }
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
