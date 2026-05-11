create extension if not exists pgcrypto;

create table if not exists public.provider_usage_logs (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  endpoint text not null,
  symbol text,
  scheme_code text,
  user_id uuid,
  cache_hit boolean not null default false,
  status_code int,
  success boolean not null default true,
  error_message text,
  request_cost int not null default 1,
  created_at timestamptz not null default now()
);

create index if not exists provider_usage_logs_provider_created_idx
  on public.provider_usage_logs (provider, created_at desc);
create index if not exists provider_usage_logs_symbol_provider_idx
  on public.provider_usage_logs (symbol, provider);
create index if not exists provider_usage_logs_scheme_provider_idx
  on public.provider_usage_logs (scheme_code, provider);
create index if not exists provider_usage_logs_user_created_idx
  on public.provider_usage_logs (user_id, created_at desc);

create table if not exists public.stock_core_snapshot (
  symbol text primary key,
  company_name text,
  exchange text,
  sector text,
  industry text,
  market_cap numeric(24,4),
  close_price numeric(24,4),
  previous_close numeric(24,4),
  change_percent numeric(12,4),
  volume numeric(24,4),
  price_date date,
  revenue_ttm numeric(24,4),
  net_profit_ttm numeric(24,4),
  eps_ttm numeric(24,6),
  pe_ratio numeric(18,6),
  pb_ratio numeric(18,6),
  roe numeric(18,6),
  roce numeric(18,6),
  debt_to_equity numeric(18,6),
  operating_margin numeric(18,6),
  net_profit_margin numeric(18,6),
  dividend_yield numeric(18,6),
  data_source text,
  provider_payload jsonb,
  last_updated timestamptz not null default now()
);

create index if not exists stock_core_snapshot_last_updated_idx
  on public.stock_core_snapshot (last_updated desc);

create table if not exists public.mutual_fund_core_snapshot (
  scheme_code text primary key,
  scheme_name text,
  amc_name text,
  category text,
  sub_category text,
  plan_type text,
  option_type text,
  fund_type text,
  nav numeric(18,6),
  nav_date date,
  return_1m numeric(18,6),
  return_3m numeric(18,6),
  return_6m numeric(18,6),
  return_1y numeric(18,6),
  return_3y numeric(18,6),
  return_5y numeric(18,6),
  volatility_1y numeric(18,6),
  max_drawdown_1y numeric(18,6),
  expense_ratio numeric(18,6),
  aum numeric(24,4),
  benchmark text,
  risk_level text,
  alpha numeric(18,6),
  beta numeric(18,6),
  sharpe_ratio numeric(18,6),
  data_source text,
  provider_payload jsonb,
  last_updated timestamptz not null default now()
);

create index if not exists mutual_fund_core_snapshot_last_updated_idx
  on public.mutual_fund_core_snapshot (last_updated desc);

create table if not exists public.mutual_fund_nav_history (
  scheme_code text not null,
  nav_date date not null,
  nav numeric(18,6) not null,
  data_source text,
  created_at timestamptz not null default now(),
  primary key (scheme_code, nav_date)
);

create index if not exists mutual_fund_nav_history_scheme_date_idx
  on public.mutual_fund_nav_history (scheme_code, nav_date desc);
