-- Allow one official file to be represented by multiple parser document types.
--
-- HDFC/Axis factsheets can be reused as portfolio_disclosure inputs. The old
-- global checksum uniqueness blocked that because both rows point to the same
-- official PDF bytes.

alter table if exists public.mf_raw_documents
  drop constraint if exists mf_raw_documents_checksum_key;

create unique index if not exists mf_raw_documents_checksum_amc_type_month_key
  on public.mf_raw_documents (
    checksum,
    amc_code,
    coalesce(document_type, source_document_type, ''),
    coalesce(report_month, date '0001-01-01')
  );
