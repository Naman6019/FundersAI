import { NextResponse } from 'next/server';
import { getUserContext } from '@/lib/auth/server';

export async function GET(req: Request) {
  try {
    const userContext = await getUserContext(req);
    if (!userContext) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { data, error } = await userContext.supabaseAdmin
      .from('ai_chat_sessions')
      .select('*')
      .eq('user_id', userContext.user.id)
      .order('updated_at', { ascending: false });

    if (error) {
      console.error('Error fetching chat sessions:', error);
      return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }

    return NextResponse.json({ sessions: data });
  } catch (error) {
    console.error('Error in GET /api/chat/sessions:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const userContext = await getUserContext(req);
    if (!userContext) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await req.json();
    const title = body.title || 'New Chat';

    const { data, error } = await userContext.supabaseAdmin
      .from('ai_chat_sessions')
      .insert([
        {
          user_id: userContext.user.id,
          title,
        },
      ])
      .select()
      .single();

    if (error) {
      console.error('Error creating chat session:', error);
      return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }

    return NextResponse.json({ session: data });
  } catch (error) {
    console.error('Error in POST /api/chat/sessions:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
