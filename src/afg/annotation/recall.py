"""Recall of the Task B lexical blocker, estimated from the Task C samples (OE1, manual section 5).

The blocker keeps a pair only if its overlap coefficient clears the operating point; the
rest are *rejected* and never reach a human in Task B. Task C labels a random sample of
rejected pairs per series. Every sampled pair labelled other than ``no_relacionada`` is a
blocker false negative, so the sample false-negative rate estimates the share of real
relations hidden in the rejected population.

## Estimator

Per series ``s``: ``p_s = FN_s / n_s`` is the sample false-negative rate, ``R_s`` the number
of rejected pairs and ``K_s`` the number of *kept* true relations (pairs of the adjudicated
Task B file whose ``final_relation`` is not ``no_relacionada``; for a single-annotator series
without an adjudication file, the annotator's own ``relation``). Then

* missed relations ``M_s = p_s * R_s``;
* blocker recall ``K_s / (K_s + M_s)``.

Pooling (per site, and overall) is a *stratified* estimate: the rate is
``sum(R_s * p_s) / sum(R_s)`` (each series weighted by its rejected population, not by its
sample size), the missed count is ``sum(R_s * p_s)`` and the kept count is ``sum(K_s)``.

## Interval

The manual mentions a bootstrap interval, but a bootstrap of a sample with 0 false negatives
collapses to ``[0, 0]``, which is exactly the case these small samples (n = 50, few or no
hits) are likely to produce. This module uses the Wilson score interval instead, the same one
used elsewhere in the project (:func:`afg.evaluation.metrics.wilson_interval`): it stays
inside ``[0, 1]`` and keeps a non-zero upper bound at 0 hits. For a pooled estimate the
Wilson formula is applied with the Kish effective sample size
``n_eff = 1 / sum((R_s / R)^2 / n_s)``, which equals ``n`` for one series, ``sum(n_s)`` for
equal weights and equal samples, and shrinks as the weights become unequal. The interval is
not corrected for finite populations (the 50 sampled pairs are 20 to 30 % of each rejected
population), so it is slightly conservative.

Interval bounds on the rate are scaled by the rejected population to bound the missed count,
and the missed bounds are propagated to recall (more missed means less recall, so the lower
recall bound uses the upper missed bound). The kept count ``K`` is treated as known; the
interval therefore reflects only the sampling uncertainty of Task C.

All inputs are versioned files; the AMI corpus is not needed. The rejected population is
rebuilt from the blocker's own partition: the cross-meeting pairs implied by the number of
decisions per meeting in ``<series>.decisions.csv`` minus the pairs kept in
``<series>.candidates.csv``.
"""

from __future__ import annotations

import csv
import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist

from afg.annotation.workspace import TaskKind, WorkspacePaths
from afg.domain.relation import RelationType
from afg.shared.csvio import open_csv_reader

__all__ = [
    "RecallEstimate",
    "RecallReport",
    "SeriesRecallCounts",
    "estimate_recall",
    "read_recall_counts",
    "recall_report",
    "rejected_population",
]

_NO_RELATION = RelationType.NO_RELACIONADA.value
_VALID_LABELS = frozenset(r.value for r in RelationType)


@dataclass(frozen=True, slots=True)
class SeriesRecallCounts:
    """The raw counts of one series behind its recall estimate."""

    series_id: str
    n_sampled: int
    n_false_negative: int
    rejected_population: int
    kept_relations: int


@dataclass(frozen=True, slots=True)
class RecallEstimate:
    """Stratified recall estimate for one series, one site or all series together."""

    label: str
    n_series: int
    n_sampled: int
    n_false_negative: int
    rejected_population: int
    kept_relations: int
    false_negative_rate: float
    rate_lower: float
    rate_upper: float
    missed: float
    missed_lower: float
    missed_upper: float
    recall: float
    recall_lower: float
    recall_upper: float
    confidence_level: float


@dataclass(frozen=True, slots=True)
class RecallReport:
    """Per-series, per-site and overall estimates, plus which planned samples were absent."""

    series: tuple[RecallEstimate, ...]
    sites: tuple[RecallEstimate, ...]
    total: RecallEstimate
    missing: tuple[str, ...]
    n_planned: int

    @property
    def n_used(self) -> int:
        return len(self.series)


# --- reading the files ----------------------------------------------------------------------


def _rows(path: Path) -> list[dict[str, str]]:
    with open_csv_reader(path) as handle:
        return list(csv.DictReader(handle))


def rejected_population(series_id: str, *, paths: WorkspacePaths | None = None) -> int:
    """Number of pairs the blocker rejected in ``series_id``.

    Cross-meeting pairs (decisions per meeting taken from ``<series>.decisions.csv``) minus
    the rows of ``<series>.candidates.csv``.
    """
    paths = paths or WorkspacePaths()
    per_meeting = Counter(
        r["meeting_id"] for r in _rows(paths.source(TaskKind.DECISIONS, series_id))
    )
    total = sum(per_meeting.values())
    all_pairs = (total * total - sum(c * c for c in per_meeting.values())) // 2
    return all_pairs - len(_rows(paths.source(TaskKind.CANDIDATES, series_id)))


