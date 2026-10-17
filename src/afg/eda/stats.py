"""Descriptive statistics, outlier detection, group comparison and correlation helpers.

Everything here is a pure function over a ``DataFrame``: no corpus access, no printing. The
EDA notebook only calls these and plots the result (CONTRIBUTING 7.1).

Conventions
-----------
* Variance, standard deviation and the z-score use the sample estimator (``ddof=1``);
  skewness and excess kurtosis are pandas' bias-corrected sample estimators.
* Rows with missing values are never imputed (decision D3): univariate helpers drop them per
  variable, multivariate ones drop them listwise and mark the row as not scored.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats as sps
from sklearn.covariance import MinCovDet
from sklearn.neighbors import LocalOutlierFactor

MISSING_LABEL = "<missing>"
CORRELATION_METHODS: tuple[str, ...] = ("pearson", "spearman", "kendall")


# --- descriptive statistics ----------------------------------------------------------------


def describe_numeric(
    df: pd.DataFrame, columns: Sequence[str], *, log: bool = False
) -> pd.DataFrame:
    """One row per numeric column with the usual location/spread/shape summary.

    Columns: ``variable``, ``transform`` (``"none"`` or ``"log1p"``), ``n`` (non-missing),
    ``mean``, ``median``, ``mode`` (smallest mode), ``variance``, ``std``, ``min``, ``q1``,
    ``q3``, ``iqr``, ``max``, ``skewness``, ``excess_kurtosis``, ``cv`` (std / mean, NaN
    when the mean is 0). With ``log=True`` every variable is summarised after ``log1p``
    (the variant used to judge whether a right-skewed count behaves better on a log scale).
    """
    rows: list[dict[str, object]] = []
    nan = float("nan")
    for column in columns:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if log:
            values = np.log1p(values)
        n = len(values)
        mean = float(values.mean()) if n else nan
        std = float(values.std(ddof=1)) if n > 1 else nan
        q1 = float(values.quantile(0.25)) if n else nan
        q3 = float(values.quantile(0.75)) if n else nan
        modes = values.mode()
        rows.append(
            {
                "variable": column,
                "transform": "log1p" if log else "none",
                "n": n,
                "mean": mean,
                "median": float(values.median()) if n else nan,
                "mode": float(modes.min()) if len(modes) else nan,
                "variance": float(values.var(ddof=1)) if n > 1 else nan,
                "std": std,
                "min": float(values.min()) if n else nan,
                "q1": q1,
                "q3": q3,
                "iqr": q3 - q1,
                "max": float(values.max()) if n else nan,
                "skewness": float(values.skew()) if n > 2 else nan,
                "excess_kurtosis": float(values.kurt()) if n > 3 else nan,
                "cv": std / mean if n > 1 and mean != 0 else nan,
            }
        )
    return pd.DataFrame(rows)


def describe_categorical(
    df: pd.DataFrame, columns: Sequence[str], *, dropna: bool = False
) -> pd.DataFrame:
    """Counts and shares per category. Columns: ``variable``, ``category``, ``count``,
    ``share``. Missing values appear as :data:`MISSING_LABEL` unless ``dropna`` is set, in
    which case they also leave the denominator."""
    rows: list[dict[str, object]] = []
    for column in columns:
        counts = df[column].value_counts(dropna=dropna)
        total = int(counts.sum())
        for category, count in counts.items():
            label = MISSING_LABEL if pd.isna(category) else category
            rows.append(
                {
                    "variable": column,
                    "category": label,
                    "count": int(count),
                    "share": count / total if total else float("nan"),
                }
            )
    return pd.DataFrame(rows, columns=["variable", "category", "count", "share"])


def rate_by_bin(
    df: pd.DataFrame,
    value: str,
    flag: str,
    bins: Sequence[float],
    *,
    labels: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Share of rows with ``flag`` true inside right-closed bins of ``value``.

    Columns: ``bin``, ``n`` (rows with a non-missing ``value`` in the bin), ``n_true`` and
    ``rate`` (NaN for an empty bin). Rows whose ``value`` is missing or outside ``bins`` are
    left out.
    """
    cut = pd.cut(pd.to_numeric(df[value], errors="coerce"), bins=list(bins), labels=labels)
    grouped = df[flag].astype(bool).groupby(cut, observed=False)
    n = grouped.size()
    n_true = grouped.sum()
    out = pd.DataFrame({"bin": n.index.astype(str), "n": n.to_numpy(dtype=int)})
    out["n_true"] = n_true.to_numpy(dtype=int)
    out["rate"] = np.where(out["n"] > 0, out["n_true"] / out["n"].where(out["n"] > 0), np.nan)
    return out


