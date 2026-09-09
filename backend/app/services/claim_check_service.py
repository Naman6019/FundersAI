"""Read-only Fund Truth Check orchestration for Phase 1."""
from __future__ import annotations

from datetime import datetime, timezone
import hmac
import os
import time
from typing import Any

from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.asset_resolver import AssetResolution, AssetResolver
from app.services.claim_check_contract import AtomicClaim, ClaimCheckRequest, ClaimCheckResponse, ResolvedEntity, needs_definition_claim
from app.services.claim_evaluators import ClaimEvaluators
from app.services.claim_parser import ClaimParser, ParsedClaim


CLAIM_CHECK_INTERNAL_PROXY_KEY = os.getenv("CLAIM_CHECK_INTERNAL_PROXY_KEY", "").strip()


def trusted_claim_check_proxy(value: str | None) -> bool:
    """Keep the read-only backend route private until the Phase 2 BFF exists."""
    configured_key = os.getenv("CLAIM_CHECK_INTERNAL_PROXY_KEY", CLAIM_CHECK_INTERNAL_PROXY_KEY).strip()
    return bool(
        configured_key
        and value
        and hmac.compare_digest(value, configured_key)
    )


class ClaimCheckCache:
    """Small process-local cache for identical read-only checks."""

    def __init__(self, *, ttl_seconds: int = 300, max_size: int = 128):
        self.ttl_seconds, self.max_size = ttl_seconds, max_size
        self._items: dict[str, tuple[float, ClaimCheckResponse]] = {}

    def get(self, key: str) -> ClaimCheckResponse | None:
        item = self._items.get(key)
        if not item:
            return None
        expires_at, response = item
        if expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None
        return response.model_copy(deep=True)

    def set(self, key: str, response: ClaimCheckResponse) -> None:
        if len(self._items) >= self.max_size:
            self._items.pop(min(self._items.items(), key=lambda item: item[1][0])[0], None)
        self._items[key] = (time.monotonic() + self.ttl_seconds, response.model_copy(deep=True))


class ClaimCheckService:
    def __init__(self, repository: Any = None, *, parser: ClaimParser | None = None, resolver: AssetResolver | None = None, evaluators: ClaimEvaluators | None = None, cache: ClaimCheckCache | None = None):
        self.repository = repository if isinstance(repository, MutualFundRepository) else MutualFundRepository(repository)
        self.parser = parser or ClaimParser()
        self.resolver = resolver or AssetResolver(self.repository)
        self.evaluators = evaluators or ClaimEvaluators(self.repository)
        self.cache = cache or ClaimCheckCache()

    @staticmethod
    def _key(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _entity_payload(resolution: AssetResolution) -> ResolvedEntity:
        return ResolvedEntity(input=resolution.input, scheme_code=str(resolution.id) if resolution.id is not None else None, scheme_name=resolution.resolved_name, amc_name=resolution.amc, confidence=resolution.confidence, resolution_status=resolution.coverage_status, candidates=[item.client_payload() for item in resolution.candidates[:3]])

    def _resolve(self, parsed: list[ParsedClaim]) -> tuple[dict[str, AssetResolution], list[ResolvedEntity]]:
        inputs = list(dict.fromkeys(entity for claim in parsed for entity in claim.entity_inputs if entity))
        resolved = {item: self.resolver.resolve(item, asset_type="mutual_fund") for item in inputs}
        return resolved, [self._entity_payload(item) for item in resolved.values()]

    def check(self, request: ClaimCheckRequest | str, *, use_cache: bool = True) -> ClaimCheckResponse:
        input_text = request.input if isinstance(request, ClaimCheckRequest) else str(request)
        if use_cache:
            cached = self.cache.get(self._key(input_text))
            if cached:
                return cached
        parsed = self.parser.parse(input_text)
        resolved, entities = self._resolve(parsed)
        claims: list[AtomicClaim] = []
        for item in parsed:
            if item.subject_term:
                claims.append(needs_definition_claim(item.statement, item.subject_term))
            else:
                claims.append(self.evaluators.evaluate(item, [resolved[key] for key in item.entity_inputs if key in resolved]))
        response = ClaimCheckResponse(input=input_text, resolved_entities=entities, claims=claims, generated_at=datetime.now(timezone.utc).isoformat())
        if use_cache:
            self.cache.set(self._key(input_text), response)
        return response
