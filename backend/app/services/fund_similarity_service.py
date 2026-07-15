from __future__ import annotations

from typing import Any

import numpy as np

from app.repositories.mutual_fund_repository import MutualFundRepository

FEATURE_VERSION = "mf_similarity_numeric_v1"
_FEATURES = (
    ("return_1m", "1M return", False),
    ("return_3m", "3M return", False),
    ("return_6m", "6M return", False),
    ("return_1y", "1Y return", False),
    ("return_3y", "3Y return", False),
    ("return_5y", "5Y return", False),
    ("volatility_1y", "1Y volatility", False),
    ("max_drawdown_1y", "1Y max drawdown", False),
    ("expense_ratio", "expense ratio", False),
    ("aum", "AUM", True),
    ("alpha", "alpha", False),
    ("beta", "beta", False),
    ("sharpe_ratio", "Sharpe ratio", False),
)
_MIN_FEATURES_PER_FUND = 5


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _feature_value(row: dict[str, Any], key: str, log_scale: bool) -> float | None:
    value = _to_float(row.get(key))
    if value is None:
        return None
    if log_scale:
        return float(np.log1p(max(value, 0.0)))
    return value


def _cluster_labels(matrix: np.ndarray) -> np.ndarray:
    """Small deterministic k-means implementation to avoid a new runtime dependency."""
    count = len(matrix)
    if count < 4:
        return np.zeros(count, dtype=int)
    cluster_count = min(4, max(2, int(np.sqrt(count))))
    seed_indexes = np.linspace(0, count - 1, cluster_count, dtype=int)
    centroids = matrix[seed_indexes].copy()
    labels = np.zeros(count, dtype=int)
    for _ in range(30):
        distances = ((matrix[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        next_labels = distances.argmin(axis=1)
        next_centroids = centroids.copy()
        for index in range(cluster_count):
            members = matrix[next_labels == index]
            if len(members):
                next_centroids[index] = members.mean(axis=0)
        if np.array_equal(next_labels, labels) and np.allclose(next_centroids, centroids):
            break
        labels, centroids = next_labels, next_centroids
    return labels


class FundSimilarityService:
    """Explainable peer discovery from stored mutual-fund snapshot data only."""

    def __init__(self, repository: MutualFundRepository | Any = None):
        if repository is None:
            self.repository = MutualFundRepository()
        elif hasattr(repository, "get_fund_by_scheme_code") and hasattr(repository, "list_core_snapshot_rows"):
            self.repository = repository
        else:
            self.repository = MutualFundRepository(repository)

    def find_similar(self, scheme_code: str | int, *, limit: int = 5) -> dict[str, Any]:
        target = self.repository.get_fund_by_scheme_code(scheme_code)
        if not target:
            return {"status": "not_found", "feature_version": FEATURE_VERSION, "peers": []}

        category = str(target.get("category") or "").strip() or None
        rows = self.repository.list_core_snapshot_rows(category=category)
        target_code = str(target.get("scheme_code") or scheme_code)
        if not any(str(row.get("scheme_code")) == target_code for row in rows):
            rows.append(target)

        raw_matrix = np.array(
            [[_feature_value(row, key, log_scale) for key, _label, log_scale in _FEATURES] for row in rows],
            dtype=float,
        )
        valid_counts = np.isfinite(raw_matrix).sum(axis=1)
        eligible = valid_counts >= _MIN_FEATURES_PER_FUND
        target_index = next((index for index, row in enumerate(rows) if str(row.get("scheme_code")) == target_code), None)
        if target_index is None or not eligible[target_index] or int(eligible.sum()) < 3:
            return self._insufficient(target, category, int(valid_counts[target_index]) if target_index is not None else 0)

        eligible_rows = [row for row, is_eligible in zip(rows, eligible) if is_eligible]
        eligible_matrix = raw_matrix[eligible]
        medians = np.nanmedian(eligible_matrix, axis=0)
        filled = np.where(np.isfinite(eligible_matrix), eligible_matrix, medians)
        scale = filled.std(axis=0)
        active_columns = scale > 1e-12
        if not active_columns.any():
            return self._insufficient(target, category, int(valid_counts[target_index]))
        standardized = (filled[:, active_columns] - filled[:, active_columns].mean(axis=0)) / scale[active_columns]
        norms = np.linalg.norm(standardized, axis=1)
        target_eligible_index = next(index for index, row in enumerate(eligible_rows) if str(row.get("scheme_code")) == target_code)
        target_vector = standardized[target_eligible_index]
        denominator = norms * max(float(np.linalg.norm(target_vector)), 1e-12)
        cosine = np.divide(standardized @ target_vector, denominator, out=np.zeros_like(denominator), where=denominator > 1e-12)
        labels = _cluster_labels(standardized)

        target_cluster = int(labels[target_eligible_index])
        candidates = []
        for index, row in enumerate(eligible_rows):
            if index == target_eligible_index:
                continue
            candidates.append(
                {
                    "scheme_code": str(row.get("scheme_code")),
                    "scheme_name": row.get("scheme_name"),
                    "amc_name": row.get("amc_name"),
                    "category": row.get("category"),
                    "risk_level": row.get("risk_level"),
                    "similarity_score": round(float((cosine[index] + 1.0) / 2.0), 4),
                    "same_cluster": int(labels[index]) == target_cluster,
                    "matching_factors": self._matching_factors(
                        raw_matrix[np.flatnonzero(eligible)[target_eligible_index]],
                        raw_matrix[np.flatnonzero(eligible)[index]],
                        standardized[target_eligible_index],
                        standardized[index],
                        active_columns,
                    ),
                }
            )
        candidates.sort(key=lambda item: (not item["same_cluster"], -item["similarity_score"], item["scheme_name"] or ""))
        cluster_size = int((labels == target_cluster).sum())
        target_missing = [label for (key, label, _log), value in zip(_FEATURES, raw_matrix[target_index]) if not np.isfinite(value)]
        return {
            "status": "available",
            "feature_version": FEATURE_VERSION,
            "method": "median_imputation + standardization + cosine_similarity + deterministic_kmeans",
            "peer_scope": {"category": category, "eligible_funds": len(eligible_rows)},
            "target": {
                "scheme_code": target_code,
                "scheme_name": target.get("scheme_name"),
                "category": category,
                "features_available": int(valid_counts[target_index]),
                "missing_features": target_missing,
                "cluster": {"id": target_cluster + 1, "member_count": cluster_size},
            },
            "peers": candidates[: max(1, min(limit, 20))],
            "limitations": [
                "Similarity is a research aid based on stored snapshot metrics, not a performance forecast or recommendation.",
                "Holdings and document-text embeddings are not part of this first numeric feature set.",
            ],
        }

    @staticmethod
    def _matching_factors(
        target_raw: np.ndarray,
        peer_raw: np.ndarray,
        target_standardized: np.ndarray,
        peer_standardized: np.ndarray,
        active_columns: np.ndarray,
    ) -> list[dict[str, Any]]:
        differences = np.abs(target_standardized - peer_standardized)
        original_indexes = np.flatnonzero(active_columns)
        output = []
        for index in np.argsort(differences)[:3]:
            original_index = int(original_indexes[index])
            key, label, _log_scale = _FEATURES[original_index]
            output.append(
                {
                    "feature": key,
                    "label": label,
                    "standardized_distance": round(float(differences[index]), 3),
                    "target_value": round(float(target_raw[original_index]), 4),
                    "peer_value": round(float(peer_raw[original_index]), 4),
                }
            )
        return output

    @staticmethod
    def _insufficient(target: dict[str, Any], category: str | None, feature_count: int) -> dict[str, Any]:
        return {
            "status": "insufficient_data",
            "feature_version": FEATURE_VERSION,
            "target": {
                "scheme_code": str(target.get("scheme_code")),
                "scheme_name": target.get("scheme_name"),
                "category": category,
                "features_available": feature_count,
            },
            "peers": [],
            "limitations": ["At least three category peers and five numeric features per fund are required."],
        }
