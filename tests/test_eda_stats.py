"""Tests for ``afg.eda.stats``: descriptive statistics, outliers, group comparison and
correlation helpers. All fixtures are small synthetic data with hand-checkable answers."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from afg.eda.stats import (
    chi2_independence,
    contingency_table,
    correlation_table,
    describe_categorical,
    describe_numeric,
    iqr_outliers,
    kruskal_by_group,
    mosaic_rectangles,
    multivariate_outliers,
    outlier_summary,
    variance_inflation_factors,
    zscore_outliers,
)


class TestDescribeNumeric:
    def test_hand_checked_values(self) -> None:
        df = pd.DataFrame({"x": [1, 2, 2, 3, 4]})
        row = describe_numeric(df, ["x"]).set_index("variable").loc["x"]
        assert row["n"] == 5
        assert row["mean"] == pytest.approx(2.4)
        assert row["median"] == 2
        assert row["mode"] == 2
        assert row["variance"] == pytest.approx(1.3)
        assert row["std"] == pytest.approx(math.sqrt(1.3))
        assert (row["min"], row["q1"], row["q3"], row["max"]) == (1, 2, 3, 4)
        assert row["iqr"] == 1
        assert row["cv"] == pytest.approx(math.sqrt(1.3) / 2.4)
        assert row["transform"] == "none"

    def test_symmetric_data_has_zero_skewness(self) -> None:
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
        row = describe_numeric(df, ["x"]).iloc[0]
        assert row["skewness"] == pytest.approx(0.0)
        assert row["excess_kurtosis"] == pytest.approx(-1.2)

    def test_log_variant_is_flagged_and_uses_log1p(self) -> None:
        df = pd.DataFrame({"x": [0.0, math.e - 1]})
        row = describe_numeric(df, ["x"], log=True).iloc[0]
        assert row["transform"] == "log1p"
        assert row["max"] == pytest.approx(1.0)

    def test_missing_values_are_ignored(self) -> None:
        df = pd.DataFrame({"x": [1.0, np.nan, 3.0]})
        row = describe_numeric(df, ["x"]).iloc[0]
        assert row["n"] == 2
        assert row["mean"] == pytest.approx(2.0)


class TestDescribeCategorical:
    def test_counts_and_shares_include_missing(self) -> None:
        df = pd.DataFrame({"g": ["a", "a", "b", None]})
        out = describe_categorical(df, ["g"]).set_index("category")
        assert out.loc["a", "count"] == 2
        assert out.loc["a", "share"] == pytest.approx(0.5)
        assert out.loc["<missing>", "count"] == 1

    def test_dropna_excludes_missing_from_the_denominator(self) -> None:
        df = pd.DataFrame({"g": ["a", "a", "b", None]})
        out = describe_categorical(df, ["g"], dropna=True).set_index("category")
        assert "<missing>" not in out.index
        assert out.loc["a", "share"] == pytest.approx(2 / 3)


class TestUnivariateOutliers:
    def test_iqr_flags_the_extreme_value(self) -> None:
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5, 100]})
        flags = iqr_outliers(df, ["x"])
        assert flags["x"].tolist() == [False] * 5 + [True]

    def test_zscore_flags_only_beyond_three_sigma(self) -> None:
        values = [0, 1] * 15 + [1000]
        flags = zscore_outliers(pd.DataFrame({"x": values}), ["x"])
        assert flags["x"].sum() == 1
        assert bool(flags["x"].iloc[-1])

    def test_constant_column_flags_nothing(self) -> None:
        df = pd.DataFrame({"x": [5, 5, 5, 5]})
        assert not zscore_outliers(df, ["x"])["x"].any()
        assert not iqr_outliers(df, ["x"])["x"].any()

    def test_missing_values_are_never_flagged(self) -> None:
        df = pd.DataFrame({"x": [1.0, np.nan, 2.0, 3.0]})
        assert not iqr_outliers(df, ["x"])["x"].iloc[1]


class TestMultivariateOutliers:
    @staticmethod
    def _cloud(rng: np.random.Generator) -> pd.DataFrame:
        points = rng.normal(size=(60, 2))
        points = np.vstack([points, [[9.0, -9.0]]])
        return pd.DataFrame(points, columns=["a", "b"])

    def test_lof_and_mcd_both_flag_the_planted_point(self, rng: np.random.Generator) -> None:
        out = multivariate_outliers(self._cloud(rng), ["a", "b"])
        last = out.iloc[-1]
        assert bool(last["lof_flag"])
        assert bool(last["mcd_flag"])
        assert out["mcd_flag"].sum() < 15

    def test_is_deterministic(self, rng: np.random.Generator) -> None:
        df = self._cloud(rng)
        first = multivariate_outliers(df, ["a", "b"])
        second = multivariate_outliers(df, ["a", "b"])
        pd.testing.assert_frame_equal(first, second)

    def test_rows_with_missing_values_are_not_scored(self, rng: np.random.Generator) -> None:
        df = self._cloud(rng)
        df.loc[0, "a"] = np.nan
        out = multivariate_outliers(df, ["a", "b"])
        assert not bool(out.loc[0, "lof_flag"])
        assert math.isnan(out.loc[0, "mahalanobis_sq"])

    def test_summary_reports_which_methods_flag_each_row(self, rng: np.random.Generator) -> None:
        out = outlier_summary(self._cloud(rng), ["a", "b"])
        last = out.iloc[-1]
        assert bool(last["z_flag"]) and bool(last["iqr_flag"])
        assert bool(last["lof_flag"]) and bool(last["mcd_flag"])
        assert last["n_methods"] == 4
        assert list(out.columns[:1]) == ["row"]


class TestKruskal:
    def test_two_perfectly_separated_groups(self) -> None:
        df = pd.DataFrame({"v": [1, 2, 3, 4, 5, 6], "g": list("aaabbb")})
        res = kruskal_by_group(df, "v", "g")
        assert res.statistic == pytest.approx(27 / 7)
        assert res.epsilon_squared == pytest.approx((27 / 7 - 1) / 4)
        assert (res.n, res.n_groups) == (6, 2)

    def test_single_group_returns_nan(self) -> None:
        df = pd.DataFrame({"v": [1, 2, 3], "g": ["a"] * 3})
        res = kruskal_by_group(df, "v", "g")
        assert math.isnan(res.statistic) and math.isnan(res.p_value)


class TestContingency:
    def test_table_counts_and_margins(self) -> None:
        df = pd.DataFrame({"r": list("aabb"), "c": list("xyxx")})
        table = contingency_table(df, "r", "c")
        assert table.loc["a", "x"] == 1 and table.loc["b", "x"] == 2
        with_margins = contingency_table(df, "r", "c", margins=True)
        assert with_margins.loc["All", "All"] == 4

    def test_independent_table_has_zero_effect(self) -> None:
        res = chi2_independence(pd.DataFrame([[10, 10], [10, 10]]))
        assert res.test == "chi2"
        assert res.statistic == pytest.approx(0.0)
        assert res.cramers_v == pytest.approx(0.0)

    def test_perfect_association_has_cramers_v_one(self) -> None:
        res = chi2_independence(pd.DataFrame([[20, 0], [0, 20]]))
        assert res.statistic == pytest.approx(40.0)
        assert res.cramers_v == pytest.approx(1.0)
        assert res.dof == 1

    def test_fisher_is_used_for_small_2x2(self) -> None:
        res = chi2_independence(pd.DataFrame([[3, 0], [0, 3]]))
        assert res.test == "fisher"
        assert res.p_value == pytest.approx(0.1)
        assert res.min_expected == pytest.approx(1.5)

    def test_larger_tables_keep_chi2_even_with_small_expected_counts(self) -> None:
        res = chi2_independence(pd.DataFrame([[1, 0, 2], [0, 2, 1]]))
        assert res.test == "chi2"

    def test_mosaic_rectangles_tile_the_unit_square(self) -> None:
        rects = mosaic_rectangles(pd.DataFrame([[10, 30], [20, 40]], index=["a", "b"]), gap=0.0)
        assert (rects["width"] * rects["height"]).sum() == pytest.approx(1.0)
        assert len(rects) == 4
        first = rects[(rects["row"] == "a") & (rects["col"] == 0)].iloc[0]
        assert first["width"] == pytest.approx(0.3)
        assert first["height"] == pytest.approx(1 / 3)


class TestCorrelation:
    def test_monotone_nonlinear_relation(self) -> None:
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [1, 4, 9, 16, 25]})
        out = correlation_table(df, ["x", "y"]).set_index("method")
        assert out.loc["spearman", "r"] == pytest.approx(1.0)
        assert out.loc["kendall", "r"] == pytest.approx(1.0)
        assert 0.9 < out.loc["pearson", "r"] < 1.0
        assert (out["n"] == 5).all()

    def test_one_row_per_unordered_pair_and_method(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 1, 4, 3], "c": [4, 3, 2, 1]})
        assert len(correlation_table(df, ["a", "b", "c"])) == 3 * 3

    def test_pairwise_complete_observations(self) -> None:
        df = pd.DataFrame({"x": [1, 2, 3, np.nan], "y": [2, 4, 6, 8]})
        out = correlation_table(df, ["x", "y"], methods=("pearson",))
        assert out.iloc[0]["n"] == 3
        assert out.iloc[0]["r"] == pytest.approx(1.0)


class TestVif:
    def test_orthogonal_columns_have_vif_one(self) -> None:
        df = pd.DataFrame({"a": [1, -1, 1, -1], "b": [1, 1, -1, -1]})
        out = variance_inflation_factors(df, ["a", "b"]).set_index("variable")
        assert out.loc["a", "vif"] == pytest.approx(1.0)

    def test_duplicated_column_has_infinite_vif(self) -> None:
        df = pd.DataFrame({"a": [1.0, 2, 3, 4, 5], "b": [1.0, 2, 3, 4, 5], "c": [1, 0, 1, 0, 1]})
        out = variance_inflation_factors(df, ["a", "b", "c"]).set_index("variable")
        assert math.isinf(out.loc["a", "vif"])
        assert math.isfinite(out.loc["c", "vif"])

    def test_known_vif_from_r_squared(self) -> None:
        # y = x + e with e orthogonal to x and centred: R^2 = var(x) / (var(x) + var(e)).
        x = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        e = np.array([1.0, -1.0, 0.0, -1.0, 1.0])
        e = e - e.mean()
        e = e - (e @ x) / (x @ x) * x
        df = pd.DataFrame({"x": x, "y": x + e})
        r2 = np.corrcoef(df["x"], df["y"])[0, 1] ** 2
        out = variance_inflation_factors(df, ["x", "y"]).set_index("variable")
        assert out.loc["x", "vif"] == pytest.approx(1 / (1 - r2))
