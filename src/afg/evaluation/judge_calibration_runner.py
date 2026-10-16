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
from pathlib import Path

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
from afg.evaluation.passage import judge_evidence_passage
from afg.shared.config import load_experiments_config
from afg.shared.paths import TRANSCRIPTS_DIR

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


def load_think_settings() -> dict[str, bool | str]:
    """``[judge.calibration.think]``: reasoning setting per candidate (absent: not sent)."""
    section = load_experiments_config()["judge"]["calibration"].get("think", {})
    allowed = {"low", "medium", "high"}
    settings: dict[str, bool | str] = {}
    for model, value in section.items():
        if not isinstance(value, bool) and value not in allowed:
            raise ValueError(
                f"[judge.calibration.think] {model!r}: {value!r} is not a bool or one of "
                f"{sorted(allowed)}."
            )
        settings[str(model)] = value
    return settings


def load_candidates() -> tuple[str, ...]:
    """The candidate judge models, from ``[judge.calibration].candidates`` (primary first)."""
    section = load_experiments_config()["judge"]["calibration"]
    return tuple(str(model) for model in section["candidates"])


CANDIDATE_ROLES: dict[str, str] = {
    "mistral-small3.2:24b": "primary",
    "atla/selene-mini:q8_0": "evaluation-specialist",
    "gpt-oss:20b": "reserve",
}
"""Why each candidate was shortlisted (notebook 05, section 3.1), keyed by model name so a
reordered ``[judge.calibration].candidates`` list cannot shift a role onto another model."""


def load_candidate_roles() -> dict[str, str]:
    """Role of each configured candidate, in config order; ``"unassigned"`` if not catalogued."""
    return {model: CANDIDATE_ROLES.get(model, "unassigned") for model in load_candidates()}


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
        reference_evidence=item.reference_evidence,
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


ExcerptFor = Callable[[CalibrationItem], str]
"""Builds the transcript excerpt the judge reads for an item; injectable for tests."""


def stored_excerpt_for(item: CalibrationItem, *, transcripts_dir: Path = TRANSCRIPTS_DIR) -> str:
    """The excerpt the judge reads for ``item``.

    It is the stored ``pasaje_transcripcion`` (the exact text the labeler saw), so the judge
    and the human work from the same passage even if the window setting changed afterwards.
    Only when the file has no such column (older files) is it rebuilt from the frozen
    transcripts with the current window.
    """
    if item.transcript_excerpt is not None:
        return item.transcript_excerpt
    return judge_evidence_passage(item.reference_evidence, transcripts_dir=transcripts_dir)


default_excerpt_for: ExcerptFor = stored_excerpt_for


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
    excerpt_for: ExcerptFor = default_excerpt_for,
    progress: Callable[[str, int, int], None] | None = None,
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
    excerpts = {item.id: excerpt_for(item) for item in items}
    total_calls = len(items) * len(_ORDERS) * len(seeds) + sum(
        1 for item in items if item.correct is False
    )
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
            transcript_excerpt=excerpts[item.id],
        )
        elapsed.append(clock() - started)
        outcomes.append(outcome)
        if progress is not None:
            progress(judge_model, len(outcomes), total_calls)
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
    excerpt_for: ExcerptFor = default_excerpt_for,
    progress: Callable[[str, int, int], None] | None = None,
    load_run: Callable[[str], CandidateRun | None] | None = None,
    save_run: Callable[[str, CandidateRun], None] | None = None,
    on_done: Callable[[str, CandidateRun, bool], None] | None = None,
) -> CalibrationResult:
    """Run every candidate, then apply the pre-registered decision rule.

    ``load_run`` lets a candidate that already finished (for these very inputs) be skipped;
    ``save_run`` is called as soon as each candidate finishes, so a failure later in the list
    loses nothing; ``on_done(model, run, reused)`` reports each candidate.
    """
    runs: list[CandidateRun] = []
    for model in candidates:
        stored = load_run(model) if load_run is not None else None
        if stored is not None:
            run, reused = stored, True
        else:
            run = run_candidate(
                items,
                judge_model=model,
                generative_model=generative_model,
                backend=backend_for(model),
                thresholds=thresholds,
                temperature=temperature,
                n_resamples=n_resamples,
                clock=clock,
                excerpt_for=excerpt_for,
                progress=progress,
            )
            reused = False
            if save_run is not None:
                save_run(model, run)
        if on_done is not None:
            on_done(model, run, reused)
        runs.append(run)
    return CalibrationResult(
        runs=tuple(runs), decision=decide_judge([r.metrics for r in runs], thresholds)
    )
