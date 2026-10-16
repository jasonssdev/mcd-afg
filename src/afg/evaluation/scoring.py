"""Experiment A scoring (OE2): extracted decisions against the adjudicated reference.

Decision-level precision, recall and F1 under the alignment protocol of thesis section 5.4
(:mod:`afg.evaluation.alignment`, ``docs/protocols/alignment.md``), computed per series and
pooled, stratified by speaker role (section 5.8 and the metrics section of the proposal)
and aggregated over repeated runs.

Nothing here computes embeddings: the similarity between (object, content) texts is an
injected :data:`SimilarityFn`, so the module is testable with a fake and independent of the
embedding backend.

## Matching

One alignment per series and threshold ``tau``. Scope decided in ADR 0011 (issue #99, from
notebook 14 on the first real extraction of a development series): a pair is admissible only if the
reference decision's meeting is among the extracted decision's origin meetings
(:attr:`afg.domain.decision.Decision.origin_meetings`; OpenKOS may merge a decision restated
in several meetings into one concept). Inadmissible pairs are masked in the similarity matrix
(set to ``-inf``) before the Hungarian assignment, so :func:`afg.evaluation.alignment.align`
is untouched. This is the primary scope (``alignment_scope="origin_meetings"``); the
series-wide alignment (every extracted decision against every reference decision of the
series) stays available as a SENSITIVITY analysis (``alignment_scope="series"``), and
:func:`score_series_views` computes both side by side. Only extracted decisions with status
``ACCEPTED`` are scored; the others are not claims of a decision and are counted in
``n_ignored_non_decisions``. ``TP`` is the number of matches, ``FP`` the unmatched extracted
decisions, ``FN`` the unmatched reference decisions. A zero denominator gives 0.0.

## Intervals

PRIMARY (ADR 0011): a percentile bootstrap that resamples whole MEETINGS with replacement
(:func:`meeting_cluster_intervals`), for precision, recall and F1. The decisions of a meeting
share context (topic, speakers, transcript quality), so resampling them as independent is
optimistic. Resamples and level come from ``[evaluation]`` in ``config/experiments.toml``,
the seed from ``[shared_budget].seed``, so the interval is deterministic.

REFERENCE (``*_interval_reference``): the intervals that treat decisions as independent.
Precision and recall are binomial proportions over a small number of decisions, so they carry
a Wilson interval (:func:`afg.evaluation.metrics.wilson_interval`); F1 is not a binomial
proportion, so it carries a percentile bootstrap over decisions (the extracted and the
reference decisions are each resampled with replacement, their hit flags being fixed).

LIMITATION (declared): with few meetings the cluster bootstrap is coarse. A single series has
4 meetings, hence only 35 distinct resamples, and the interval is fragile; it is more stable
when pooling several evaluation series.

## Role stratification

PRIMARY (``by_role``): recall by role uses the majority role of each reference decision
(:func:`afg.evaluation.reference.primary_role`). Precision by role needs a role for each
extracted decision, so it is reported only when ``predicted_role_of`` is given (typically
:func:`evidence_role_resolver`, which reads the role from the extracted decision's evidence
turns).

SENSITIVITY (``by_role_every_role``, ratified in ADR 0011): the same counts, but a decision
with evidence from several roles counts in every role involved (``ReferenceDecision.roles``;
for extracted decisions, ``predicted_roles_of``, typically
:func:`evidence_roles_resolver`).

Native / non-native speakers are not stratified (proposal, section 6.3).

## Partition guard

Results are flagged with the ADR 0005 partition of their series. Anything that touches a
development series is ``development_only`` and :meth:`require_reportable` refuses it, so it
cannot silently enter a results table.
"""

from __future__ import annotations

import random
import statistics
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

from afg.conditions.c1_chunking import FrozenTurn, load_frozen_turns
from afg.domain.decision import Decision
from afg.evaluation.alignment import Match, align
from afg.evaluation.metrics import precision_recall_f1, wilson_interval
from afg.evaluation.reference import ReferenceDecision, primary_role, roles_of
from afg.extraction.runner import MIN_RUNS
from afg.shared.config import load_experiments_config
from afg.shared.paths import TRANSCRIPTS_DIR

