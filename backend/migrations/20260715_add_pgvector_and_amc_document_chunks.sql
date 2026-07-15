-- Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the table for storing AMC document chunks and embeddings
CREATE TABLE IF NOT EXISTS public.amc_document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES public.mf_raw_documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding vector(1536), -- Default for OpenAI text-embedding-3-small, adjust if needed
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.amc_document_chunks
  ADD COLUMN IF NOT EXISTS chunk_hash text,
  ADD COLUMN IF NOT EXISTS embedding_model text,
  ADD COLUMN IF NOT EXISTS embedding_version text,
  ADD COLUMN IF NOT EXISTS parser_version text,
  ADD COLUMN IF NOT EXISTS source_url text;

CREATE UNIQUE INDEX IF NOT EXISTS amc_document_chunks_document_hash_idx
  ON public.amc_document_chunks (document_id, chunk_hash);

-- Create an HNSW index for fast nearest-neighbor search
CREATE INDEX ON public.amc_document_chunks USING hnsw (embedding vector_cosine_ops);

-- Enable Row Level Security (admin only)
ALTER TABLE public.amc_document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow admin access to document chunks"
    ON public.amc_document_chunks
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles
            WHERE user_profiles.user_id = auth.uid()
            AND user_profiles.role = 'admin'
        )
    );

-- Create a Postgres function for similarity search
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    filter_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_text TEXT,
    metadata JSONB,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        adc.id,
        adc.document_id,
        adc.chunk_text,
        adc.metadata,
        1 - (adc.embedding <=> query_embedding) AS similarity
    FROM public.amc_document_chunks adc
    WHERE 1 - (adc.embedding <=> query_embedding) > match_threshold
      AND adc.metadata @> filter_metadata
    ORDER BY adc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

ALTER TABLE public.mf_parse_review_queue
  ADD COLUMN IF NOT EXISTS reviewer_decision text,
  ADD COLUMN IF NOT EXISTS issue_category text,
  ADD COLUMN IF NOT EXISTS reparse_succeeded boolean,
  ADD COLUMN IF NOT EXISTS reviewed_at timestamptz,
  ADD COLUMN IF NOT EXISTS review_duration_seconds integer;
