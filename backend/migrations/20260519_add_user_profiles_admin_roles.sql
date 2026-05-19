create extension if not exists pgcrypto;

create table if not exists public.user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'user' check (role in ('user', 'admin', 'tester')),
  tier text not null default 'free' check (tier in ('free', 'pro')),
  last_active_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.user_profiles
  add column if not exists role text not null default 'user' check (role in ('user', 'admin', 'tester'));

alter table public.user_profiles
  add column if not exists tier text not null default 'free' check (tier in ('free', 'pro'));

alter table public.user_profiles
  add column if not exists last_active_at timestamptz;

alter table public.user_profiles
  add column if not exists created_at timestamptz not null default now();

alter table public.user_profiles
  add column if not exists updated_at timestamptz not null default now();

create or replace function public.touch_user_profiles_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

do $$
begin
  if not exists (
    select 1
    from pg_trigger
    where tgname = 'touch_user_profiles_updated_at'
      and tgrelid = 'public.user_profiles'::regclass
  ) then
    create trigger touch_user_profiles_updated_at
      before update on public.user_profiles
      for each row
      execute function public.touch_user_profiles_updated_at();
  end if;
end
$$;

create or replace function public.current_user_is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.user_profiles up
    where up.user_id = auth.uid()
      and up.role = 'admin'
  );
$$;

grant execute on function public.current_user_is_admin() to authenticated;

alter table public.user_profiles enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'user_profiles'
      and policyname = 'user_profiles_select_own_or_admin'
  ) then
    create policy user_profiles_select_own_or_admin
      on public.user_profiles
      for select
      to authenticated
      using (user_id = auth.uid() or public.current_user_is_admin());
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'user_profiles'
      and policyname = 'user_profiles_insert_own'
  ) then
    create policy user_profiles_insert_own
      on public.user_profiles
      for insert
      to authenticated
      with check (user_id = auth.uid() or public.current_user_is_admin());
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'user_profiles'
      and policyname = 'user_profiles_update_admin_only'
  ) then
    create policy user_profiles_update_admin_only
      on public.user_profiles
      for update
      to authenticated
      using (public.current_user_is_admin())
      with check (public.current_user_is_admin());
  end if;
end
$$;

create index if not exists user_profiles_role_idx on public.user_profiles (role);
create index if not exists user_profiles_tier_idx on public.user_profiles (tier);
create index if not exists user_profiles_last_active_idx on public.user_profiles (last_active_at);
