create extension if not exists pgcrypto;

do $$
declare
  constraint_record record;
begin
  for constraint_record in
    select conname
    from pg_constraint
    where conrelid = 'public.user_profiles'::regclass
      and contype = 'c'
      and pg_get_constraintdef(oid) like '%tier%'
  loop
    execute format('alter table public.user_profiles drop constraint if exists %I', constraint_record.conname);
  end loop;
end
$$;

alter table public.user_profiles
  add constraint user_profiles_tier_check check (tier in ('free', 'pro', 'ultra'));

create table if not exists public.billing_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  provider text not null default 'razorpay' check (provider in ('razorpay')),
  tier text not null check (tier in ('pro', 'ultra')),
  billing_period text not null default 'monthly' check (billing_period in ('monthly', 'annual', 'lifetime')),
  status text not null default 'created',
  provider_plan_id text not null,
  provider_subscription_id text not null,
  provider_customer_id text,
  provider_payment_id text,
  current_start timestamptz,
  current_end timestamptz,
  ended_at timestamptz,
  cancel_at_cycle_end boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (provider, provider_subscription_id)
);

create index if not exists billing_subscriptions_user_idx
  on public.billing_subscriptions (user_id, created_at desc);

create index if not exists billing_subscriptions_status_idx
  on public.billing_subscriptions (status);

create unique index if not exists billing_subscriptions_one_live_per_user_idx
  on public.billing_subscriptions (provider, user_id)
  where status in ('created', 'authenticated', 'active', 'pending', 'halted');

create table if not exists public.billing_events (
  id uuid primary key default gen_random_uuid(),
  provider text not null default 'razorpay' check (provider in ('razorpay')),
  event_id text not null,
  event_type text not null,
  provider_subscription_id text,
  payload jsonb not null default '{}'::jsonb,
  processed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (provider, event_id)
);

create index if not exists billing_events_subscription_idx
  on public.billing_events (provider_subscription_id, created_at desc);

create or replace function public.touch_billing_subscriptions_updated_at()
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
    where tgname = 'touch_billing_subscriptions_updated_at'
      and tgrelid = 'public.billing_subscriptions'::regclass
  ) then
    create trigger touch_billing_subscriptions_updated_at
      before update on public.billing_subscriptions
      for each row
      execute function public.touch_billing_subscriptions_updated_at();
  end if;
end
$$;

alter table public.billing_subscriptions enable row level security;
alter table public.billing_events enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'billing_subscriptions'
      and policyname = 'billing_subscriptions_select_own_or_admin'
  ) then
    create policy billing_subscriptions_select_own_or_admin
      on public.billing_subscriptions
      for select
      to authenticated
      using (user_id = auth.uid() or public.current_user_is_admin());
  end if;
end
$$;
