alter table public.provider_response_cache enable row level security;

revoke all on table public.provider_response_cache from public;
revoke all on table public.provider_response_cache from anon;
revoke all on table public.provider_response_cache from authenticated;

grant select, insert, update, delete on table public.provider_response_cache to service_role;
