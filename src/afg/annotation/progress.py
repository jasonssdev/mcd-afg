"""Where one annotator really stands, and the one thing to do next.

``afg gold setup`` and ``afg gold status --annotator`` used to answer "what now?" from the
first series in the config, which for months was a series already adjudicated. Everything
here is derived from the state of the repository instead:

* **Released** (``plan.released_series``): whether ``jss`` has opened the series. A human
  signal, so it is the only piece of state kept in ``config/annotation.toml``.
* **Adjudicated**: both ``<series>.decisions.adjudicated.csv`` and
  ``<series>.candidates.adjudicated.csv`` exist. The series is closed.
* **Ready to deliver**: every row of Tasks A and B is filled and the files validate. The
  repository cannot tell whether the pull request was already opened, so the next-step text
  says "if you have not yet".
* **In progress / to start / with errors / not prepared**: from the validation report.

The next action is the first applicable of: work on the first open, unfinished series;
deliver a finished series; do Task C; work on the question bank; wait for ``jss``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from afg.annotation.workspace import (
    AnnotationPlan,
    SeriesProgress,
    TaskKind,
    WorkspacePaths,
    decision_row_counts,
    validate_annotator,
    validate_workspace_file,
)
from afg.experiments.question_bank import QuestionBankProgress, question_bank_progress

__all__ = [
    "AnnotatorStatus",
    "NextAction",
    "NextKind",
    "RecallStatus",
    "SeriesState",
    "SeriesStatus",
    "annotator_status",
]


class SeriesState(StrEnum):
    """The value is the label shown to the annotator."""

    NOT_YET = "pendiente (aún no)"
    NOT_PREPARED = "sin preparar"
    TO_START = "por empezar"
    IN_PROGRESS = "en curso"
    ERRORS = "con errores"
    READY = "lista para entregar"
    ADJUDICATED = "adjudicada"


class NextKind(StrEnum):
    ANNOTATE = "annotate"
    FIX = "fix"
    PREPARE = "prepare"
    DELIVER = "deliver"
    RECALL = "recall"
    BANK = "bank"
    WAIT = "wait"
    NOTHING = "nothing"


@dataclass(frozen=True, slots=True)
class SeriesStatus:
    series_id: str
    phase: int
    state: SeriesState
    double: bool
    decisions_filled: int
    decisions_total: int
    originals: int
    parts: int
    candidates_filled: int
    candidates_total: int
    issue_count: int


@dataclass(frozen=True, slots=True)
class RecallStatus:
    """Task C progress for one series of the recall sample."""

    series_id: str
    state: SeriesState
    filled: int
    total: int


@dataclass(frozen=True, slots=True)
class NextAction:
    kind: NextKind
    message: str
    series_id: str | None = None
    phase: int | None = None
    target: Path | None = None
    partner: Path | None = None


@dataclass(frozen=True, slots=True)
class AnnotatorStatus:
    initials: str
    series: tuple[SeriesStatus, ...]
    recall: tuple[RecallStatus, ...]
    bank: QuestionBankProgress | None
    bank_role: str | None
    """``"author"`` or ``"validator"`` when this person works on the question bank."""
    next_action: NextAction


def _series_state(
    plan: AnnotationPlan,
    initials: str,
    series_id: str,
    progress: SeriesProgress | None,
    paths: WorkspacePaths,
) -> SeriesState:
    if not plan.is_released(series_id):
        return SeriesState.NOT_YET
    if (
        paths.adjudicated(TaskKind.DECISIONS, series_id).exists()
        and paths.adjudicated(TaskKind.CANDIDATES, series_id).exists()
    ):
        return SeriesState.ADJUDICATED
    assert progress is not None
    if progress.not_started:
        return SeriesState.NOT_PREPARED
    if not progress.ok:
        return SeriesState.ERRORS
    if progress.complete:
        return SeriesState.READY
    if progress.decisions_filled == 0 and progress.candidates_filled == 0:
        return SeriesState.TO_START
    return SeriesState.IN_PROGRESS


def _recall_statuses(
    plan: AnnotationPlan,
    initials: str,
    paths: WorkspacePaths,
    by_series: dict[str, SeriesStatus],
) -> tuple[RecallStatus, ...]:
    recall = plan.recall_sample
    if recall.owner != initials:
        return ()
    closed = {SeriesState.READY, SeriesState.ADJUDICATED}
    out: list[RecallStatus] = []
    for series_id in recall.series_ids:
        own = by_series.get(series_id)
        if not plan.is_released(series_id) or (own is not None and own.state not in closed):
            out.append(RecallStatus(series_id, SeriesState.NOT_YET, 0, 0))
            continue
        target = paths.target(TaskKind.RECALL_SAMPLE, series_id, initials)
        if not target.exists():
            out.append(RecallStatus(series_id, SeriesState.NOT_PREPARED, 0, 0))
            continue
        filled, total, issues = validate_workspace_file(
            target, paths.source(TaskKind.RECALL_SAMPLE, series_id), TaskKind.RECALL_SAMPLE
        )
        if issues:
            state = SeriesState.ERRORS
        elif total and filled == total:
            state = SeriesState.READY
        elif filled == 0:
            state = SeriesState.TO_START
        else:
            state = SeriesState.IN_PROGRESS
        out.append(RecallStatus(series_id, state, filled, total))
    return tuple(out)


def _bank(
    plan: AnnotationPlan, initials: str, paths: WorkspacePaths
) -> tuple[QuestionBankProgress | None, str | None]:
    bank = plan.question_bank
    role = (
        "author" if bank.author == initials else "validator" if bank.validator == initials else None
    )
    if role is None:
        return None, None
    from afg.domain.question import QuestionStratum

    progress = question_bank_progress(
        paths.question_bank,
        minimum=bank.questions_per_stratum,
        rows_per_stratum={s: bank.rows_for(s) for s in QuestionStratum},
    )
    return progress, role


def _next_action(
    plan: AnnotationPlan,
    initials: str,
    paths: WorkspacePaths,
    series: tuple[SeriesStatus, ...],
    recall: tuple[RecallStatus, ...],
    bank: QuestionBankProgress | None,
    bank_role: str | None,
) -> NextAction:
    adjudicator = plan.adjudicator
    doc = f"tareas-{initials}.md"

    for item in series:
        if item.state is SeriesState.NOT_PREPARED:
            return NextAction(
                NextKind.PREPARE,
                f"Corre `uv run afg gold prepare --annotator {initials}` para crear los "
                f"archivos de {item.series_id}.",
                item.series_id,
                item.phase,
            )
        if item.state is SeriesState.ERRORS:
            return NextAction(
                NextKind.FIX,
                f"Corrige los errores de {item.series_id}: corre `uv run afg gold validate "
                f"--annotator {initials} --series {item.series_id}` y sigue lo que indica.",
                item.series_id,
                item.phase,
            )
        if item.state in (SeriesState.TO_START, SeriesState.IN_PROGRESS):
            decisions = paths.target(TaskKind.DECISIONS, item.series_id, initials)
            candidates = paths.target(TaskKind.CANDIDATES, item.series_id, initials)
            if item.decisions_filled < item.decisions_total or item.candidates_total == 0:
                target, partner = decisions, candidates
            else:
                target, partner = candidates, decisions
            return NextAction(
                NextKind.ANNOTATE,
                f"Anota la serie {item.series_id} (fase {item.phase}): abre {target.name}.",
                item.series_id,
                item.phase,
                target,
                partner,
            )

    for item in series:
        if item.state is SeriesState.READY:
            tail = f" y espera la adjudicación de {adjudicator}" if item.double else ""
            return NextAction(
                NextKind.DELIVER,
                f"Entrega la serie {item.series_id} si aún no abriste su PR (ver «Cómo "
                f"entregas» en {doc}){tail}.",
                item.series_id,
                item.phase,
            )

    for rec in recall:
        if rec.state in (SeriesState.TO_START, SeriesState.IN_PROGRESS, SeriesState.NOT_PREPARED):
            return NextAction(
                NextKind.RECALL,
                f"Haz la muestra de recall de {rec.series_id} (Tarea C): abre "
                f"{paths.target(TaskKind.RECALL_SAMPLE, rec.series_id, initials).name}.",
                rec.series_id,
            )
        if rec.state is SeriesState.ERRORS:
            return NextAction(
                NextKind.FIX,
                f"Corrige los errores de la muestra de {rec.series_id} (Tarea C): corre "
                f"`uv run afg gold validate --annotator {initials} --series {rec.series_id}`.",
                rec.series_id,
            )

    if bank is not None and bank_role == "author":
        if bank.missing_for_minimum > 0:
            minimum = plan.question_bank.questions_per_stratum
            return NextAction(
                NextKind.BANK,
                "Sigue con el banco de preguntas: faltan "
                f"{bank.missing_for_minimum} preguntas para el mínimo de {minimum} por estrato.",
            )
        if bank.awaiting_validation > 0:
            return NextAction(
                NextKind.BANK,
                f"El banco ya tiene el mínimo escrito: avisa a {plan.question_bank.validator} "
                "para que lo valide (E3 admite más preguntas solo si el material lo permite).",
            )
    if bank is not None and bank_role == "validator" and bank.awaiting_validation > 0:
        return NextAction(
            NextKind.BANK,
            f"Valida las {bank.awaiting_validation} pregunta(s) del banco que "
            f"{plan.question_bank.author} ya escribió (columna `validated_by`).",
        )

    waiting = [item for item in series if item.state is SeriesState.NOT_YET]
    if waiting:
        return NextAction(
            NextKind.WAIT,
            f"Espera la indicación de {adjudicator} para empezar {waiting[0].series_id}.",
            waiting[0].series_id,
            waiting[0].phase,
        )
    return NextAction(NextKind.NOTHING, "No te queda nada pendiente por ahora.")


def annotator_status(
    plan: AnnotationPlan, initials: str, *, paths: WorkspacePaths
) -> AnnotatorStatus:
    """Derive the full status of one annotating person from the files.

    Raises:
        UnknownAnnotatorError: if ``initials`` is not in the plan.
    """
    person = plan.annotator(initials)
    double = set(plan.double_annotated_series)
    items: list[SeriesStatus] = []
    for assignment in person.assignments:
        sid = assignment.series_id
        progress = (
            validate_annotator(plan, initials, paths=paths, series=sid).series[0]
            if plan.is_released(sid)
            else None
        )
        state = _series_state(plan, initials, sid, progress, paths)
        originals, parts = decision_row_counts(paths.target(TaskKind.DECISIONS, sid, initials))
        items.append(
            SeriesStatus(
                series_id=sid,
                phase=assignment.phase,
                state=state,
                double=sid in double,
                decisions_filled=progress.decisions_filled if progress else 0,
                decisions_total=progress.decisions_total if progress else 0,
                originals=originals,
                parts=parts,
                candidates_filled=progress.candidates_filled if progress else 0,
                candidates_total=progress.candidates_total if progress else 0,
                issue_count=len(progress.issues) if progress else 0,
            )
        )
    series = tuple(items)
    recall = _recall_statuses(plan, initials, paths, {s.series_id: s for s in series})
    bank, bank_role = _bank(plan, initials, paths)
    return AnnotatorStatus(
        initials=initials,
        series=series,
        recall=recall,
        bank=bank,
        bank_role=bank_role,
        next_action=_next_action(plan, initials, paths, series, recall, bank, bank_role),
    )
