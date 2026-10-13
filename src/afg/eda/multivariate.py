"""Standardised PCA and silhouette-scanned clustering.

Both work on z-scored numeric columns and on listwise-complete rows (no imputation,
decision D3). Everything is deterministic: ``random_state`` is fixed by default.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def _complete_numeric(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    return df[list(columns)].apply(pd.to_numeric, errors="coerce").dropna()


@dataclass(frozen=True, slots=True)
class PcaResult:
    """Standardised PCA outcome.

    ``explained_variance_ratio`` and ``cumulative`` are indexed ``PC1..PCk``; ``loadings``
    has the original variables as rows and components as columns (eigenvectors scaled by
    the square root of the eigenvalue, i.e. correlations between variable and component);
    ``scores`` keeps the original row index of the complete cases; ``n_kaiser`` is the
    number of components with eigenvalue > 1 (Kaiser criterion).
    """

    explained_variance_ratio: pd.Series
    cumulative: pd.Series
    loadings: pd.DataFrame
    scores: pd.DataFrame
    n_kaiser: int


def pca_standardized(
    df: pd.DataFrame, columns: Sequence[str], *, n_components: int | None = None
) -> PcaResult:
    """PCA on the z-scored ``columns`` (correlation-matrix PCA)."""
    data = _complete_numeric(df, columns)
    # ddof=1 z-scores make the covariance equal to the correlation matrix, so eigenvalues sum
    # to the number of variables (Kaiser) and loadings are variable-component correlations.
    scaled = ((data - data.mean()) / data.std(ddof=1)).to_numpy(dtype=float)
    pca = PCA(n_components=n_components, random_state=0).fit(scaled)
    names = [f"PC{i + 1}" for i in range(pca.n_components_)]
    ratio = pd.Series(pca.explained_variance_ratio_, index=names)
    loadings = pd.DataFrame(
        pca.components_.T * (pca.explained_variance_**0.5), index=list(columns), columns=names
    )
    scores = pd.DataFrame(pca.transform(scaled), index=data.index, columns=names)
    return PcaResult(
        explained_variance_ratio=ratio,
        cumulative=ratio.cumsum(),
        loadings=loadings,
        scores=scores,
        n_kaiser=int((pca.explained_variance_ > 1.0).sum()),
    )


@dataclass(frozen=True, slots=True)
class ClusterScanResult:
    """Silhouette scan over ``k``.

    ``table`` has ``k`` and ``silhouette`` (plus ``inertia`` for k-means); ``labels`` are the
    cluster labels at ``best_k`` indexed like the complete cases; ``interpretation`` applies
    the Kaufman and Rousseeuw (1990) bands to the best silhouette; ``meaningful`` is true
    only for a reasonable structure (best silhouette above 0.5).
    """

    algorithm: str
    table: pd.DataFrame
    best_k: int
    best_silhouette: float
    labels: pd.Series
    interpretation: str
    meaningful: bool


def _interpret(silhouette: float) -> str:
    if silhouette > 0.70:
        return "estructura fuerte"
    if silhouette > 0.50:
        return "estructura razonable"
    if silhouette > 0.25:
        return "estructura débil, posiblemente artificial"
    return "sin estructura sustancial"


def cluster_scan(
    df: pd.DataFrame,
    columns: Sequence[str],
    *,
    k_range: range = range(2, 7),
    algorithm: str = "kmeans",
    random_state: int = 0,
) -> ClusterScanResult:
    """Cluster the z-scored ``columns`` for each ``k`` and report the silhouette.

    ``algorithm`` is ``"kmeans"`` (``n_init=10``, fixed seed) or ``"ward"``
    (agglomerative, Ward linkage; deterministic by construction). The question the table
    answers is whether any ``k`` yields a structure better than noise, not which ``k`` is
    "right": read ``interpretation`` before reading the labels.
    """
    if algorithm not in {"kmeans", "ward"}:
        raise ValueError(f"algoritmo no soportado: {algorithm!r} (use 'kmeans' o 'ward')")
    data = _complete_numeric(df, columns)
    scaled = StandardScaler().fit_transform(data.to_numpy(dtype=float))

    rows: list[dict[str, float | int]] = []
    best: tuple[float, int, list[int]] | None = None
    for k in k_range:
        if algorithm == "kmeans":
            model = KMeans(n_clusters=k, n_init=10, random_state=random_state).fit(scaled)
            labels = model.labels_
            row: dict[str, float | int] = {"k": k, "inertia": float(model.inertia_)}
        else:
            labels = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(scaled)
            row = {"k": k}
        score = float(silhouette_score(scaled, labels))
        row["silhouette"] = score
        rows.append(row)
        if best is None or score > best[0]:
            best = (score, k, [int(v) for v in labels])

    assert best is not None, "k_range must not be empty"
    best_score, best_k, best_labels = best
    return ClusterScanResult(
        algorithm=algorithm,
        table=pd.DataFrame(rows),
        best_k=best_k,
        best_silhouette=best_score,
        labels=pd.Series(best_labels, index=data.index, name="cluster"),
        interpretation=_interpret(best_score),
        meaningful=best_score > 0.5,
    )