__all__ = [
    "ClusterIntervals",
    "DevelopmentResultError",
    "IntervalSettings",
    "PooledScore",
    "RoleScore",
    "RunsReport",
    "ScoreViews",
    "SeriesScore",
    "SimilarityFn",
    "evidence_role_resolver",
    "evidence_roles_resolver",
    "interval_settings_from_config",
    "meeting_cluster_intervals",
    "pair_text",
    "pool_scores",
    "score_runs",
    "score_series",
    "score_series_views",
]

SimilarityFn = Callable[[Sequence[str], Sequence[str]], np.ndarray]
"""``(predicted_texts, reference_texts) -> similarity matrix`` of shape (n_pred, n_ref)."""

AlignmentScope = Literal["origin_meetings", "series"]
"""``origin_meetings`` is the primary scope; ``series`` is the sensitivity analysis."""

UNKNOWN_ROLE = "unknown"
_METHODS = {
    "precision": "meeting-cluster bootstrap",
    "recall": "meeting-cluster bootstrap",
    "f1": "meeting-cluster bootstrap",
}
_REFERENCE_METHODS = {
    "precision": "wilson",
    "recall": "wilson",
    "f1": "bootstrap over decisions",
}


class DevelopmentResultError(RuntimeError):
    """A result computed on development series was asked to enter a results table."""


@dataclass(frozen=True, slots=True)
class IntervalSettings:
    n_resamples: int
    confidence_level: float
    seed: int


def interval_settings_from_config() -> IntervalSettings:
    config = load_experiments_config()
    return IntervalSettings(
        n_resamples=int(config["evaluation"]["bootstrap_resamples"]),
        confidence_level=float(config["evaluation"]["bootstrap_confidence_level"]),
        seed=int(config["shared_budget"]["seed"]),
    )


def pair_text(decision_object: str, content: str) -> str:
    """The text whose embedding represents a decision (thesis section 5.4: object + content)."""
    return f"{decision_object}: {content}"


@dataclass(frozen=True, slots=True)
class RoleScore:
    """Counts behind recall (reference side) and precision (extracted side) for one role."""

    n_reference: int = 0
    n_covered: int = 0
    n_predicted: int = 0
    n_correct: int = 0

    @property
    def recall(self) -> float | None:
        return self.n_covered / self.n_reference if self.n_reference else None

    @property
    def precision(self) -> float | None:
        return self.n_correct / self.n_predicted if self.n_predicted else None

    def __add__(self, other: RoleScore) -> RoleScore:
        return RoleScore(
            self.n_reference + other.n_reference,
            self.n_covered + other.n_covered,
            self.n_predicted + other.n_predicted,
            self.n_correct + other.n_correct,
        )


@dataclass(frozen=True, slots=True)
class SeriesScore:
    """Scores of one series at one threshold."""

    series_id: str
    tau: float
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    predicted_hits: tuple[bool, ...]
    reference_hits: tuple[bool, ...]
    by_role: Mapping[str, RoleScore]
    n_ignored_non_decisions: int = 0
    by_role_every_role: Mapping[str, RoleScore] = field(default_factory=dict)
    alignment_scope: AlignmentScope = "origin_meetings"
    predicted_meetings: tuple[str, ...] = ()
    reference_meetings: tuple[str, ...] = ()


def _align_series(
    reference: Sequence[ReferenceDecision],
    predicted: Sequence[Decision],
    similarity: SimilarityFn,
    tau: float,
    alignment_scope: AlignmentScope,
) -> tuple[list[Decision], tuple[Match, ...]]:
    """The scored (``ACCEPTED``) extracted decisions and their one-to-one matches."""
    accepted = [d for d in predicted if d.is_decision]
    if accepted and reference:
        matrix = np.asarray(
            similarity(
                [pair_text(d.decision_object, d.content) for d in accepted],
                [pair_text(r.decision_object, r.content) for r in reference],
            ),
            dtype=float,
        )
    else:
        matrix = np.zeros((len(accepted), len(reference)))
    if alignment_scope == "origin_meetings":
        admissible = np.array(
            [[r.meeting_id in d.origin_meetings for r in reference] for d in accepted],
            dtype=bool,
        ).reshape(len(accepted), len(reference))
        matrix = np.where(admissible, matrix, -np.inf)
    return accepted, align(matrix, tau).matches


