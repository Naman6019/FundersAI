alter table public.mf_discovery_documents
  drop constraint if exists mf_discovery_documents_month_confirmation_check;

alter table public.mf_discovery_documents
  add constraint mf_discovery_documents_month_confirmation_check
  check (month_confirmation in ('confirmed', 'content_confirmed', 'unconfirmed'));
