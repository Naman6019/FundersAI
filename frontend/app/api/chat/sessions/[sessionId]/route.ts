import { NextResponse } from 'next/server';
import { getUserContext } from '@/lib/auth/server';

export async function GET(req: Request, { params }: { params: Promise<{ sessionId: string }> }) {
  try {
    const { sessionId } = await params;
    const userContext = await getUserContext(req);
    if (!userContext) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Verify session belongs to user
    const { data: sessionData, error: sessionError } = await userContext.supabaseAdmin
      .from('ai_chat_sessions')
      .select('id')
      .eq('id', sessionId)
      .eq('user_id', userContext.user.id)
      .single();

    if (sessionError || !sessionData) {
      return NextResponse.json({ error: 'Session not found or unauthorized' }, { status: 404 });
    }

    const { data, error } = await userContext.supabaseAdmin
      .from('ai_chat_messages')
      .select('*')
      .eq('session_id', sessionId)
      .order('created_at', { ascending: true });

    if (error) {
      console.error('Error fetching chat messages:', error);
      return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }

    return NextResponse.json({ messages: data });
  } catch (error) {
    console.error('Error in GET /api/chat/sessions/[sessionId]:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