def score_series(
    series_id: str,
    reference: Sequence[ReferenceDecision],
    predicted: Sequence[Decision],
    similarity: SimilarityFn,
    *,
    tau: float,
    predicted_role_of: Callable[[Decision], str | None] | None = None,
    predicted_roles_of: Callable[[Decision], Sequence[str]] | None = None,
    alignment_scope: AlignmentScope = "origin_meetings",
) -> SeriesScore:
    """Align ``predicted`` to ``reference`` at ``tau`` and count TP/FP/FN (module docstring)."""
    accepted, matches = _align_series(reference, predicted, similarity, tau, alignment_scope)

    predicted_hits = [False] * len(accepted)
    reference_hits = [False] * len(reference)
    for match in matches:
        predicted_hits[match.predicted_index] = True
        reference_hits[match.reference_index] = True

    tp = len(matches)
    fp, fn = len(accepted) - tp, len(reference) - tp
    precision, recall, f1 = precision_recall_f1(tp, fp, fn)

    roles: dict[str, RoleScore] = {}
    for ref, hit in zip(reference, reference_hits, strict=True):
        key = ref.role or UNKNOWN_ROLE
        roles[key] = roles.get(key, RoleScore()) + RoleScore(1, int(hit), 0, 0)
    if predicted_role_of is not None:
        for decision, hit in zip(accepted, predicted_hits, strict=True):
            key = predicted_role_of(decision) or UNKNOWN_ROLE
            roles[key] = roles.get(key, RoleScore()) + RoleScore(0, 0, 1, int(hit))

    every_role: dict[str, RoleScore] = {}
    for ref, hit in zip(reference, reference_hits, strict=True):
        for key in ref.roles or (ref.role or UNKNOWN_ROLE,):
            every_role[key] = every_role.get(key, RoleScore()) + RoleScore(1, int(hit), 0, 0)
    if predicted_roles_of is not None:
        for decision, hit in zip(accepted, predicted_hits, strict=True):
            for key in predicted_roles_of(decision) or (UNKNOWN_ROLE,):
                every_role[key] = every_role.get(key, RoleScore()) + RoleScore(0, 0, 1, int(hit))

    return SeriesScore(
        series_id=series_id,
        tau=tau,
        tp=tp,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        predicted_hits=tuple(predicted_hits),
        reference_hits=tuple(reference_hits),
        by_role=roles,
        n_ignored_non_decisions=len(predicted) - len(accepted),
        by_role_every_role=every_role,
        alignment_scope=alignment_scope,
        predicted_meetings=tuple(d.meeting_id for d in accepted),
        reference_meetings=tuple(r.meeting_id for r in reference),
    )


@dataclass(frozen=True, slots=True)
class ScoreViews:
    """The primary score (origin-meeting scope) and its series-wide sensitivity analysis."""

    primary: SeriesScore
    series_wide_sensitivity: SeriesScore


def score_series_views(
    series_id: str,
    reference: Sequence[ReferenceDecision],
    predicted: Sequence[Decision],
    similarity: SimilarityFn,
    *,
    tau: float,
    predicted_role_of: Callable[[Decision], str | None] | None = None,
    predicted_roles_of: Callable[[Decision], Sequence[str]] | None = None,
) -> ScoreViews:
    """Score once per alignment scope so both results are reportable side by side."""

    def run(scope: AlignmentScope) -> SeriesScore:
        return score_series(
            series_id,
            reference,
            predicted,
            similarity,
            tau=tau,
            predicted_role_of=predicted_role_of,
            predicted_roles_of=predicted_roles_of,
            alignment_scope=scope,
        )

    return ScoreViews(primary=run("origin_meetings"), series_wide_sensitivity=run("series"))


