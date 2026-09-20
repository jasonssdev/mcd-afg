"""Metrics for OE2 (extraction) and OE3 (answer quality), thesis section 5.6.

Relation label accuracy and relation *direction* accuracy are reported separately (thesis
section 3, OE2 and hypothesis H3): a system can get the relation type right while
inverting which decision relates to which, and that failure mode must be countable on its
own, not averaged away inside a single "relation accuracy" number.

Every result thesis section 5.0 requires a bootstrap confidence interval; :func:`bootstrap_ci`
is the single implementation of that resampling procedure used across the codebase.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import NormalDist

from sklearn.metrics import cohen_kappa_score

from afg.domain.relation import TemporalRelation


def precision_recall_f1(
    true_positives: int, false_positives: int, false_negatives: int
) -> tuple[float, float, float]:
    """Precision, recall, and F1 from raw counts.

    Returns 0.0 for precision/recall/F1 when their denominator is zero, rather than
    raising -- an extractor that predicts nothing has precision 0 by convention here, not
    an undefined value that forces every caller to special-case it.
    """
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0.0
    )
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    """Cohen's kappa between two annotators' labels over the same items, in order.

    Delegates to scikit-learn; this project does not reimplement the statistic.
    """
    if len(labels_a) != len(labels_b):
        raise ValueError("labels_a and labels_b must have the same length.")
    if not labels_a:
        raise ValueError("cohen_kappa is undefined for an empty label sequence.")
    return float(cohen_kappa_score(list(labels_a), list(labels_b)))


def relation_label_accuracy(predicted: Sequence[str], reference: Sequence[str]) -> float:
    """Fraction of matched relation pairs where the predicted label equals the reference.

    ``predicted`` and ``reference`` must already be aligned (same length, index ``i`` in
    both refers to the same matched pair) -- alignment itself is
    :mod:`afg.evaluation.alignment`'s job, not this function's.
    """
    if len(predicted) != len(reference):
        raise ValueError("predicted and reference must have the same length.")
    if not predicted:
        raise ValueError("relation_label_accuracy is undefined for an empty sequence.")
    correct = sum(1 for p, r in zip(predicted, reference, strict=True) if p == r)
    return correct / len(predicted)


def relation_direction_accuracy(
    matched_relations: Sequence[tuple[TemporalRelation, TemporalRelation]],
) -> float:
    """Fraction of matched relation pairs where the predicted direction is not inverted.

    Thesis hypothesis H3: direction is measured separately from relation type. A pair
    counts as correct only if both ``source_decision_id`` and ``target_decision_id`` match
    the reference exactly -- a relation whose type is right but whose source/target are
    swapped (:meth:`TemporalRelation.inverted`) counts as a direction failure.
    """
    if not matched_relations:
        raise ValueError("relation_direction_accuracy is undefined for an empty sequence.")
    correct = sum(
        1
        for predicted, reference in matched_relations
        if predicted.source_decision_id == reference.source_decision_id
        and predicted.target_decision_id == reference.target_decision_id
    )
    return correct / len(matched_relations)


def recall_at_k(retrieved_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of ``relevant_ids`` found within the top ``k`` of ``retrieved_ids``.

    Thesis section 5.4: retained only to evaluate the retrieval stage within C1 and C2,
    where a ranking actually exists -- never used as a primary extraction-quality metric.
    """
    if k <= 0:
        raise ValueError("k must be positive.")
    if not relevant_ids:
        raise ValueError("recall_at_k is undefined when relevant_ids is empty.")
    top_k = set(retrieved_ids[:k])
    found = len(top_k & relevant_ids)
    return found / len(relevant_ids)


@dataclass(frozen=True, slots=True)
class BootstrapCI:
    point_estimate: float
    lower: float
    upper: float
    confidence_level: float
    n_resamples: int


def bootstrap_ci(
    values: Sequence[float],
    statistic: Callable[[Sequence[float]], float],
    n: int = 10_000,
    seed: int | None = None,
    confidence_level: float = 0.95,
) -> BootstrapCI:
    """Percentile bootstrap confidence interval for ``statistic`` over ``values``.

    Thesis section 5.0: every reported result carries a bootstrap CI, and no conclusion
    relies on differences that fall within them. ``statistic`` defaults to no assumption
    about what is being estimated (mean, F1, accuracy, ...) -- pass any reducer from a
    sequence of floats to a float.
    """
    if not values:
        raise ValueError("bootstrap_ci is undefined for an empty values sequence.")
    if not (0.0 < confidence_level < 1.0):
        raise ValueError("confidence_level must be strictly between 0 and 1.")

    rng = random.Random(seed)
    n_values = len(values)
    point_estimate = statistic(values)

    resampled_statistics: list[float] = []
    for _ in range(n):
        resample = [values[rng.randrange(n_values)] for _ in range(n_values)]
        resampled_statistics.append(statistic(resample))

    resampled_statistics.sort()
    alpha = 1.0 - confidence_level
    lower_index = max(0, int((alpha / 2) * n))
    upper_index = min(n - 1, int((1 - alpha / 2) * n))

    return BootstrapCI(
        point_estimate=point_estimate,
        lower=resampled_statistics[lower_index],
        upper=resampled_statistics[upper_index],
        confidence_level=confidence_level,
        n_resamples=n,
    )


@dataclass(frozen=True, slots=True)
class ProportionCI:
    successes: int
    trials: int
    point_estimate: float
    lower: float
    upper: float
    confidence_level: float

    def scaled_to(self, population: int) -> tuple[float, float, float]:
        """Project (point, lower, upper) onto a population of ``population`` items.

        Useful for turning an observed rate into an expected count, e.g. "45.5% of 11
        adjudicated candidates were real relations, so of 81 evaluation candidates expect
        ~37, CI [17, 58]". The projection inherits every limitation of the estimate --
        it does not add information.
        """
        return (
            self.point_estimate * population,
            self.lower * population,
            self.upper * population,
        )


def wilson_interval(
    successes: int, trials: int, confidence_level: float = 0.95
) -> ProportionCI:
    """Wilson score interval for a binomial proportion.

    Used instead of the normal (Wald) approximation because the samples this project
    estimates proportions from are small -- the first positive-rate estimate had n = 11 --
    and Wald is badly behaved there: it can produce bounds outside [0, 1] and collapses to
    zero width when the observed count is 0 or n. Wilson stays inside [0, 1] and keeps a
    sensible width at the extremes.

    The z value is derived from ``confidence_level`` via the normal quantile, so 0.95 gives
    the familiar 1.96 without hard-coding it.
    """
    if trials <= 0:
        raise ValueError("wilson_interval requires trials > 0.")
    if not (0 <= successes <= trials):
        raise ValueError("successes must satisfy 0 <= successes <= trials.")
    if not (0.0 < confidence_level < 1.0):
        raise ValueError("confidence_level must be strictly between 0 and 1.")

    z = NormalDist().inv_cdf(1.0 - (1.0 - confidence_level) / 2.0)
    p = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    half_width = (
        z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    )
    return ProportionCI(
        successes=successes,
        trials=trials,
        point_estimate=p,
        lower=max(0.0, centre - half_width),
        upper=min(1.0, centre + half_width),
        confidence_level=confidence_level,
    )
