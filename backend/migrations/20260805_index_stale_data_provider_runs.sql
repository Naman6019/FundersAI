create index if not exists data_provider_runs_status_started_at_idx
  on public.data_provider_runs (status, started_at)
  where finished_at is null;