def evidence_roles_resolver(
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> Callable[[Decision], tuple[str, ...]]:
    """Every role of an extracted decision's evidence turns (sensitivity view of the roles)."""
    cache: dict[str, list[FrozenTurn]] = {}

    def roles_for(decision: Decision) -> tuple[str, ...]:
        meeting = decision.evidence.meeting_id
        if meeting not in cache:
            cache[meeting] = load_frozen_turns(meeting, transcripts_dir)
        return roles_of(decision.evidence.dialogue_act_ids, cache[meeting])

    return roles_for


def evidence_role_resolver(
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> Callable[[Decision], str | None]:
    """Role of an extracted decision: primary role of the turns of its evidence acts."""
    cache: dict[str, list[FrozenTurn]] = {}

    def role_of(decision: Decision) -> str | None:
        meeting = decision.evidence.meeting_id
        if meeting not in cache:
            cache[meeting] = load_frozen_turns(meeting, transcripts_dir)
        return primary_role(decision.evidence.dialogue_act_ids, cache[meeting])

    return role_of


# --- pooling --------------------------------------------------------------------------------


def _combine_partitions(partitions: Iterable[str]) -> str:
    found = set(partitions)
    return found.pop() if len(found) == 1 else "mixed"


def _bootstrap_f1(
    predicted_hits: Sequence[bool],
    reference_hits: Sequence[bool],
    settings: IntervalSettings,
) -> tuple[float, float]:
    n_p, n_r = len(predicted_hits), len(reference_hits)
    if not n_p or not n_r:
        return (0.0, 0.0)
    rng = random.Random(settings.seed)
    values: list[float] = []
    for _ in range(settings.n_resamples):
        tp_p = sum(predicted_hits[rng.randrange(n_p)] for _ in range(n_p))
        tp_r = sum(reference_hits[rng.randrange(n_r)] for _ in range(n_r))
        precision, recall = tp_p / n_p, tp_r / n_r
        total = precision + recall
        values.append(2 * precision * recall / total if total else 0.0)
    values.sort()
    alpha = 1.0 - settings.confidence_level
    lower = values[max(0, int(alpha / 2 * settings.n_resamples))]
    upper = values[min(settings.n_resamples - 1, int((1 - alpha / 2) * settings.n_resamples))]
    return (lower, upper)


@dataclass(frozen=True, slots=True)
class ClusterIntervals:
    """Point estimates and meeting-cluster bootstrap intervals (percentile)."""

    n_clusters: int
    precision: float
    recall: float
    f1: float
    precision_interval: tuple[float, float]
    recall_interval: tuple[float, float]
    f1_interval: tuple[float, float]
    confidence_level: float


def _f1(precision: float, recall: float) -> float:
    total = precision + recall
    return 2 * precision * recall / total if total else 0.0


def _percentiles(values: list[float], level: float) -> tuple[float, float]:
    values.sort()
    n = len(values)
    alpha = 1.0 - level
    return (values[max(0, int(alpha / 2 * n))], values[min(n - 1, int((1 - alpha / 2) * n))])


def meeting_cluster_intervals(
    predicted: Sequence[tuple[str, bool]],
    reference: Sequence[tuple[str, bool]],
    settings: IntervalSettings,
) -> ClusterIntervals:
    """Percentile bootstrap that resamples whole clusters (meetings) with replacement.

    ``predicted`` and ``reference`` are ``(cluster, hit)`` pairs, e.g. the meeting of each
    extracted decision with its hit flag, and the meeting of each reference decision with its
    hit flag. Each resample draws as many clusters as there are, sums their counts and
    recomputes precision, recall and F1 (a zero denominator gives 0.0, as in scoring).
    Deterministic for ``settings.seed`` and ``settings.n_resamples``.
    """
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])  # hits_p, n_p, hits_r, n_r
    for cluster, hit in predicted:
        counts[cluster][0] += int(hit)
        counts[cluster][1] += 1
    for cluster, hit in reference:
        counts[cluster][2] += int(hit)
        counts[cluster][3] += 1
    clusters = sorted(counts)
    n_p, n_r = len(predicted), len(reference)
    precision = sum(c[0] for c in counts.values()) / n_p if n_p else 0.0
    recall = sum(c[2] for c in counts.values()) / n_r if n_r else 0.0
    if not clusters:
        zero = (0.0, 0.0)
        return ClusterIntervals(0, 0.0, 0.0, 0.0, zero, zero, zero, settings.confidence_level)

    rng = random.Random(settings.seed)
    ps: list[float] = []
    rs: list[float] = []
    fs: list[float] = []
    for _ in range(settings.n_resamples):
        total = [0, 0, 0, 0]
        for _ in clusters:
            for k, v in enumerate(counts[clusters[rng.randrange(len(clusters))]]):
                total[k] += v
        p = total[0] / total[1] if total[1] else 0.0
        r = total[2] / total[3] if total[3] else 0.0
        ps.append(p)
        rs.append(r)
        fs.append(_f1(p, r))
    level = settings.confidence_level
    return ClusterIntervals(
        n_clusters=len(clusters),
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
        precision_interval=_percentiles(ps, level),
        recall_interval=_percentiles(rs, level),
        f1_interval=_percentiles(fs, level),
        confidence_level=level,
    )