# --- univariate outliers -------------------------------------------------------------------


def zscore_outliers(
    df: pd.DataFrame, columns: Sequence[str], *, threshold: float = 3.0
) -> pd.DataFrame:
    """Boolean frame: ``|z| > threshold`` per value (sample std; missing and constant
    columns are never flagged)."""
    flags = pd.DataFrame(False, index=df.index, columns=list(columns))
    for column in columns:
        values = pd.to_numeric(df[column], errors="coerce")
        std = values.std(ddof=1)
        if not np.isfinite(std) or std == 0:
            continue
        flags[column] = ((values - values.mean()).abs() / std > threshold).fillna(False)
    return flags


def iqr_outliers(df: pd.DataFrame, columns: Sequence[str], *, k: float = 1.5) -> pd.DataFrame:
    """Boolean frame: value outside ``[Q1 - k*IQR, Q3 + k*IQR]`` (Tukey fences). Missing
    values are never flagged; a zero IQR flags every value different from the quartiles."""
    flags = pd.DataFrame(False, index=df.index, columns=list(columns))
    for column in columns:
        values = pd.to_numeric(df[column], errors="coerce")
        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        flags[column] = ((values < q1 - k * iqr) | (values > q3 + k * iqr)).fillna(False)
    return flags


# --- multivariate outliers -----------------------------------------------------------------


def _standardised_complete_cases(
    df: pd.DataFrame, columns: Sequence[str]
) -> tuple[pd.DataFrame, np.ndarray]:
    """Listwise-complete rows over the non-constant ``columns``, standardised (z-scores)."""
    numeric = df[list(columns)].apply(pd.to_numeric, errors="coerce").dropna()
    numeric = numeric.loc[:, numeric.std(ddof=0) > 0]
    standardised = (numeric - numeric.mean()) / numeric.std(ddof=0)
    return numeric, standardised.to_numpy(dtype=float)


def multivariate_outliers(
    df: pd.DataFrame,
    columns: Sequence[str],
    *,
    contamination: float = 0.05,
    n_neighbors: int = 20,
    chi2_quantile: float = 0.975,
    random_state: int = 0,
) -> pd.DataFrame:
    """Local Outlier Factor and robust (Minimum Covariance Determinant) Mahalanobis
    distance on the standardised numeric ``columns``.

    Columns (index = ``df.index``): ``lof_score`` (negative LOF factor; lower = more
    isolated), ``lof_flag`` (the ``contamination`` fraction most isolated rows),
    ``mahalanobis_sq`` (squared robust distance), ``mcd_flag`` (distance above the
    ``chi2_quantile`` quantile of a chi-square with as many degrees of freedom as retained
    variables). Rows with any missing value are not scored (NaN score, flag ``False``).
    Deterministic: ``random_state`` seeds MCD; LOF has no randomness.
    """
    out = pd.DataFrame(
        {
            "lof_score": np.nan,
            "lof_flag": False,
            "mahalanobis_sq": np.nan,
            "mcd_flag": False,
        },
        index=df.index,
    )
    numeric, matrix = _standardised_complete_cases(df, columns)
    n_rows, n_vars = matrix.shape
    if n_rows < 3 or n_vars == 0:
        return out

    lof = LocalOutlierFactor(n_neighbors=min(n_neighbors, n_rows - 1), contamination=contamination)
    labels = lof.fit_predict(matrix)
    out.loc[numeric.index, "lof_score"] = lof.negative_outlier_factor_
    out.loc[numeric.index, "lof_flag"] = labels == -1

    mcd = MinCovDet(random_state=random_state).fit(matrix)
    distances = mcd.mahalanobis(matrix)
    cutoff = sps.chi2.ppf(chi2_quantile, df=n_vars)
    out.loc[numeric.index, "mahalanobis_sq"] = distances
    out.loc[numeric.index, "mcd_flag"] = distances > cutoff
    return out.astype({"lof_flag": bool, "mcd_flag": bool})


