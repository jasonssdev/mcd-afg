"""Calibration metrics and decision rule for choosing the judge model (thesis section 5.7).

Section 5.7 reports judge-human concordance and discards automatic judging when it is low.
This module is the pure arithmetic behind that choice: it compares judge verdicts with
human labels and applies thresholds that were fixed in ``config/experiments.toml``
(``[judge.calibration]``) before any candidate was run. Nothing here calls a model; the
notebook reads these numbers and never recomputes them.

A verdict slot that is ``None`` means the judge produced no usable output for that item
(a :class:`afg.evaluation.judge.JudgeFailure`). Agreement metrics skip such slots; the
consistency metrics count them as inconsistent, because an unusable output is not a stable
verdict.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from afg.evaluation.judge import JudgeFailure, JudgeVerdict
from afg.evaluation.metrics import BootstrapCI, bootstrap_ci, cohen_kappa
from afg.shared.config import load_experiments_config

Label = bool | None


@dataclass(frozen=True, slots=True)
class CalibrationThresholds:
    """The pre-registered acceptance thresholds, as read from the experiments config."""

    min_kappa_correct: float
    min_position_consistency: float
    min_seed_consistency: float
    min_e4_accuracy: float
    min_json_valid_rate: float
    max_verbosity_flip_rate: float
    seeds: tuple[int, ...]


def load_thresholds() -> CalibrationThresholds:
    """Read ``[judge.calibration]``; the single source of the thresholds."""
    section = load_experiments_config()["judge"]["calibration"]
    return CalibrationThresholds(
        min_kappa_correct=float(section["min_kappa_correct"]),
        min_position_consistency=float(section["min_position_consistency"]),
        min_seed_consistency=float(section["min_seed_consistency"]),
        min_e4_accuracy=float(section["min_e4_accuracy"]),
        min_json_valid_rate=float(section["min_json_valid_rate"]),
        max_verbosity_flip_rate=float(section["max_verbosity_flip_rate"]),
        seeds=tuple(int(seed) for seed in section["seeds"]),
    )


# --- agreement with human labels ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FieldAgreement:
    """Cohen's kappa and raw accuracy of one verdict field against its human labels."""

    kappa: float
    accuracy: float
    n: int


def _comparable_pairs(judge: Sequence[Label], human: Sequence[Label]) -> list[tuple[bool, bool]]:
    if len(judge) != len(human):
        raise ValueError("judge and human labels must have the same length.")
    return [(j, h) for j, h in zip(judge, human, strict=True) if j is not None and h is not None]


def _kappa(pairs: Sequence[tuple[bool, bool]]) -> float:
    judge = [str(j) for j, _ in pairs]
    human = [str(h) for _, h in pairs]
    if judge == human:
        # sklearn returns nan when both raters use a single class; identical labels are
        # perfect agreement, not an undefined statistic.
        return 1.0
    kappa = cohen_kappa(judge, human)
    return 0.0 if kappa != kappa else kappa  # nan: one rater constant, chance-level


def field_agreement(judge: Sequence[Label], human: Sequence[Label]) -> FieldAgreement:
    """Kappa and accuracy over the items where both the judge and the humans have a label.

    This also serves the optional ``citation_correct`` field: items without a value on
    either side are simply dropped.
    """
    pairs = _comparable_pairs(judge, human)
    if not pairs:
        raise ValueError("field_agreement needs at least one item labeled on both sides.")
    accuracy = sum(1 for j, h in pairs if j == h) / len(pairs)
    return FieldAgreement(kappa=_kappa(pairs), accuracy=accuracy, n=len(pairs))


def negative_class_recall(judge: Sequence[Label], human: Sequence[Label]) -> float:
    """Share of human-labeled negatives (``False``) that the judge also labeled negative."""
    pairs = _comparable_pairs(judge, human)
    negatives = [(j, h) for j, h in pairs if not h]
    if not negatives:
        raise ValueError("negative_class_recall needs at least one human negative.")
    return sum(1 for j, _ in negatives if not j) / len(negatives)


def kappa_confidence_interval(
    judge: Sequence[Label],
    human: Sequence[Label],
    *,
    n_resamples: int | None = None,
) -> BootstrapCI:
    """Percentile bootstrap CI for kappa, resampling items.

    Reuses :func:`afg.evaluation.metrics.bootstrap_ci`. Resamples, confidence level and
    seed come from ``config/experiments.toml``; ``n_resamples`` overrides only the count.
    """
    pairs = _comparable_pairs(judge, human)
    if not pairs:
        raise ValueError("kappa_confidence_interval needs at least one comparable item.")
    config = load_experiments_config()
    evaluation = config["evaluation"]

    def kappa_of(indices: Sequence[float]) -> float:
        return _kappa([pairs[int(i)] for i in indices])

    return bootstrap_ci(
        [float(i) for i in range(len(pairs))],
        kappa_of,
        n=n_resamples if n_resamples is not None else int(evaluation["bootstrap_resamples"]),
        seed=int(config["shared_budget"]["seed"]),
        confidence_level=float(evaluation["bootstrap_confidence_level"]),
    )


