create extension if not exists pgcrypto;

create table if not exists public.user_feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  feedback_type text not null check (feedback_type in ('general', 'response', 'logout')),
  rating smallint not null check (rating between 1 and 5),
  comment text check (comment is null or char_length(comment) <= 2000),
  message_id uuid references public.ai_chat_messages(id) on delete set null,
  session_id uuid references public.ai_chat_sessions(id) on delete set null,
  trace_id text check (trace_id is null or char_length(trace_id) <= 128),
  page_path text check (page_path is null or char_length(page_path) <= 500),
  response_excerpt text check (response_excerpt is null or char_length(response_excerpt) <= 1000),
  created_at timestamptz not null default now()
);

create index if not exists user_feedback_user_created_idx
  on public.user_feedback (user_id, created_at desc);

create index if not exists user_feedback_type_created_idx
  on public.user_feedback (feedback_type, created_at desc);

create index if not exists user_feedback_trace_idx
  on public.user_feedback (trace_id)
  where trace_id is not null;

alter table public.user_feedback enable row level security;

revoke all on table public.user_feedback from anon, authenticated;
grant select, insert, update, delete on table public.user_feedback to service_role;