def _kept_relations(series_id: str, annotator: str, paths: WorkspacePaths) -> int:
    adjudicated = paths.adjudicated(TaskKind.CANDIDATES, series_id)
    if adjudicated.exists():
        labels = [r["final_relation"] for r in _rows(adjudicated)]
    else:
        labels = [
            r["relation"] for r in _rows(paths.target(TaskKind.CANDIDATES, series_id, annotator))
        ]
    return sum(1 for label in labels if label and label != _NO_RELATION)


def read_recall_counts(
    series_id: str, annotator: str = "gv", *, paths: WorkspacePaths | None = None
) -> SeriesRecallCounts | None:
    """Counts of ``<series>.recall-sample.<annotator>.csv``, or ``None`` if it is not there.

    Raises:
        ValueError: a row has no label, a label is outside the closed set, or the sample is
            larger than the rejected population.
    """
    paths = paths or WorkspacePaths()
    sample_path = paths.target(TaskKind.RECALL_SAMPLE, series_id, annotator)
    if not sample_path.exists():
        return None
    labels = [r["relation"].strip() for r in _rows(sample_path)]
    unlabeled = sum(1 for label in labels if not label)
    if unlabeled:
        raise ValueError(
            f"{series_id}: {unlabeled} filas sin etiqueta en {sample_path.name}; la muestra "
            "debe estar completa para estimar el recall."
        )
    unknown = sorted({label for label in labels if label not in _VALID_LABELS})
    if unknown:
        raise ValueError(f"{series_id}: etiquetas fuera del conjunto cerrado: {unknown}.")
    population = rejected_population(series_id, paths=paths)
    if len(labels) > population:
        raise ValueError(
            f"{series_id}: la muestra ({len(labels)}) supera la población de pares "
            f"rechazados ({population})."
        )
    return SeriesRecallCounts(
        series_id=series_id,
        n_sampled=len(labels),
        n_false_negative=sum(1 for label in labels if label != _NO_RELATION),
        rejected_population=population,
        kept_relations=_kept_relations(series_id, annotator, paths),
    )


# --- estimation -----------------------------------------------------------------------------


def _wilson_bounds(p: float, n_eff: float, confidence_level: float) -> tuple[float, float]:
    """Wilson score bounds for proportion ``p`` on a (possibly fractional) sample size."""
    z = NormalDist().inv_cdf(1.0 - (1.0 - confidence_level) / 2.0)
    denominator = 1.0 + z * z / n_eff
    centre = (p + z * z / (2 * n_eff)) / denominator
    half = z * math.sqrt(p * (1 - p) / n_eff + z * z / (4 * n_eff * n_eff)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def estimate_recall(
    counts: Sequence[SeriesRecallCounts],
    *,
    label: str | None = None,
    confidence_level: float = 0.95,
) -> RecallEstimate:
    """Stratified recall estimate over ``counts`` (see the module docstring)."""
    if not counts:
        raise ValueError("estimate_recall requires at least one series.")
    population = sum(c.rejected_population for c in counts)
    weights = [c.rejected_population / population for c in counts]
    rate = sum(w * c.n_false_negative / c.n_sampled for w, c in zip(weights, counts, strict=True))
    n_eff = 1.0 / sum(w * w / c.n_sampled for w, c in zip(weights, counts, strict=True))
    lower, upper = _wilson_bounds(rate, n_eff, confidence_level)
    kept = sum(c.kept_relations for c in counts)

    def recall_given(missed: float) -> float:
        return kept / (kept + missed) if kept + missed > 0 else 1.0

    missed, missed_lower, missed_upper = rate * population, lower * population, upper * population
    return RecallEstimate(
        label=label or "+".join(c.series_id for c in counts),
        n_series=len(counts),
        n_sampled=sum(c.n_sampled for c in counts),
        n_false_negative=sum(c.n_false_negative for c in counts),
        rejected_population=population,
        kept_relations=kept,
        false_negative_rate=rate,
        rate_lower=lower,
        rate_upper=upper,
        missed=missed,
        missed_lower=missed_lower,
        missed_upper=missed_upper,
        recall=recall_given(missed),
        recall_lower=recall_given(missed_upper),
        recall_upper=recall_given(missed_lower),
        confidence_level=confidence_level,
    )


def recall_report(
    series_ids: Sequence[str],
    annotator: str = "gv",
    *,
    paths: WorkspacePaths | None = None,
    confidence_level: float = 0.95,
) -> RecallReport:
    """Per-series, per-site (first two letters of the series id) and overall estimates.

    Series without a sample file are listed in ``missing`` rather than dropped silently;
    ``n_planned`` is ``len(series_ids)`` so the reader sees how many samples were used.
    """
    paths = paths or WorkspacePaths()
    found: list[SeriesRecallCounts] = []
    missing: list[str] = []
    for series_id in series_ids:
        counts = read_recall_counts(series_id, annotator, paths=paths)
        if counts is None:
            missing.append(series_id)
        else:
            found.append(counts)
    if not found:
        raise ValueError("No hay ninguna muestra de recall disponible para estimar.")

    def estimate(group: Sequence[SeriesRecallCounts], label: str) -> RecallEstimate:
        return estimate_recall(group, label=label, confidence_level=confidence_level)

    sites = sorted({c.series_id[:2] for c in found})
    return RecallReport(
        series=tuple(estimate([c], c.series_id) for c in found),
        sites=tuple(
            estimate([c for c in found if c.series_id[:2] == site], site) for site in sites
        ),
        total=estimate(found, "Total"),
        missing=tuple(missing),
        n_planned=len(series_ids),
    )