def _wilson(successes: int, trials: int, level: float) -> tuple[float, float]:
    if trials <= 0:
        return (0.0, 0.0)
    interval = wilson_interval(successes, trials, level)
    return (interval.lower, interval.upper)


@dataclass(frozen=True, slots=True)
class PooledScore:
    """Micro-averaged scores over several series at one threshold."""

    tau: float
    series: tuple[str, ...]
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    precision_interval: tuple[float, float]
    recall_interval: tuple[float, float]
    f1_interval: tuple[float, float]
    confidence_level: float
    by_role: Mapping[str, RoleScore]
    partition: str
    n_clusters: int = 0
    precision_interval_reference: tuple[float, float] = (0.0, 0.0)
    recall_interval_reference: tuple[float, float] = (0.0, 0.0)
    f1_interval_reference: tuple[float, float] = (0.0, 0.0)
    by_role_every_role: Mapping[str, RoleScore] = field(default_factory=dict)
    alignment_scope: AlignmentScope = "origin_meetings"
    interval_methods: Mapping[str, str] = field(default_factory=lambda: dict(_METHODS))
    reference_interval_methods: Mapping[str, str] = field(
        default_factory=lambda: dict(_REFERENCE_METHODS)
    )

    @property
    def development_only(self) -> bool:
        return self.partition == "development"

    @property
    def reportable(self) -> bool:
        """Only a result over evaluation series only may enter a results table."""
        return self.partition == "evaluation"

    def require_reportable(self) -> None:
        _require_reportable(self.partition, self.series)


def _require_reportable(partition: str, series: Sequence[str]) -> None:
    if partition != "evaluation":
        raise DevelopmentResultError(
            f"Result over {', '.join(series)} has partition {partition!r}: only results over "
            "evaluation series enter a results table (ADR 0005)."
        )


def _cluster_hits(
    scores: Sequence[SeriesScore],
) -> tuple[list[tuple[str, bool]], list[tuple[str, bool]]]:
    """``(meeting, hit)`` pairs of the extracted and the reference decisions of ``scores``.

    A score built without meeting labels falls back to its series as the cluster.
    """
    predicted: list[tuple[str, bool]] = []
    reference: list[tuple[str, bool]] = []
    for s in scores:
        p_labels = s.predicted_meetings or (s.series_id,) * len(s.predicted_hits)
        r_labels = s.reference_meetings or (s.series_id,) * len(s.reference_hits)
        predicted += zip(p_labels, s.predicted_hits, strict=True)
        reference += zip(r_labels, s.reference_hits, strict=True)
    return predicted, reference


