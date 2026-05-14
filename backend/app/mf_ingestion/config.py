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



def get_config() -> IngestionConfig:
    raw_root = os.getenv("MF_RAW_STORAGE_ROOT", "data/mf_raw_docs")
    return IngestionConfig(
        raw_storage_root=Path(raw_root),
        request_timeout_seconds=float(os.getenv("MF_INGESTION_TIMEOUT_SECONDS", "30")),
        parser_version=os.getenv("MF_PARSER_VERSION", "mf_ingestion_v1"),
        user_agent=os.getenv(
            "MF_INGESTION_USER_AGENT",
            "MarketMindResearchBot/1.0 contact: YOUR_EMAIL_HERE",
        ),
    )
