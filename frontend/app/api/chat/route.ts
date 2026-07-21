import { NextResponse } from 'next/server';
import { randomUUID } from 'crypto';
import { requireUserContext, type UserContext } from '@/lib/auth/server';
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

type ChatPayload = Record<string, unknown>;

function encodeSse(event: Record<string, unknown>): Uint8Array {
  return new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`);
}

function parseSseEvent(frame: string): Record<string, unknown> | null {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n');
  if (!data) return null;
  return JSON.parse(data) as Record<string, unknown>;
}

async function persistChatResult(
  userContext: UserContext,
  sessionId: string | null,
  requestBody: Record<string, unknown>,
  data: ChatPayload,
): Promise<string | null> {
  if (!sessionId) return null;

  const nowMs = Date.now();
  const rows = [
    {
      user_id: userContext.user.id,
      role: 'user',
      content: trimForHistory(requestBody.query),
      created_at: new Date(nowMs).toISOString(),
      metadata: {
        asset_type: requestBody.asset_type || null,
        research_depth: requestBody.research_depth || null,
        explanation_mode: requestBody.explanation_mode || null,
        comparison_view_mode: requestBody.comparison_view_mode || null,
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
        explanation_mode: data.explanation_mode || requestBody.explanation_mode || null,
        answer_mode: data.answer_mode || null,
        news_context_status: data.news_context_status || null,
        sources: data.sources || null,
        reasoning_summary: data.reasoning_summary || null,
      },
    },
  ].filter((row) => row.content.trim().length > 0);

  if (rows.length === 0) return null;
  const rowsWithSession = rows.map((row) => ({ ...row, session_id: sessionId }));
  const { data: insertedRows, error: insertError } = await userContext.supabaseAdmin
    .from('ai_chat_messages')
    .insert(rowsWithSession)
    .select('id,role');
  if (insertError) throw new Error(`chat_history_write_failed:${insertError.message}`);

  const { error: updateError } = await userContext.supabaseAdmin
    .from('ai_chat_sessions')
    .update({ updated_at: new Date(nowMs + 1).toISOString() })
    .eq('id', sessionId)
    .eq('user_id', userContext.user.id);
  if (updateError) throw new Error(`chat_session_update_failed:${updateError.message}`);
  return insertedRows?.find((row) => row.role === 'system')?.id || null;
}

export async function POST(req: Request) {
  let tokenReservation: TokenReservation | null = null;
  let userContext: UserContext | null = null;
  try {
    const auth = await requireUserContext(req);
    if (!auth.ok) return auth.response;
    userContext = auth.context;

    const body = await req.json();
    const rawSessionId = body.session_id;
    const sessionId = typeof rawSessionId === 'string' ? rawSessionId.trim() : null;
    if (rawSessionId != null && !sessionId) {
      return NextResponse.json({ error: 'invalid_session_id' }, { status: 400 });
    }

    if (sessionId) {
      const { data: ownedSession, error: sessionError } = await userContext.supabaseAdmin
        .from('ai_chat_sessions')
        .select('id')
        .eq('id', sessionId)
        .eq('user_id', userContext.user.id)
        .maybeSingle();

      if (sessionError) {
        console.error('Chat session ownership check failed:', sessionError);
        return NextResponse.json({ error: 'session_ownership_check_failed' }, { status: 500 });
      }
      if (!ownedSession) {
        return NextResponse.json({ error: 'session_not_found' }, { status: 403 });
      }
    }

    const limited = await enforceRateLimit(req, 'chat', {
      identifier: userContext.user.id,
      tier: userContext.profile.tier,
      role: userContext.profile.role,
    });
    if (limited) return limited;

    if (tokenLimitsEnabled()) {
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
        'X-User-Id': userContext.user.id,
        'X-User-Tier': userContext.profile.tier,
        ...(process.env.CHAT_INTERNAL_PROXY_KEY ? {
          'X-Internal-Proxy-Key': process.env.CHAT_INTERNAL_PROXY_KEY,
        } : {}),
      },
      body: JSON.stringify(body),
    });

    if (!proxyRes.ok) {
        const errorText = await proxyRes.text();
        console.error(`Upstream Error (${proxyRes.status}):`, errorText);
        if (tokenReservation) {
          await finalizeAiUsage(userContext.supabaseAdmin, {
            requestId: tokenReservation.requestId,
            success: false,
            errorMessage: `upstream_error:${proxyRes.status}`,
          });
        }
        return NextResponse.json({ error: 'Upstream Error' }, { status: proxyRes.status });
    }

    if (!proxyRes.body) {
      if (tokenReservation) {
        await finalizeAiUsage(userContext.supabaseAdmin, {
          requestId: tokenReservation.requestId,
          success: false,
          errorMessage: 'empty_upstream_response',
        });
      }
      return NextResponse.json({ error: 'Empty response' }, { status: 500 });
    }

    const context = userContext;
    const reservation = tokenReservation;
    const upstreamReader = proxyRes.body.getReader();
    let clientClosed = false;
    let usageFinalized = false;

    const finalizeUsage = async (
      success: boolean,
      usage: TokenUsage | null = null,
      errorMessage?: string,
    ) => {
      if (!reservation || usageFinalized) return;
      usageFinalized = true;
      try {
        await finalizeAiUsage(context.supabaseAdmin, {
          requestId: reservation.requestId,
          usage,
          success,
          errorMessage,
        });
      } catch (usageError) {
        console.error('AI usage finalization failed:', usageError);
      }
    };

    const responseStream = new ReadableStream<Uint8Array>({
      start(controller) {
        const emit = (event: Record<string, unknown>) => {
          if (clientClosed) return;
          try {
            controller.enqueue(encodeSse(event));
          } catch {
            clientClosed = true;
          }
        };

        void (async () => {
          const decoder = new TextDecoder();
          let buffer = '';
          let terminalEventSeen = false;

          const handleFrame = async (frame: string) => {
            const event = parseSseEvent(frame);
            if (!event || terminalEventSeen) return;

            if (event.type === 'status' && typeof event.message === 'string') {
              emit({ type: 'status', message: event.message });
              return;
            }

            if (event.type === 'error') {
              terminalEventSeen = true;
              await finalizeUsage(false, null, 'upstream_stream_error');
              emit({
                type: 'error',
                message: 'FundersAI research service could not complete the request.',
              });
              return;
            }

            if (event.type === 'final' && event.payload && typeof event.payload === 'object') {
              terminalEventSeen = true;
              const data = { ...(event.payload as ChatPayload) };
              const usage = (data._usage || null) as TokenUsage | null;
              delete data._usage;
              const responseMessageId = await persistChatResult(context, sessionId, body, data);
              data.response_message_id = responseMessageId;
              await finalizeUsage(true, usage);
              emit({ type: 'final', payload: data });
            }
          };

          try {
            while (true) {
              const { done, value } = await upstreamReader.read();
              if (done) break;
              buffer += decoder.decode(value, { stream: true });

              let boundary = buffer.search(/\r?\n\r?\n/);
              while (boundary >= 0) {
                const frame = buffer.slice(0, boundary);
                const delimiter = buffer.slice(boundary).match(/^(?:\r?\n){2}/)?.[0] || '\n\n';
                buffer = buffer.slice(boundary + delimiter.length);
                await handleFrame(frame);
                boundary = buffer.search(/\r?\n\r?\n/);
              }
            }

            buffer += decoder.decode();
            if (buffer.trim()) await handleFrame(buffer);
            if (!terminalEventSeen) {
              await finalizeUsage(false, null, 'missing_terminal_stream_event');
              emit({
                type: 'error',
                message: 'FundersAI research service ended without a final response.',
              });
            }
          } catch (streamError) {
            console.error('Chat stream processing failed:', streamError);
            await finalizeUsage(
              false,
              null,
              streamError instanceof Error ? streamError.message.slice(0, 500) : 'chat_stream_error',
            );
            emit({
              type: 'error',
              message: 'FundersAI could not save or complete this response. Please retry.',
            });
          } finally {
            upstreamReader.releaseLock();
            if (!clientClosed) controller.close();
          }
        })();
      },
      cancel() {
        // Continue reading upstream so accounting and owned-session persistence complete.
        clientClosed = true;
      },
    });

    return new Response(responseStream, {
      status: proxyRes.status,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

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
