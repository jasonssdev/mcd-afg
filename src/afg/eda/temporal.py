"""Within-series temporal (a to d) aggregates and monotonic-trend tests.

A series has exactly four meetings, so a per-series trend test has four points: the exact
Kendall p-value can never go below 2/24 = 0.083 and a per-series result is descriptive,
not inferential. The pooled row (all series together) has more observations but mixes
between-series differences into the ranking; report both and say so.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
from scipy import stats as sps

POOLED_LABEL = "ALL"


def position_aggregates(
    df: pd.DataFrame, columns: Sequence[str], *, position: str = "position_index"
) -> pd.DataFrame:
    """Mean and median of each column per meeting position. Columns: ``variable``,
    ``position_index``, ``n`` (non-missing), ``mean``, ``median``."""
    rows: list[dict[str, object]] = []
    for column in columns:
        values = pd.to_numeric(df[column], errors="coerce")
        grouped = values.groupby(df[position])
        for pos, group in grouped:
            rows.append(
                {
                    "variable": column,
                    position: pos,
                    "n": int(group.count()),
                    "mean": float(group.mean()),
                    "median": float(group.median()),
                }
            )
    return pd.DataFrame(rows, columns=["variable", position, "n", "mean", "median"])


def monotonic_trend(
    df: pd.DataFrame,
    value: str,
    *,
    position: str = "position_index",
    group: str | None = None,
    method: str = "kendall",
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Rank correlation of ``value`` against meeting position, per ``group`` and pooled.

    Columns: ``group`` (``"ALL"`` for the pooled row), ``method``, ``n``, ``statistic``
    (tau or rho), ``p_value``, ``direction`` (``"creciente"``, ``"decreciente"`` or
    ``"sin tendencia"`` by the sign of the statistic) and ``significant`` (``p < alpha``).
    A constant ``value`` yields NaN. Kendall's tau-b is the default because it is exact
    for the tiny n of a single series.
    """
    if method not in {"kendall", "spearman"}:
        raise ValueError(f"método no soportado: {method!r} (use 'kendall' o 'spearman')")
    subsets: list[tuple[str, pd.DataFrame]] = []
    if group is not None:
        subsets.extend((str(key), part) for key, part in df.groupby(group, sort=True))
    subsets.append((POOLED_LABEL, df))

    rows: list[dict[str, object]] = []
    for label, part in subsets:
        pair = part[[position, value]].apply(pd.to_numeric, errors="coerce").dropna()
        stat = p = float("nan")
        if len(pair) > 2 and pair[value].nunique() > 1 and pair[position].nunique() > 1:
            test = sps.kendalltau if method == "kendall" else sps.spearmanr
            result = test(pair[position], pair[value])
            stat, p = float(result[0]), float(result[1])
        if stat > 1e-12:
            direction = "creciente"
        elif stat < -1e-12:
            direction = "decreciente"
        else:
            direction = "sin tendencia"
        rows.append(
            {
                "group": label,
                "method": method,
                "n": len(pair),
                "statistic": stat,
                "p_value": p,
                "direction": direction,
                "significant": bool(p < alpha) if p == p else False,
            }
        )
    return pd.DataFrame(rows)