def outlier_summary(
    df: pd.DataFrame,
    columns: Sequence[str],
    *,
    z_threshold: float = 3.0,
    iqr_k: float = 1.5,
    contamination: float = 0.05,
    random_state: int = 0,
) -> pd.DataFrame:
    """Which of the four methods flags each row.

    Columns: ``row`` (original index), ``z_flag`` / ``iqr_flag`` (any variable flagged),
    ``flagged_variables`` (variables flagged by z or IQR, comma separated), ``lof_flag``,
    ``mcd_flag`` and ``n_methods`` (0-4). Whether a flagged row is an error or a genuine
    phenomenon is a judgement the notebook records, not something this table decides.
    """
    z = zscore_outliers(df, columns, threshold=z_threshold)
    iqr = iqr_outliers(df, columns, k=iqr_k)
    multi = multivariate_outliers(
        df, columns, contamination=contamination, random_state=random_state
    )
    either = z | iqr
    summary = pd.DataFrame(
        {
            "row": df.index,
            "z_flag": z.any(axis=1).to_numpy(),
            "iqr_flag": iqr.any(axis=1).to_numpy(),
            "flagged_variables": [
                ", ".join(c for c in either.columns if either.loc[i, c]) for i in df.index
            ],
            "lof_flag": multi["lof_flag"].to_numpy(),
            "mcd_flag": multi["mcd_flag"].to_numpy(),
        },
        index=df.index,
    )
    flag_columns = ["z_flag", "iqr_flag", "lof_flag", "mcd_flag"]
    summary["n_methods"] = summary[flag_columns].sum(axis=1).astype(int)
    return summary


# --- group comparison ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class KruskalResult:
    """Kruskal-Wallis H test with its epsilon-squared effect size."""

    statistic: float
    p_value: float
    epsilon_squared: float
    n: int
    n_groups: int


def kruskal_by_group(df: pd.DataFrame, value: str, group: str) -> KruskalResult:
    """Kruskal-Wallis across the levels of ``group`` for the numeric ``value``.

    Effect size ``epsilon^2 = (H - k + 1) / (n - k)`` (Tomczak and Tomczak, 2014): 0 means
    no rank shift, 1 means complete separation. Fewer than two non-empty groups yields NaN.
    """
    data = df[[value, group]].dropna()
    samples = [g[value].to_numpy(dtype=float) for _, g in data.groupby(group, observed=True)]
    n, k = len(data), len(samples)
    nan = float("nan")
    if k < 2 or n <= k:
        return KruskalResult(nan, nan, nan, n, k)
    try:
        h, p = sps.kruskal(*samples)
    except ValueError:  # all values identical
        return KruskalResult(nan, nan, nan, n, k)
    return KruskalResult(float(h), float(p), float((h - k + 1) / (n - k)), n, k)


def contingency_table(
    df: pd.DataFrame, row: str, col: str, *, margins: bool = False
) -> pd.DataFrame:
    """Cross-tabulation of two categorical columns (missing values excluded)."""
    return pd.crosstab(df[row], df[col], margins=margins)


