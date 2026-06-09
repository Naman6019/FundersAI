import { NextResponse } from 'next/server';
import { requireUserContext } from '@/lib/auth/server';

type ChatMessageRow = {
  id: string;
  role: 'user' | 'system';
  content: string;
  created_at: string;
  metadata?: Record<string, unknown> | null;
};

export async function GET(request: Request) {
  const auth = await requireUserContext(request);
  if (!auth.ok) return auth.response;

  const { user, supabaseAdmin } = auth.context;
  const { data, error } = await supabaseAdmin
    .from('chat_messages')
    .select('id,role,content,created_at,metadata')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })
    .limit(80);

  if (error) {
    console.error('Chat history read failed:', error);
    return NextResponse.json({ error: 'History read failed' }, { status: 500 });
  }

  const messages = ((data || []) as ChatMessageRow[]).reverse();
  return NextResponse.json({ messages });
}

export async function DELETE(request: Request) {
  const auth = await requireUserContext(request);
  if (!auth.ok) return auth.response;

  const { user, supabaseAdmin } = auth.context;
  const { error } = await supabaseAdmin
    .from('chat_messages')
    .delete()
    .eq('user_id', user.id);

  if (error) {
    console.error('Chat history clear failed:', error);
    return NextResponse.json({ error: 'History clear failed' }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
