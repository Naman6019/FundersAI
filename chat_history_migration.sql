-- Migration: Create AI Chat Sessions and Messages Tables

CREATE TABLE IF NOT EXISTS public.ai_chat_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- Nullable for anonymous users
    title TEXT NOT NULL DEFAULT 'New Chat',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.ai_chat_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES public.ai_chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'system', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_ai_chat_sessions_user_id ON public.ai_chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_messages_session_id ON public.ai_chat_messages(session_id);

-- Optional: RLS (Row Level Security)
-- Uncomment these if you have authentication enforced.
-- ALTER TABLE public.ai_chat_sessions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.ai_chat_messages ENABLE ROW LEVEL SECURITY;

-- CREATE POLICY "Users can view their own sessions" ON public.ai_chat_sessions FOR SELECT USING (auth.uid() = user_id);
-- CREATE POLICY "Users can insert their own sessions" ON public.ai_chat_sessions FOR INSERT WITH CHECK (auth.uid() = user_id);
-- CREATE POLICY "Users can update their own sessions" ON public.ai_chat_sessions FOR UPDATE USING (auth.uid() = user_id);
-- CREATE POLICY "Users can delete their own sessions" ON public.ai_chat_sessions FOR DELETE USING (auth.uid() = user_id);

-- CREATE POLICY "Users can view their own messages" ON public.ai_chat_messages FOR SELECT USING (EXISTS (SELECT 1 FROM public.ai_chat_sessions WHERE id = session_id AND user_id = auth.uid()));
-- CREATE POLICY "Users can insert their own messages" ON public.ai_chat_messages FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM public.ai_chat_sessions WHERE id = session_id AND user_id = auth.uid()));
