export type ClaimVerdict = 'supported' | 'contradicted' | 'mixed' | 'unverifiable';
export type ClaimFreshness = 'current' | 'stale' | 'unknown';
export type ClaimStatus =
  | 'evaluated'
  | 'clarification_required'
  | 'unsupported'
  | 'entity_resolution_required';

export type ClaimEvidence = {
  source_type: string;
  source_name: string;
  source_url: string | null;
  document_id: string | null;
  as_of_date: string | null;
  source_fingerprint: string | null;
};

export type ClaimClarification = {
  reason: string;
  prompt: string;
  choices: string[];
};

export type AtomicClaim = {
  statement: string;
  metric: string | null;
  operator: string | null;
  status: ClaimStatus;
  verdict: ClaimVerdict;
  freshness: ClaimFreshness;
  values: Record<string, unknown>;
  evidence: ClaimEvidence[];
  limitations: string[];
  clarification: ClaimClarification | null;
  trackable: boolean;
};

export type ResolvedEntity = {
  input: string;
  scheme_code: string | null;
  scheme_name: string | null;
  amc_name: string | null;
  confidence: number;
  resolution_status: string;
  candidates: Array<Record<string, unknown>>;
};

export type ClaimCheckResponse = {
  input: string;
  resolved_entities: ResolvedEntity[];
  claims: AtomicClaim[];
  generated_at: string;
};
