import { NextResponse } from 'next/server';
import { createServiceClient, getUserContext } from '@/lib/auth/server';
import { enforceRateLimit } from '@/lib/rateLimit';

const FEEDBACK_TYPES = new Set(['general', 'response', 'logout']);
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const MAX_FEEDBACK_BODY_BYTES = 16_384;

function requestSecurityError(request: Request): NextResponse | null {
  const contentType = request.headers.get('content-type')?.split(';', 1)[0]?.trim().toLowerCase();
  if (contentType !== 'application/json') {
    return NextResponse.json({ error: 'unsupported_media_type' }, { status: 415 });
  }

  const contentLength = Number(request.headers.get('content-length') || 0);
  if (Number.isFinite(contentLength) && contentLength > MAX_FEEDBACK_BODY_BYTES) {
    return NextResponse.json({ error: 'feedback_payload_too_large' }, { status: 413 });
  }

  const origin = request.headers.get('origin');
  if (origin && origin !== new URL(request.url).origin) {
    return NextResponse.json({ error: 'cross_origin_request_blocked' }, { status: 403 });
  }

  return null;
}

function optionalText(value: unknown, maxLength: number): string | null {
  if (typeof value !== 'string') return null;
  const clean = value.trim();
  return clean ? clean.slice(0, maxLength) : null;
}

function optionalUuid(value: unknown): string | null {
  const clean = optionalText(value, 36);
  return clean && UUID_PATTERN.test(clean) ? clean : null;
}

export async function POST(request: Request) {
  try {
    const securityError = requestSecurityError(request);
    if (securityError) return securityError;

    const body = await request.json();
    if (body?.website) {
      return NextResponse.json({ error: 'invalid_feedback' }, { status: 400 });
    }

    const feedbackType = optionalText(body?.feedback_type, 20);
    const rating = Number(body?.rating);
    if (!feedbackType || !FEEDBACK_TYPES.has(feedbackType) || !Number.isInteger(rating) || rating < 1 || rating > 5) {
      return NextResponse.json({ error: 'invalid_feedback' }, { status: 400 });
    }

    const userContext = await getUserContext(request);
    if (feedbackType !== 'logout' && !userContext) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const limited = await enforceRateLimit(request, 'feedback', userContext ? {
      identifier: userContext.user.id,
      tier: userContext.profile.tier,
      role: userContext.profile.role,
    } : {});
    if (limited) return limited;

    const supabaseAdmin = userContext?.supabaseAdmin || createServiceClient();
    if (!supabaseAdmin) {
      return NextResponse.json({ error: 'feedback_storage_unavailable' }, { status: 503 });
    }

    const isResponseFeedback = feedbackType === 'response';
    const messageId = isResponseFeedback ? optionalUuid(body?.message_id) : null;
    const sessionId = isResponseFeedback ? optionalUuid(body?.session_id) : null;
    const traceId = isResponseFeedback ? optionalText(body?.trace_id, 128) : null;
    if (feedbackType === 'response' && !messageId && !traceId) {
      return NextResponse.json({ error: 'response_target_required' }, { status: 400 });
    }

    if (userContext && messageId) {
      const { data: ownedMessage, error } = await supabaseAdmin
        .from('ai_chat_messages')
        .select('id')
        .eq('id', messageId)
        .eq('user_id', userContext.user.id)
        .eq('role', 'system')
        .maybeSingle();
      if (error || !ownedMessage) {
        return NextResponse.json({ error: 'message_not_found' }, { status: 403 });
      }
    }

    if (userContext && sessionId) {
      const { data: ownedSession, error } = await supabaseAdmin
        .from('ai_chat_sessions')
        .select('id')
        .eq('id', sessionId)
        .eq('user_id', userContext.user.id)
        .maybeSingle();
      if (error || !ownedSession) {
        return NextResponse.json({ error: 'session_not_found' }, { status: 403 });
      }
    }

    const { error } = await supabaseAdmin.from('user_feedback').insert({
      user_id: userContext?.user.id || null,
      feedback_type: feedbackType,
      rating,
      comment: optionalText(body?.comment, 2000),
      message_id: messageId,
      session_id: sessionId,
      trace_id: traceId,
      page_path: optionalText(body?.page_path, 500),
      response_excerpt: isResponseFeedback ? optionalText(body?.response_excerpt, 1000) : null,
    });

    if (error) {
      console.error('Feedback write failed:', {
        code: error.code,
        message: error.message,
      });
      const storageUnavailable = error.code === 'PGRST205' || error.code === '42P01';
      return NextResponse.json(
        { error: storageUnavailable ? 'feedback_storage_unavailable' : 'feedback_write_failed' },
        { status: storageUnavailable ? 503 : 500 },
      );
    }

    return NextResponse.json({ ok: true }, { status: 201 });
  } catch (error) {
    console.error('Feedback request failed:', error);
    return NextResponse.json({ error: 'invalid_feedback' }, { status: 400 });
  }
}
