create table if not exists public.ai_usage_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  tier text not null check (tier in ('free', 'pro', 'ultra')),
  feature text not null default 'chat',
  provider text not null default 'openrouter',
  model text,
  prompt_tokens integer not null default 0 check (prompt_tokens >= 0),
  completion_tokens integer not null default 0 check (completion_tokens >= 0),
  total_tokens integer not null default 0 check (total_tokens >= 0),
  estimated_tokens integer not null default 0 check (estimated_tokens >= 0),
  reserved_tokens integer not null default 0 check (reserved_tokens >= 0),
  success boolean,
  error_message text,
  request_id uuid not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ai_usage_events_user_created_idx
  on public.ai_usage_events (user_id, created_at desc);

create index if not exists ai_usage_events_tier_created_idx
  on public.ai_usage_events (tier, created_at desc);

alter table public.ai_usage_events enable row level security;

create or replace function public.reserve_ai_tokens(
  p_user_id uuid,
  p_tier text,
  p_request_id uuid,
  p_estimated_tokens integer,
  p_daily_limit integer,
  p_monthly_limit integer,
  p_feature text default 'chat',
  p_provider text default 'openrouter',
  p_model text default null
)
returns table (
  allowed boolean,
  daily_used integer,
  monthly_used integer,
  daily_limit integer,
  monthly_limit integer,
  daily_remaining integer,
  monthly_remaining integer
)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_estimated integer := greatest(coalesce(p_estimated_tokens, 0), 0);
  v_daily_used integer := 0;
  v_monthly_used integer := 0;
  v_daily_limit integer := greatest(coalesce(p_daily_limit, 0), 0);
  v_monthly_limit integer := greatest(coalesce(p_monthly_limit, 0), 0);
begin
  select coalesce(sum(
    case
      when success = true then total_tokens
      when success is null then reserved_tokens
      else 0
    end
  ), 0)::integer
  into v_daily_used
  from public.ai_usage_events
  where user_id = p_user_id
    and created_at >= date_trunc('day', now());

  select coalesce(sum(
    case
      when success = true then total_tokens
      when success is null then reserved_tokens
      else 0
    end
  ), 0)::integer
  into v_monthly_used
  from public.ai_usage_events
  where user_id = p_user_id
    and created_at >= date_trunc('month', now());

  if v_daily_used + v_estimated > v_daily_limit
    or v_monthly_used + v_estimated > v_monthly_limit
  then
    return query select
      false,
      v_daily_used,
      v_monthly_used,
      v_daily_limit,
      v_monthly_limit,
      greatest(v_daily_limit - v_daily_used, 0),
      greatest(v_monthly_limit - v_monthly_used, 0);
    return;
  end if;

  insert into public.ai_usage_events (
    user_id,
    tier,
    feature,
    provider,
    model,
    estimated_tokens,
    reserved_tokens,
    request_id
  )
  values (
    p_user_id,
    p_tier,
    coalesce(nullif(p_feature, ''), 'chat'),
    coalesce(nullif(p_provider, ''), 'openrouter'),
    p_model,
    v_estimated,
    v_estimated,
    p_request_id
  );

  return query select
    true,
    v_daily_used + v_estimated,
    v_monthly_used + v_estimated,
    v_daily_limit,
    v_monthly_limit,
    greatest(v_daily_limit - v_daily_used - v_estimated, 0),
    greatest(v_monthly_limit - v_monthly_used - v_estimated, 0);
end;
$$;

revoke all on function public.reserve_ai_tokens(uuid, text, uuid, integer, integer, integer, text, text, text) from public;
revoke all on function public.reserve_ai_tokens(uuid, text, uuid, integer, integer, integer, text, text, text) from anon;
revoke all on function public.reserve_ai_tokens(uuid, text, uuid, integer, integer, integer, text, text, text) from authenticated;
grant execute on function public.reserve_ai_tokens(uuid, text, uuid, integer, integer, integer, text, text, text) to service_role;
