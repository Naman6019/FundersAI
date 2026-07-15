from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from app.mf_ingestion.extractors.contracts import NormalizedExtraction, parse_normalized_extraction
from langfuse.decorators import observe, langfuse_context
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser


class LLMExtractionUnavailable(RuntimeError):
    pass


class StrictJSONLLMExtractor:
    def __init__(self, *, enabled: bool, mode: str, model: str) -> None:
        self.enabled = enabled
        self.mode = mode
        self.model = model

    @observe(as_type="generation", name="document_extraction")
    def extract(self, file_path: str, document: dict[str, Any]) -> NormalizedExtraction:
        if not self.enabled or self.mode not in {"deterministic_then_llm", "llm_then_deterministic"}:
            raise LLMExtractionUnavailable("llm_extractor_disabled")

        fixture_path = os.getenv("MF_LLM_EXTRACTOR_FIXTURE_PATH", "").strip()
        if fixture_path:
            payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
            return parse_normalized_extraction(payload)

        api_key, base_url, provider = _resolve_llm_api()
        if not api_key:
            raise LLMExtractionUnavailable("llm_api_key_missing")
        if not self.model:
            raise LLMExtractionUnavailable("mf_llm_extractor_model_missing")

        langfuse_context.update_current_observation(model=self.model)

        text = _extract_document_text(file_path)
        if not text:
            raise LLMExtractionUnavailable("llm_source_text_empty")

        langfuse_context.update_current_observation(
            input={"document_id": document.get("id"), "text": text[:50000]}
        )

        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=_build_llm_headers(api_key, provider),
            timeout=90,
            json={
                "model": self.model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Extract Indian mutual fund factsheet or portfolio data. "
                            "Return only strict JSON with source_document_id, extractor_type, and records. "
                            "Each records item must contain scheme_name, report_month, holdings, aum, "
                            "expense_ratio, benchmark, fund_manager, risk_level, confidence_score, "
                            "and validation_issues. Set extractor_type to llm."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "source_document_id": document.get("id"),
                                "amc_code": document.get("amc_code"),
                                "document_type": document.get("document_type"),
                                "report_month": document.get("report_month"),
                                "text": text[:50000],
                            },
                            default=str,
                        ),
                    },
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        
        usage = payload.get("usage")
        if isinstance(usage, dict):
            langfuse_context.update_current_observation(
                usage={
                    "input": int(usage.get("prompt_tokens") or 0),
                    "output": int(usage.get("completion_tokens") or 0),
                    "total": int(usage.get("total_tokens") or 0),
                }
            )

        content = payload["choices"][0]["message"]["content"]
        extracted = json.loads(content)
        extracted.setdefault("source_document_id", str(document.get("id") or ""))
        extracted["extractor_type"] = "llm"
        return parse_normalized_extraction(extracted)


def _resolve_llm_api() -> tuple[str, str, str]:
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    configured_base_url = os.getenv("MF_LLM_BASE_URL", "").strip()

    if openrouter_key:
        return (
            openrouter_key,
            configured_base_url or "https://openrouter.ai/api/v1",
            "openrouter",
        )
    return (
        openai_key,
        configured_base_url or "https://api.openai.com/v1",
        "openai",
    )


def _build_llm_headers(api_key: str, provider: str) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if provider == "openrouter":
        referer = os.getenv("MF_LLM_HTTP_REFERER", "").strip()
        title = os.getenv("MF_LLM_APP_TITLE", "FundersAI").strip()
        if referer:
            headers["HTTP-Referer"] = referer
        if title:
            headers["X-Title"] = title
    return headers


def _extract_document_text(file_path: str) -> str:
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return PDFTextParser().extract_text(str(path))
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