@dataclass(frozen=True, slots=True)
class Chi2Result:
    """Independence test on a contingency table.

    ``test`` is ``"chi2"`` (Pearson, no continuity correction) or ``"fisher"`` (exact, used
    only for 2x2 tables with an expected count below 5; ``statistic`` is then NaN and
    ``odds_ratio`` is filled). ``cramers_v`` is always computed from the uncorrected
    chi-square so it stays comparable across tables.
    """

    test: str
    statistic: float
    dof: int
    p_value: float
    cramers_v: float
    min_expected: float
    n: int
    odds_ratio: float


def chi2_independence(table: pd.DataFrame, *, min_expected: float = 5.0) -> Chi2Result:
    """Chi-square test of independence with Cramer's V; Fisher exact for small 2x2 tables."""
    kept = table.loc[table.sum(axis=1) > 0, table.sum(axis=0) > 0]
    observed = kept.to_numpy(dtype=float)
    nan = float("nan")
    if min(observed.shape) < 2:
        return Chi2Result("chi2", nan, 0, nan, nan, nan, int(observed.sum()), nan)
    n = int(observed.sum())
    chi2, p, dof, expected = sps.chi2_contingency(observed, correction=False)
    smallest = float(expected.min())
    v = float(np.sqrt(chi2 / (n * (min(observed.shape) - 1))))
    if observed.shape == (2, 2) and smallest < min_expected:
        odds, p_exact = sps.fisher_exact(observed)
        return Chi2Result("fisher", nan, int(dof), float(p_exact), v, smallest, n, float(odds))
    return Chi2Result("chi2", float(chi2), int(dof), float(p), v, smallest, n, nan)


def mosaic_rectangles(table: pd.DataFrame, *, gap: float = 0.01) -> pd.DataFrame:
    """Geometry of a mosaic plot on the unit square, so the notebook can draw it with plain
    matplotlib (no extra dependency).

    Columns of the table split the x axis in proportion to their totals; within each, the
    rows split the y axis in proportion to their share of that column. Output columns:
    ``row``, ``col``, ``count``, ``x``, ``y``, ``width``, ``height`` (``gap`` is removed from
    each rectangle's extent, not from the proportions).
    """
    values = table.to_numpy(dtype=float)
    total = values.sum()
    columns = ["row", "col", "count", "x", "y", "width", "height"]
    if total == 0:
        return pd.DataFrame(columns=columns)
    col_totals = values.sum(axis=0)
    rows: list[dict[str, object]] = []
    x = 0.0
    for j, col_label in enumerate(table.columns):
        width = col_totals[j] / total
        y = 0.0
        for i, row_label in enumerate(table.index):
            height = values[i, j] / col_totals[j] if col_totals[j] else 0.0
            rows.append(
                {
                    "row": row_label,
                    "col": col_label,
                    "count": int(values[i, j]),
                    "x": x,
                    "y": y,
                    "width": max(width - gap, 0.0),
                    "height": max(height - gap, 0.0),
                }
            )
            y += height
        x += width
    return pd.DataFrame(rows, columns=columns)


# --- correlation and collinearity ----------------------------------------------------------


def correlation_table(
    df: pd.DataFrame,
    columns: Sequence[str],
    methods: Sequence[str] = CORRELATION_METHODS,
) -> pd.DataFrame:
    """Long-format correlations for every unordered pair of ``columns`` and each method.

    Columns: ``x``, ``y``, ``method``, ``r``, ``p``, ``n``. Pairwise-complete observations;
    a constant variable gives NaN rather than a warning.
    """
    rows: list[dict[str, object]] = []
    for x_name, y_name in combinations(columns, 2):
        pair = df[[x_name, y_name]].apply(pd.to_numeric, errors="coerce").dropna()
        usable = len(pair) > 2 and pair[x_name].nunique() > 1 and pair[y_name].nunique() > 1
        for method in methods:
            r = p = float("nan")
            if usable:
                a, b = pair[x_name].to_numpy(), pair[y_name].to_numpy()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    if method == "pearson":
                        r, p = (float(v) for v in sps.pearsonr(a, b))
                    elif method == "spearman":
                        r, p = (float(v) for v in sps.spearmanr(a, b))
                    else:
                        r, p = (float(v) for v in sps.kendalltau(a, b))
            rows.append(
                {"x": x_name, "y": y_name, "method": method, "r": r, "p": p, "n": len(pair)}
            )
    return pd.DataFrame(rows, columns=["x", "y", "method", "r", "p", "n"])


