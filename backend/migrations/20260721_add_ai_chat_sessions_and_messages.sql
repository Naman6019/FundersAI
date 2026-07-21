create extension if not exists pgcrypto;

create table if not exists public.ai_chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'New Chat',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.ai_chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.ai_chat_sessions(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'system')),
  content text not null check (char_length(content) <= 20000),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- Repair older deployments where these tables already exist with a partial schema.
alter table public.ai_chat_sessions
  add column if not exists user_id uuid,
  add column if not exists title text not null default 'New Chat',
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

alter table public.ai_chat_messages
  add column if not exists session_id uuid,
  add column if not exists user_id uuid,
  add column if not exists role text,
  add column if not exists content text,
  add column if not exists metadata jsonb not null default '{}'::jsonb,
  add column if not exists created_at timestamptz not null default now();

update public.ai_chat_messages as message
set user_id = session.user_id
from public.ai_chat_sessions as session
where message.session_id = session.id
  and message.user_id is null;

do $$
begin
  if exists (select 1 from public.ai_chat_sessions where user_id is null) then
    raise exception 'ai_chat_sessions contains rows without user_id; repair ownership before applying constraints';
  end if;
  if exists (select 1 from public.ai_chat_messages where session_id is null or user_id is null) then
    raise exception 'ai_chat_messages contains orphan rows; repair session ownership before applying constraints';
  end if;
end
$$;

alter table public.ai_chat_sessions
  alter column user_id set not null;

alter table public.ai_chat_messages
  alter column session_id set not null,
  alter column user_id set not null,
  alter column role set not null,
  alter column content set not null;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_chat_sessions'::regclass
      and conname = 'ai_chat_sessions_user_id_fkey'
  ) then
    alter table public.ai_chat_sessions
      add constraint ai_chat_sessions_user_id_fkey
      foreign key (user_id) references auth.users(id) on delete cascade;
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_chat_messages'::regclass
      and conname = 'ai_chat_messages_session_id_fkey'
  ) then
    alter table public.ai_chat_messages
      add constraint ai_chat_messages_session_id_fkey
      foreign key (session_id) references public.ai_chat_sessions(id) on delete cascade;
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_chat_messages'::regclass
      and conname = 'ai_chat_messages_user_id_fkey'
  ) then
    alter table public.ai_chat_messages
      add constraint ai_chat_messages_user_id_fkey
      foreign key (user_id) references auth.users(id) on delete cascade;
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_chat_messages'::regclass
      and conname = 'ai_chat_messages_role_check'
  ) then
    alter table public.ai_chat_messages
      add constraint ai_chat_messages_role_check
      check (role in ('user', 'system'));
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.ai_chat_messages'::regclass
      and conname = 'ai_chat_messages_content_length_check'
  ) then
    alter table public.ai_chat_messages
      add constraint ai_chat_messages_content_length_check
      check (char_length(content) <= 20000);
  end if;
end
$$;

create index if not exists ai_chat_sessions_user_updated_idx
  on public.ai_chat_sessions (user_id, updated_at desc);

create index if not exists ai_chat_messages_session_created_idx
  on public.ai_chat_messages (session_id, created_at);

create index if not exists ai_chat_messages_user_created_idx
  on public.ai_chat_messages (user_id, created_at desc);

alter table public.ai_chat_sessions enable row level security;
alter table public.ai_chat_messages enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'ai_chat_sessions'
      and policyname = 'ai_chat_sessions_own_rows'
  ) then
    create policy ai_chat_sessions_own_rows
      on public.ai_chat_sessions
      for all
      to authenticated
      using (user_id = auth.uid())
      with check (user_id = auth.uid());
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'ai_chat_messages'
      and policyname = 'ai_chat_messages_own_rows'
  ) then
    create policy ai_chat_messages_own_rows
      on public.ai_chat_messages
      for all
      to authenticated
      using (user_id = auth.uid())
      with check (
        user_id = auth.uid()
        and exists (
          select 1
          from public.ai_chat_sessions as session
          where session.id = session_id
            and session.user_id = auth.uid()
        )
      );
  end if;
end
$$;