def pool_scores(
    scores: Sequence[SeriesScore],
    *,
    settings: IntervalSettings,
    partition_of: Callable[[str], str] | None = None,
) -> PooledScore:
    """Pool per-series scores (micro average) and attach intervals and the partition flag.

    The primary intervals resample whole meetings (ADR 0011); the independent-decision
    intervals are attached as ``*_interval_reference``.
    """
    if not scores:
        raise ValueError("pool_scores is undefined for an empty list of series scores.")
    taus = {s.tau for s in scores}
    if len(taus) != 1:
        raise ValueError(f"Cannot pool scores computed at different tau values: {sorted(taus)}.")
    if partition_of is None:
        from afg.experiments.runner import configured_partition_of

        partition_of = configured_partition_of()

    tp, fp, fn = (sum(getattr(s, name) for s in scores) for name in ("tp", "fp", "fn"))
    precision, recall, f1 = precision_recall_f1(tp, fp, fn)
    predicted_hits = [h for s in scores for h in s.predicted_hits]
    reference_hits = [h for s in scores for h in s.reference_hits]
    clusters = _cluster_hits(scores)
    cluster_intervals = meeting_cluster_intervals(*clusters, settings)
    pooled_roles: dict[str, RoleScore] = {}
    for s in scores:
        for role, counts in s.by_role.items():
            pooled_roles[role] = pooled_roles.get(role, RoleScore()) + counts
    pooled_every_role: dict[str, RoleScore] = {}
    for s in scores:
        for role, counts in s.by_role_every_role.items():
            pooled_every_role[role] = pooled_every_role.get(role, RoleScore()) + counts
    level = settings.confidence_level
    return PooledScore(
        tau=scores[0].tau,
        series=tuple(s.series_id for s in scores),
        tp=tp,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        precision_interval=cluster_intervals.precision_interval,
        recall_interval=cluster_intervals.recall_interval,
        f1_interval=cluster_intervals.f1_interval,
        confidence_level=level,
        by_role=pooled_roles,
        partition=_combine_partitions(partition_of(s.series_id) for s in scores),
        n_clusters=cluster_intervals.n_clusters,
        precision_interval_reference=_wilson(tp, tp + fp, level),
        recall_interval_reference=_wilson(tp, tp + fn, level),
        f1_interval_reference=_bootstrap_f1(predicted_hits, reference_hits, settings),
        by_role_every_role=pooled_every_role,
        alignment_scope=scores[0].alignment_scope,
    )


# --- repeated runs (thesis section 5.8) ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RunsReport:
    """Pooled score of each run plus mean and sample standard deviation across runs."""

    runs: tuple[PooledScore, ...]
    precision_mean: float
    precision_stdev: float
    recall_mean: float
    recall_stdev: float
    f1_mean: float
    f1_stdev: float
    partition: str

    @property
    def n_runs(self) -> int:
        return len(self.runs)

    @property
    def reportable(self) -> bool:
        return self.partition == "evaluation"

    def require_reportable(self) -> None:
        _require_reportable(self.partition, sorted({s for r in self.runs for s in r.series}))


def score_runs(
    references: Mapping[str, Sequence[ReferenceDecision]],
    runs: Sequence[Mapping[str, Sequence[Decision]]],
    similarity: SimilarityFn,
    *,
    tau: float,
    settings: IntervalSettings,
    partition_of: Callable[[str], str] | None = None,
    predicted_role_of: Callable[[Decision], str | None] | None = None,
    predicted_roles_of: Callable[[Decision], Sequence[str]] | None = None,
    alignment_scope: AlignmentScope = "origin_meetings",
) -> RunsReport:
    """Score each run (``series -> extracted decisions``) and aggregate across runs.

    Raises:
        ValueError: fewer than :data:`~afg.extraction.runner.MIN_RUNS` runs (section 5.8).
        KeyError: a run has a series with no reference.
    """
    if len(runs) < MIN_RUNS:
        raise ValueError(
            f"{len(runs)} runs is below the thesis section 5.8 minimum of {MIN_RUNS} runs."
        )
    pooled = tuple(
        pool_scores(
            [
                score_series(
                    series,
                    references[series],
                    decisions,
                    similarity,
                    tau=tau,
                    predicted_role_of=predicted_role_of,
                    predicted_roles_of=predicted_roles_of,
                    alignment_scope=alignment_scope,
                )
                for series, decisions in run.items()
            ],
            settings=settings,
            partition_of=partition_of,
        )
        for run in runs
    )

    def mean_stdev(values: list[float]) -> tuple[float, float]:
        return statistics.mean(values), statistics.stdev(values)

    p_mean, p_sd = mean_stdev([r.precision for r in pooled])
    r_mean, r_sd = mean_stdev([r.recall for r in pooled])
    f_mean, f_sd = mean_stdev([r.f1 for r in pooled])
    return RunsReport(
        runs=pooled,
        precision_mean=p_mean,
        precision_stdev=p_sd,
        recall_mean=r_mean,
        recall_stdev=r_sd,
        f1_mean=f_mean,
        f1_stdev=f_sd,
        partition=_combine_partitions(r.partition for r in pooled),
    )
