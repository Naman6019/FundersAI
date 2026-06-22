from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IngestionConfig:
    raw_storage_root: Path
    request_timeout_seconds: float
    parser_version: str
    user_agent: str
    extractor_mode: str
    llm_extractor_enabled: bool
    llm_extractor_model: str
    source_manifest_path: str
    r2_endpoint: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_raw_bucket: str
    r2_cold_bucket: str
    r2_signed_url_ttl_seconds: int
    require_r2_for_raw_storage: bool



def get_config() -> IngestionConfig:
    raw_root = os.getenv("MF_RAW_STORAGE_ROOT", "data/mf_raw_docs")
    return IngestionConfig(
        raw_storage_root=Path(raw_root),
        request_timeout_seconds=float(os.getenv("MF_INGESTION_TIMEOUT_SECONDS", "30")),
        parser_version=os.getenv("MF_PARSER_VERSION", "mf_ingestion_v1"),
        user_agent=os.getenv(
            "MF_INGESTION_USER_AGENT",
            "FundersAIResearchBot/1.0 contact: YOUR_EMAIL_HERE",
        ),
        extractor_mode=os.getenv("MF_EXTRACTOR_MODE", "deterministic").strip().lower(),
        llm_extractor_enabled=os.getenv("MF_LLM_EXTRACTOR_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
        llm_extractor_model=os.getenv("MF_LLM_EXTRACTOR_MODEL", "").strip(),
        source_manifest_path=os.getenv("MF_SOURCE_MANIFEST_PATH", "").strip(),
        r2_endpoint=os.getenv("R2_ENDPOINT", "").strip(),
        r2_access_key_id=os.getenv("R2_ACCESS_KEY_ID", "").strip(),
        r2_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY", "").strip(),
        r2_raw_bucket=os.getenv("R2_RAW_BUCKET", "").strip(),
        r2_cold_bucket=os.getenv("R2_COLD_BUCKET", "").strip(),
        r2_signed_url_ttl_seconds=int(os.getenv("R2_SIGNED_URL_TTL_SECONDS", "300")),
        require_r2_for_raw_storage=os.getenv("MF_REQUIRE_R2_FOR_RAW_STORAGE", "false").strip().lower() in {"1", "true", "yes", "on"},
    )
