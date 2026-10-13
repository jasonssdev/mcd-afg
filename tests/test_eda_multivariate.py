"""Tests for ``afg.eda.multivariate`` (PCA, clustering) and ``afg.eda.temporal``."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from afg.eda.multivariate import cluster_scan, pca_standardized
from afg.eda.temporal import monotonic_trend, position_aggregates


class TestPca:
    def test_two_identical_columns_collapse_to_one_component(self) -> None:
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        res = pca_standardized(pd.DataFrame({"a": x, "b": x}), ["a", "b"])
        assert res.explained_variance_ratio["PC1"] == pytest.approx(1.0)
        assert res.explained_variance_ratio["PC2"] == pytest.approx(0.0, abs=1e-12)
        # loadings are variable-component correlations: both columns equal PC1 up to sign
        assert abs(res.loadings.loc["a", "PC1"]) == pytest.approx(1.0)
        assert res.n_kaiser == 1

    def test_ratios_sum_to_one_and_cumulative_ends_at_one(self, rng: np.random.Generator) -> None:
        df = pd.DataFrame(rng.normal(size=(40, 4)), columns=list("abcd"))
        res = pca_standardized(df, list("abcd"))
        assert res.explained_variance_ratio.sum() == pytest.approx(1.0)
        assert res.cumulative.iloc[-1] == pytest.approx(1.0)
        assert res.scores.shape == (40, 4)

    def test_scores_are_uncorrelated(self, rng: np.random.Generator) -> None:
        df = pd.DataFrame(rng.normal(size=(50, 3)), columns=list("abc"))
        scores = pca_standardized(df, list("abc")).scores
        corr = np.corrcoef(scores.to_numpy().T)
        assert np.allclose(corr, np.eye(3), atol=1e-8)

    def test_incomplete_rows_are_dropped_and_index_is_kept(self) -> None:
        df = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0], "b": [2.0, 1.0, 3.0, 5.0]})
        res = pca_standardized(df, ["a", "b"])
        assert list(res.scores.index) == [0, 1, 3]

    def test_component_count_can_be_limited(self, rng: np.random.Generator) -> None:
        df = pd.DataFrame(rng.normal(size=(30, 4)), columns=list("abcd"))
        res = pca_standardized(df, list("abcd"), n_components=2)
        assert list(res.explained_variance_ratio.index) == ["PC1", "PC2"]


class TestClusterScan:
    @staticmethod
    def _two_blobs() -> pd.DataFrame:
        left = [(0.0, 0.0), (0.1, 0.0), (0.0, 0.1), (0.1, 0.1)]
        right = [(5.0, 5.0), (5.1, 5.0), (5.0, 5.1), (5.1, 5.1)]
        return pd.DataFrame(left + right, columns=["x", "y"])

    def test_recovers_two_well_separated_groups(self) -> None:
        res = cluster_scan(self._two_blobs(), ["x", "y"], k_range=range(2, 5))
        assert res.best_k == 2
        assert res.best_silhouette > 0.7
        assert res.meaningful
        assert res.labels.nunique() == 2
        assert set(res.labels.iloc[:4]) != set(res.labels.iloc[4:])
        assert list(res.table["k"]) == [2, 3, 4]

    def test_unstructured_data_is_not_called_meaningful(self, rng: np.random.Generator) -> None:
        df = pd.DataFrame(rng.uniform(size=(80, 3)), columns=list("abc"))
        res = cluster_scan(df, list("abc"), k_range=range(2, 6))
        assert res.best_silhouette < 0.5
        assert not res.meaningful

    def test_is_deterministic(self, rng: np.random.Generator) -> None:
        df = pd.DataFrame(rng.normal(size=(60, 2)), columns=["a", "b"])
        first = cluster_scan(df, ["a", "b"])
        second = cluster_scan(df, ["a", "b"])
        pd.testing.assert_frame_equal(first.table, second.table)

    def test_ward_algorithm_is_available(self) -> None:
        res = cluster_scan(self._two_blobs(), ["x", "y"], k_range=range(2, 4), algorithm="ward")
        assert res.best_k == 2
        assert res.algorithm == "ward"

    def test_unknown_algorithm_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="algoritmo"):
            cluster_scan(self._two_blobs(), ["x", "y"], algorithm="dbscan")


class TestTemporal:
    @staticmethod
    def _meetings() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "series_id": ["S1"] * 4 + ["S2"] * 4,
                "position_index": [1, 2, 3, 4] * 2,
                "n_decisions": [1, 2, 3, 4, 4, 3, 2, 1],
            }
        )

    def test_position_aggregates_are_hand_checkable(self) -> None:
        out = position_aggregates(self._meetings(), ["n_decisions"]).set_index("position_index")
        assert out.loc[1, "mean"] == pytest.approx(2.5)
        assert out.loc[1, "n"] == 2
        assert out.loc[4, "median"] == pytest.approx(2.5)

    def test_monotone_series_has_tau_one_and_the_exact_p_value(self) -> None:
        out = monotonic_trend(self._meetings(), "n_decisions", group="series_id")
        s1 = out.set_index("group").loc["S1"]
        assert s1["statistic"] == pytest.approx(1.0)
        assert s1["p_value"] == pytest.approx(1 / 12)  # exact Kendall, n = 4
        assert s1["direction"] == "creciente"
        s2 = out.set_index("group").loc["S2"]
        assert s2["statistic"] == pytest.approx(-1.0)
        assert s2["direction"] == "decreciente"

    def test_pooled_row_is_always_present(self) -> None:
        out = monotonic_trend(self._meetings(), "n_decisions", group="series_id")
        pooled = out.set_index("group").loc["ALL"]
        assert pooled["n"] == 8
        assert pooled["statistic"] == pytest.approx(0.0)
        assert pooled["direction"] == "sin tendencia"

    def test_constant_values_give_nan(self) -> None:
        df = pd.DataFrame({"position_index": [1, 2, 3, 4], "v": [5, 5, 5, 5]})
        out = monotonic_trend(df, "v")
        assert math.isnan(out.iloc[0]["statistic"])

    def test_spearman_is_selectable(self) -> None:
        out = monotonic_trend(self._meetings(), "n_decisions", method="spearman")
        assert out.iloc[0]["method"] == "spearman"