def variance_inflation_factors(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """VIF per column: ``1 / (1 - R^2)`` of regressing it on the others (with intercept),
    by ordinary least squares in numpy. Listwise-complete rows. ``inf`` when the column is
    (numerically) a linear combination of the rest. Columns: ``variable``, ``vif``,
    ``r_squared``. Rule of thumb: above 5 (strict) or 10 (lenient) signals collinearity."""
    data = df[list(columns)].apply(pd.to_numeric, errors="coerce").dropna().to_numpy(dtype=float)
    rows: list[dict[str, object]] = []
    for j, name in enumerate(columns):
        y = data[:, j]
        others = np.delete(data, j, axis=1)
        design = np.column_stack([np.ones(len(y)), others])
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        residual = float(((y - design @ coef) ** 2).sum())
        total = float(((y - y.mean()) ** 2).sum())
        r2 = 1.0 - residual / total if total > 0 else float("nan")
        slack = 1.0 - r2
        vif = float("inf") if slack < 1e-10 else 1.0 / slack
        rows.append({"variable": name, "vif": vif, "r_squared": r2})
    return pd.DataFrame(rows, columns=["variable", "vif", "r_squared"])


def benjamini_hochberg(
    p_values: Sequence[float],
    *,
    alpha: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """Adjust p-values with Benjamini-Hochberg FDR control."""
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1:
        raise ValueError("p_values must be one-dimensional")
    if np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("p_values must be finite values between 0 and 1")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")

    order = np.argsort(p)
    ranked = p[order]
    m = len(ranked)

    q_ranked = ranked * m / np.arange(1, m + 1)
    q_ranked = np.minimum.accumulate(q_ranked[::-1])[::-1]
    q_ranked = np.clip(q_ranked, 0.0, 1.0)

    q_values = np.empty_like(q_ranked)
    q_values[order] = q_ranked

    return q_values, q_values <= alpha


def cluster_bootstrap(
    df: pd.DataFrame,
    cluster_col: str,
    statistic: Callable[[pd.DataFrame], float],
    *,
    n_boot: int = 5_000,
    random_state: int = 0,
) -> dict[str, object]:
    """Bootstrap a statistic by resampling complete clusters."""
    work = df.dropna(subset=[cluster_col]).copy()
    clusters = work[cluster_col].drop_duplicates().to_numpy()

    if len(clusters) < 2:
        raise ValueError("at least two clusters are required")
    if n_boot < 1:
        raise ValueError("n_boot must be positive")

    rng = np.random.default_rng(random_state)
    grouped = {key: group.copy() for key, group in work.groupby(cluster_col, sort=False)}
    estimates: list[float] = []

    for _ in range(n_boot):
        sampled = rng.choice(clusters, size=len(clusters), replace=True)
        sample = pd.concat(
            [grouped[key] for key in sampled],
            ignore_index=True,
        )
        estimates.append(float(statistic(sample)))

    distribution = np.asarray(estimates, dtype=float)
    distribution = distribution[np.isfinite(distribution)]

    if distribution.size == 0:
        raise ValueError("bootstrap produced no finite estimates")

    return {
        "estimate": float(statistic(work)),
        "boot_mean": float(np.mean(distribution)),
        "ci_low": float(np.quantile(distribution, 0.025)),
        "ci_high": float(np.quantile(distribution, 0.975)),
        "n_clusters": len(clusters),
        "n_boot_valid": len(distribution),
        "distribution": distribution,
    }
