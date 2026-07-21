from __future__ import annotations

from types import SimpleNamespace

from app.services.asset_resolver import AssetResolver, ResolverCache
from app.services.asset_resolver import _fund_search_pattern as resolver_search_pattern
from app.services.chat_service import _fund_search_pattern as chat_search_pattern


class _FakeQuery:
    def __init__(self, root, table_name: str):
        self.root = root
        self.table_name = table_name
        self.ilike_filters: list[tuple[str, str]] = []
        self.eq_filters: list[tuple[str, object]] = []
        self.limit_value = None
        self.order_by: list[tuple[str, bool]] = []

    def select(self, _fields: str, count=None):
        self.root.calls.append((self.table_name, "select"))
        return self

    def ilike(self, key: str, pattern: str):
        self.ilike_filters.append((key, pattern))
        return self

    def eq(self, key: str, value):
        self.eq_filters.append((key, value))
        return self

    def order(self, key: str, desc=False):
        self.order_by.append((key, bool(desc)))
        return self

    def limit(self, value: int):
        self.limit_value = value
        return self

    def execute(self):
        rows = list(self.root.tables.get(self.table_name, []))
        for key, pattern in self.ilike_filters:
            needles = [part.lower() for part in pattern.split("%") if part]
            rows = [row for row in rows if all(needle in str(row.get(key) or "").lower() for needle in needles)]
        for key, value in self.eq_filters:
            rows = [row for row in rows if str(row.get(key)) == str(value)]
        for key, desc in reversed(self.order_by):
            rows.sort(key=lambda row: row.get(key) or "", reverse=desc)
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return SimpleNamespace(data=rows)


class _FakeSupabase:
    def __init__(self, tables: dict[str, list[dict]]):
        self.tables = tables
        self.calls: list[tuple[str, str]] = []

    def table(self, name: str):
        return _FakeQuery(self, name)


def _resolver(rows: list[dict]) -> tuple[AssetResolver, _FakeSupabase]:
    fake = _FakeSupabase({"mutual_fund_core_snapshot": rows, "mutual_funds": []})
    return AssetResolver(fake, cache=ResolverCache(ttl_seconds=60, max_size=10)), fake


def test_empty_and_wildcard_only_fund_searches_do_not_create_match_all_patterns():
    for value in ("", "   ", "%", "___", "fund growth"):
        assert resolver_search_pattern(value) is None
        assert chat_search_pattern(value) is None


def test_resolver_maps_ppfas_typo_to_high_confidence_fund_and_caches():
    resolver, fake = _resolver([
        {
            "scheme_code": "122639",
            "scheme_name": "Parag Parikh Flexi Cap Fund Direct Growth",
            "amc_name": "PPFAS Mutual Fund",
        }
    ])

    first = resolver.resolve("Paras Flexi Cap", asset_type="mutual_fund")
    second = resolver.resolve("Paras Flexi Cap", asset_type="mutual_fund")

    assert first.coverage_status == "supported"
    assert first.resolved_name == "Parag Parikh Flexi Cap Fund Direct Growth"
    assert first.confidence >= 0.88
    assert "candidates" not in first.client_payload()
    assert second.cache_hit is True
    assert len(fake.calls) == 1


def test_resolver_maps_axis_typo_to_high_confidence_fund():
    resolver, _fake = _resolver([
        {
            "scheme_code": "axis-101",
            "scheme_name": "Axis Flexi Cap Fund Direct Growth",
            "amc_name": "Axis Mutual Fund",
        }
    ])

    result = resolver.resolve("Axs flexi", asset_type="mutual_fund")

    assert result.coverage_status == "supported"
    assert result.resolved_name == "Axis Flexi Cap Fund Direct Growth"
    assert result.amc == "AXIS"
    assert result.confidence >= 0.88


def test_resolver_maps_nippon_small_cap_to_supported_fund():
    resolver, _fake = _resolver([
        {
            "scheme_code": "119332",
            "scheme_name": "Nippon India Small Cap Fund - Direct Plan - Growth",
            "amc_name": "Nippon India Mutual Fund",
        }
    ])

    result = resolver.resolve("Nippon small cap", asset_type="mutual_fund")

    assert result.coverage_status == "supported"
    assert result.resolved_name == "Nippon India Small Cap Fund - Direct Plan - Growth"
    assert result.amc == "NIPPON"
    assert result.confidence >= 0.88


def test_resolver_maps_hdfc_mid_cpa_typo_to_mid_cap_fund():
    resolver, _fake = _resolver([
        {
            "scheme_code": "hdfc-mid-101",
            "scheme_name": "HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth",
            "amc_name": "HDFC Mutual Fund",
        }
    ])

    result = resolver.resolve("Hdfc mid cpa", asset_type="mutual_fund")

    assert result.coverage_status == "supported"
    assert result.resolved_name == "HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth"
    assert result.id == "hdfc-mid-101"
    assert result.confidence >= 0.88


def test_resolver_prefers_growth_variant_over_idcw():
    resolver, _fake = _resolver([
        {
            "scheme_code": "axis-idcw",
            "scheme_name": "Axis Large Cap Fund - Direct Plan - IDCW",
            "amc_name": "Axis Mutual Fund",
        },
        {
            "scheme_code": "axis-growth",
            "scheme_name": "Axis Large Cap Fund - Direct Plan - Growth",
            "amc_name": "Axis Mutual Fund",
        },
    ])

    result = resolver.resolve("Axis Large cap", asset_type="mutual_fund")

    assert result.coverage_status == "supported"
    assert result.id == "axis-growth"


def test_resolver_rejects_unsupported_amc_without_db_lookup():
    resolver, fake = _resolver([])

    result = resolver.resolve("Quant Small Cap Fund", asset_type="mutual_fund")

    assert result.coverage_status == "unsupported"
    assert result.confidence == 0
    assert fake.calls == []


def test_resolver_keeps_motilal_parser_only_until_coverage_is_promoted():
    resolver, fake = _resolver([
        {
            "scheme_code": "motilal-101",
            "scheme_name": "Motilal Oswal Midcap Fund Direct Growth",
            "amc_name": "Motilal Oswal Mutual Fund",
        }
    ])

    result = resolver.resolve("Motilal Midcap Fund", asset_type="mutual_fund")

    assert result.coverage_status == "unsupported"
    assert result.confidence == 0
    assert fake.calls == []


def test_resolver_does_not_treat_quantify_as_quant_amc():
    resolver, fake = _resolver([])

    result = resolver.resolve("quantify HDFC Flexi Cap risk", asset_type="mutual_fund")

    assert result.coverage_status != "unsupported"
    assert fake.calls


def test_resolver_returns_medium_candidates_for_ambiguous_query():
    resolver, _fake = _resolver([
        {
            "scheme_code": "118955",
            "scheme_name": "HDFC Large Cap Fund Direct Growth",
            "amc_name": "HDFC Mutual Fund",
        },
        {
            "scheme_code": "118956",
            "scheme_name": "HDFC Large and Mid Cap Fund Direct Growth",
            "amc_name": "HDFC Mutual Fund",
        },
    ])

    result = resolver.resolve("HDFC Cap Fund", asset_type="mutual_fund")

    assert result.coverage_status == "ambiguous"
    assert 0.68 <= result.confidence < 0.88
    assert len(result.client_payload()["candidates"]) >= 1
