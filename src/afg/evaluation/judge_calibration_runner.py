"""Runs candidate judge models over the labeled calibration set (thesis section 5.7).

For each candidate this module calls :func:`afg.evaluation.judge.judge_answer` on every
labeled item in both presentation orders and for each seed in ``[judge.calibration].seeds``,
adds the verbosity probe (every answer humans labeled incorrect is padded to about twice its
length and judged again), times each call and counts the calls that produced no usable
verdict. All arithmetic is delegated to :mod:`afg.evaluation.judge_calibration`; the
decision across candidates is :func:`afg.evaluation.judge_calibration.decide_judge`.

The backend is injected (``JudgeBackend``), so tests use a fake and the harness uses
:class:`afg.evaluation.judge.OllamaJudgeBackend`. Backend errors (connection, missing model)
propagate: they say nothing about the judge's behaviour.

The primary run (reference first, first seed) feeds the agreement, abstention and
verbosity metrics; the other runs feed the consistency metrics.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from afg.domain.question import Answer, Question, QuestionStratum
from afg.evaluation.judge import (
    JudgeBackend,
    JudgeFailure,
    JudgeVerdict,
    PresentationOrder,
    judge_answer,
)
from afg.evaluation.judge_calibration import (
    CalibrationThresholds,
    CandidateMetrics,
    FieldAgreement,
    JudgeDecision,
    Label,
    decide_judge,
    field_agreement,
    flip_rate,
    json_valid_rate,
    kappa_confidence_interval,
    paired_consistency,
    seed_consistency,
    stratum_accuracy,
)
from afg.evaluation.judge_calibration_set import CalibrationItem, CalibrationSetError
from afg.evaluation.metrics import BootstrapCI
from afg.shared.config import load_experiments_config

_CONDITION = "CAL"
"""Placeholder condition id: the judge never sees it (anonymization)."""

_ORDERS: tuple[PresentationOrder, ...] = ("reference_first", "answer_first")

Outcome = JudgeVerdict | JudgeFailure


@dataclass(frozen=True, slots=True)
class CandidateRun:
    """What one candidate produced: its metrics plus the bookkeeping behind them."""

    metrics: CandidateMetrics
    evidence_supported: FieldAgreement | None
    calls: int
    failures: int


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    runs: tuple[CandidateRun, ...]
    decision: JudgeDecision


def load_candidates() -> tuple[str, ...]:
    """The candidate judge models, from ``[judge.calibration].candidates`` (primary first)."""
    section = load_experiments_config()["judge"]["calibration"]
    return tuple(str(model) for model in section["candidates"])


def pad_to_double_length(text: str) -> str:
    """Repeat ``text`` once after itself: about twice the length, with the same content.

    Deterministic by construction. The verbosity probe asks whether a judge rewards length
    alone (Zheng et al., 2023), so the padding adds no new claim.
    """
    return f"{text} {text}"


def _question(item: CalibrationItem) -> Question:
    return Question(
        id=item.id,
        series_id=item.series_id,
        stratum=item.stratum,
        text=item.question,
        reference_answer=item.reference_answer,
    )


def _answer(item: CalibrationItem, text: str) -> Answer:
    return Answer(
        question_id=item.id,
        condition=_CONDITION,
        text=text,
        abstained=item.answer_abstained,
    )


def _no_kappa(n_resamples: int | None) -> BootstrapCI:
    """Worst-case kappa for a judge with no usable verdict at all (chance level)."""
    evaluation = load_experiments_config()["evaluation"]
    return BootstrapCI(
        point_estimate=0.0,
        lower=0.0,
        upper=0.0,
        confidence_level=float(evaluation["bootstrap_confidence_level"]),
        n_resamples=n_resamples
        if n_resamples is not None
        else int(evaluation["bootstrap_resamples"]),
    )


def _correct(outcomes: Sequence[Outcome]) -> list[Label]:
    return [o.correct if isinstance(o, JudgeVerdict) else None for o in outcomes]


def _evidence(outcomes: Sequence[Outcome]) -> list[Label]:
    return [o.evidence_supported if isinstance(o, JudgeVerdict) else None for o in outcomes]


def run_candidate(
    items: Sequence[CalibrationItem],
    *,
    judge_model: str,
    generative_model: str,
    backend: JudgeBackend,
    thresholds: CalibrationThresholds,
    temperature: float = 0.0,
    n_resamples: int | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> CandidateRun:
    """Judge every labeled item with one candidate and build its :class:`CandidateMetrics`.

    Raises:
        CalibrationSetError: if an item has no human labels.
        JudgeConfigurationError: if the judge and generative models coincide.
        ValueError: if the set lacks what a metric needs (no E4 item, no incorrect answer).
    """
    for item in items:
        if not item.is_labeled:
            raise CalibrationSetError(f"item {item.id!r} has no human labels.")
    if not any(item.stratum is QuestionStratum.E4_UNANSWERABLE for item in items):
        raise ValueError("the calibration set needs at least one E4 (unanswerable) item.")
    if not any(item.correct is False for item in items):
        raise ValueError("the calibration set needs at least one answer labeled incorrect.")
    seeds = thresholds.seeds
    elapsed: list[float] = []
    outcomes: list[Outcome] = []

    def judge(item: CalibrationItem, text: str, order: PresentationOrder, seed: int) -> Outcome:
        started = clock()
        outcome = judge_answer(
            _question(item),
            _answer(item, text),
            judge_model=judge_model,
            generative_model=generative_model,
            backend=backend,
            order=order,
            seed=seed,
            temperature=temperature,
        )
        elapsed.append(clock() - started)
        outcomes.append(outcome)
        return outcome

    runs = {
        (order, seed): [judge(item, item.answer_text, order, seed) for item in items]
        for order in _ORDERS
        for seed in seeds
    }
    primary = runs[("reference_first", seeds[0])]
    wrong = [i for i, item in enumerate(items) if item.correct is False]
    padded = [
        judge(items[i], pad_to_double_length(items[i].answer_text), "reference_first", seeds[0])
        for i in wrong
    ]

    human_correct: list[Label] = [item.correct for item in items]
    judge_correct = _correct(primary)
    # A judge with no usable verdict on the compared items takes the worst value of the
    # metric (the unusable outputs are also charged to json_valid_rate) instead of aborting.
    try:
        kappa = kappa_confidence_interval(judge_correct, human_correct, n_resamples=n_resamples)
    except ValueError:
        kappa = _no_kappa(n_resamples)
    try:
        e4 = stratum_accuracy(
            [item.stratum.value for item in items],
            judge_correct,
            human_correct,
            QuestionStratum.E4_UNANSWERABLE.value,
        )
    except ValueError:
        e4 = 0.0
    try:
        verbosity = flip_rate([judge_correct[i] for i in wrong], _correct(padded))
    except ValueError:
        verbosity = 1.0
    metrics = CandidateMetrics(
        model=judge_model,
        kappa_correct=kappa,
        position_consistency=paired_consistency(
            judge_correct, _correct(runs[("answer_first", seeds[0])])
        ),
        seed_consistency=seed_consistency([_correct(runs[("reference_first", s)]) for s in seeds]),
        e4_accuracy=e4,
        json_valid_rate=json_valid_rate(outcomes),
        verbosity_flip_rate=verbosity,
        latency_seconds=sum(elapsed) / len(elapsed),
    )
    try:
        evidence = field_agreement(_evidence(primary), [item.evidence_supported for item in items])
    except ValueError:
        evidence = None  # no verdict at all: already charged to json_valid_rate
    return CandidateRun(
        metrics=metrics,
        evidence_supported=evidence,
        calls=len(outcomes),
        failures=sum(1 for o in outcomes if isinstance(o, JudgeFailure)),
    )


def run_calibration(
    items: Sequence[CalibrationItem],
    *,
    candidates: Sequence[str],
    generative_model: str,
    backend_for: Callable[[str], JudgeBackend],
    thresholds: CalibrationThresholds,
    temperature: float = 0.0,
    n_resamples: int | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> CalibrationResult:
    """Run every candidate, then apply the pre-registered decision rule."""
    runs = tuple(
        run_candidate(
            items,
            judge_model=model,
            generative_model=generative_model,
            backend=backend_for(model),
            thresholds=thresholds,
            temperature=temperature,
            n_resamples=n_resamples,
            clock=clock,
        )
        for model in candidates
    )
    return CalibrationResult(
        runs=runs, decision=decide_judge([r.metrics for r in runs], thresholds)
    )