def stratum_accuracy(
    strata: Sequence[str], judge: Sequence[Label], human: Sequence[Label], stratum: str
) -> float:
    """Judge-human accuracy restricted to the items of one question stratum (e.g. E4)."""
    if not len(strata) == len(judge) == len(human):
        raise ValueError("strata, judge and human must have the same length.")
    pairs = _comparable_pairs(
        [j for s, j in zip(strata, judge, strict=True) if s == stratum],
        [h for s, h in zip(strata, human, strict=True) if s == stratum],
    )
    if not pairs:
        raise ValueError(f"no comparable items in stratum {stratum!r}.")
    return sum(1 for j, h in pairs if j == h) / len(pairs)


# --- stability and robustness ---------------------------------------------------------------


def paired_consistency(first: Sequence[Label], second: Sequence[Label]) -> float:
    """Share of items given the same verdict in two runs (e.g. the two presentation orders)."""
    if len(first) != len(second):
        raise ValueError("the two runs must cover the same items.")
    if not first:
        raise ValueError("paired_consistency is undefined for an empty run.")
    same = sum(1 for a, b in zip(first, second, strict=True) if a is not None and a == b)
    return same / len(first)


def seed_consistency(runs: Sequence[Sequence[Label]]) -> float:
    """Share of items that receive the identical verdict in every seed run."""
    if len(runs) < 2:
        raise ValueError("seed_consistency needs at least two runs.")
    if len({len(run) for run in runs}) != 1:
        raise ValueError("all seed runs must cover the same items.")
    if not runs[0]:
        raise ValueError("seed_consistency is undefined for empty runs.")
    stable = sum(
        1 for item in zip(*runs, strict=True) if item[0] is not None and len(set(item)) == 1
    )
    return stable / len(runs[0])


def json_valid_rate(outcomes: Sequence[JudgeVerdict | JudgeFailure]) -> float:
    """Share of judge calls that produced a parseable, schema-valid verdict."""
    if not outcomes:
        raise ValueError("json_valid_rate is undefined for an empty batch.")
    return sum(1 for o in outcomes if isinstance(o, JudgeVerdict)) / len(outcomes)


def flip_rate(original: Sequence[Label], padded: Sequence[Label]) -> float:
    """Share of verdicts that change when a wrong answer is padded to twice its length.

    Only pairs where both sides produced a verdict are compared; the unusable ones are
    already charged to :func:`json_valid_rate`.
    """
    if len(original) != len(padded):
        raise ValueError("original and padded runs must cover the same items.")
    pairs = [
        (a, b) for a, b in zip(original, padded, strict=True) if a is not None and b is not None
    ]
    if not pairs:
        raise ValueError("flip_rate needs at least one item with a verdict on both sides.")
    return sum(1 for a, b in pairs if a != b) / len(pairs)


# --- decision rule --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CandidateMetrics:
    """Everything the decision rule needs about one candidate judge model."""

    model: str
    kappa_correct: BootstrapCI
    position_consistency: float
    seed_consistency: float
    e4_accuracy: float
    json_valid_rate: float
    verbosity_flip_rate: float
    latency_seconds: float

    def failed_criteria(self, thresholds: CalibrationThresholds) -> tuple[str, ...]:
        """Names of the pre-registered criteria this candidate misses (empty if it passes)."""
        checks = (
            ("kappa_correct", self.kappa_correct.point_estimate >= thresholds.min_kappa_correct),
            (
                "position_consistency",
                self.position_consistency >= thresholds.min_position_consistency,
            ),
            ("seed_consistency", self.seed_consistency >= thresholds.min_seed_consistency),
            ("e4_accuracy", self.e4_accuracy >= thresholds.min_e4_accuracy),
            ("json_valid_rate", self.json_valid_rate >= thresholds.min_json_valid_rate),
            (
                "verbosity_flip_rate",
                self.verbosity_flip_rate <= thresholds.max_verbosity_flip_rate,
            ),
        )
        return tuple(name for name, passed in checks if not passed)


@dataclass(frozen=True, slots=True)
class JudgeDecision:
    """Outcome of the selection: a model id, or the explicit ``no_judge`` outcome."""

    selected: str | None
    failures: dict[str, tuple[str, ...]]

    @property
    def outcome(self) -> str:
        return "selected" if self.selected is not None else "no_judge"


def decide_judge(
    candidates: Sequence[CandidateMetrics], thresholds: CalibrationThresholds
) -> JudgeDecision:
    """Apply the pre-registered rule: pass every threshold, then best kappa, then latency.

    Among the passing candidates the one with the highest kappa on ``correct`` wins; if
    other passing candidates' kappa intervals overlap the winner's, the fastest of that
    group is chosen instead. When nobody passes, automatic judging is discarded
    (``selected is None``) and thesis section 5.7 is met with the human subsample alone.
    """
    if not candidates:
        raise ValueError("decide_judge needs at least one candidate.")
    failures = {c.model: c.failed_criteria(thresholds) for c in candidates}
    passing = [c for c in candidates if not failures[c.model]]
    if not passing:
        return JudgeDecision(selected=None, failures=failures)
    best = max(passing, key=lambda c: c.kappa_correct.point_estimate)
    tied = [
        c
        for c in passing
        if c.kappa_correct.lower <= best.kappa_correct.upper
        and best.kappa_correct.lower <= c.kappa_correct.upper
    ]
    winner = min(tied, key=lambda c: c.latency_seconds)
    return JudgeDecision(selected=winner.model, failures=failures)
