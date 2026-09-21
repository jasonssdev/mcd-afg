"""Per-annotator annotation workspaces: prepare, validate, adjudicate, question bank.

This module exists to delete manual work. Before it, an annotator had to copy the right
CSVs out of ``data/processed/``, rename each one with their own initials, and remember
which of the 14 OE1 series were theirs -- three chances per file to produce a name that
``afg gold agreement`` then silently fails to glob, which looks exactly like "no
disagreements" instead of like "your file is not there".

The assignment itself lives in ``config/annotation.toml``
(:func:`afg.shared.config.load_annotation_config`), the machine-readable form of
``docs/anotacion/asignacion/README.md``. Nothing here infers who annotates what.

## The three invariants

1. **``prepare`` cannot destroy work.** A target file that already contains any human
   annotation is skipped, never rewritten, unless the caller passes ``force``. Re-running
   ``afg gold prepare`` after a day of labelling is a plausible accident and must be
   harmless.
2. **Machine columns are the machine's.** ``validate`` re-reads the generated base file
   and compares every machine column cell-for-cell. A hand-edited ``earlier_text`` or
   ``evidence_text`` would corrupt the gold set invisibly -- the row still looks
   plausible, it just no longer describes the corpus.
3. **Closed sets are closed.** ``status``, ``relation``, ``direction_ok`` and
   ``confidence`` are validated against the enums in :mod:`afg.domain`, which carry the
   manual's Spanish vocabulary precisely because that is what an annotator types.

## What "half-filled" means here

Reported as an error, and deliberately narrower than "not finished" -- an untouched row is
progress-zero, not a defect:

- **Task A (decisions).** A row is *filled* when ``status`` is set. It is *half-filled*
  when (a) ``status`` is empty but some other human column is not, (b) ``status`` is
  ``decision`` but ``decision_object`` or ``decision_content`` is empty, (c) ``status`` is
  ``sin_soporte`` but ``notes`` is empty -- the manual's closing checklist requires the
  annotator to say what the evidence actually said -- or (d) ``status`` is set but
  ``annotator`` is empty.
- **Task B (candidates/recall sample).** ``relation``, ``direction_ok`` and ``confidence``
  are a unit: a row is *filled* when all three are set and *half-filled* when some but not
  all are. A half-filled row never counts toward progress.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

from afg.annotation.agreement import (
    AdjudicationEntry,
    build_adjudication_log,
    compute_series_agreement,
)
from afg.domain.decision import AnnotationStatus
from afg.domain.question import QuestionStratum
from afg.domain.relation import Confidence, DirectionOk, RelationType
from afg.shared.config import load_annotation_config
from afg.shared.csvio import open_csv_writer
from afg.shared.paths import GOLD_DECISIONS_DIR, GOLD_RELATIONS_DIR, QUESTIONS_DIR

__all__ = [
    "ADJUDICATION_UNRESOLVED",
    "AnnotationPlan",
    "Annotator",
    "IssueKind",
    "PrepareOutcome",
    "QuestionBankNotEmptyError",
    "SeriesAssignment",
    "SeriesProgress",
    "TaskKind",
    "UnknownAnnotatorError",
    "ValidationIssue",
    "ValidationReport",
    "WorkspaceFile",
    "WorkspacePaths",
    "adjudication_has_resolutions",
    "expected_files",
    "load_annotation_plan",
    "prepare_annotator_workspace",
    "question_bank_is_empty",
    "series_has_annotated_work",
    "validate_annotator",
    "write_adjudication_log",
    "write_question_bank_template",
]


class UnknownAnnotatorError(RuntimeError):
    """Raised when initials do not appear in ``config/annotation.toml``."""


class QuestionBankNotEmptyError(RuntimeError):
    """Raised when the question bank already holds written questions."""


class TaskKind(StrEnum):
    """The three kinds of file an annotator fills, named as they appear in filenames."""

    DECISIONS = "decisions"
    """Tarea A: ``<series>.decisions.<initials>.csv``."""

    CANDIDATES = "candidates"
    """Tarea B: ``<series>.candidates.<initials>.csv``."""

    RECALL_SAMPLE = "recall-sample"
    """Tarea C: ``<series>.recall-sample.<initials>.csv``."""


# --- column contracts -------------------------------------------------------------------
# Mirrors of what `write_gold_decisions_csv` and `write_candidate_pairs_csv` emit. They are
# restated rather than imported because validation's whole job is to be an INDEPENDENT
# check: importing the writer's private tuple would make a writer bug invisible here.

_DECISION_ID_COLUMN = "decision_id"
_DECISION_MACHINE_COLUMNS = (
    "meeting_id",
    "source_sentence_id",
    "sentence_text",
    "evidence_da_count",
    "evidence_text",
    "machine_flags",
)
_DECISION_HUMAN_COLUMNS = (
    "status",
    "decision_object",
    "decision_content",
    "annotator",
    "notes",
)

_PAIR_ID_COLUMN = "pair_id"
_CANDIDATE_MACHINE_COLUMNS = (
    "earlier_decision_id",
    "later_decision_id",
    "earlier_sentence_id",
    "later_sentence_id",
    "earlier_text",
    "later_text",
    "blocker_score",
)
_CANDIDATE_HUMAN_COLUMNS = ("relation", "direction_ok", "confidence", "annotator", "notes")

_QUESTION_COLUMNS = (
    "id",
    "series_id",
    "stratum",
    "text",
    "reference_answer",
    "reference_evidence",
    "author",
    "validated_by",
)

# The one human column `prepare` fills in, and the one it therefore ignores when deciding
# whether a file "contains annotation": the annotator's own initials are already in the
# filename, so writing them into every row is transcription, not judgment.
_IDENTITY_COLUMN = "annotator"

ADJUDICATION_UNRESOLVED = "`<pendiente>`"
"""Placeholder written into the two cells only the adjudicator may fill."""


# --- the plan ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SeriesAssignment:
    """One series assigned to one person, with the phase that fixes when it is annotated."""

    series_id: str
    phase: int


@dataclass(frozen=True, slots=True)
class Annotator:
    """One person and the series they annotate, per phase."""

    initials: str
    name: str
    role: str
    github: str
    phase1_series: tuple[str, ...]
    phase2_series: tuple[str, ...]
    phase3_series: tuple[str, ...]

    @property
    def annotates(self) -> bool:
        """False for the maintainer, who adjudicates and therefore never annotates."""
        return self.role == "annotator"

    @property
    def assignments(self) -> tuple[SeriesAssignment, ...]:
        """Every assigned series in execution order: phase 1, then 2, then 3."""
        if not self.annotates:
            return ()
        return tuple(
            SeriesAssignment(series_id=series_id, phase=phase)
            for phase, series_ids in (
                (1, self.phase1_series),
                (2, self.phase2_series),
                (3, self.phase3_series),
            )
            for series_id in series_ids
        )


@dataclass(frozen=True, slots=True)
class RecallSampleAssignment:
    """Tarea C: who adjudicates the blocker's rejected-pair sample, over which series."""

    owner: str
    series_id: str
    n: int
    seed: int


@dataclass(frozen=True, slots=True)
class QuestionBankAssignment:
    """OE4 question bank: who writes it, who validates it, and how big it must be."""

    author: str
    validator: str
    total_questions: int
    questions_per_stratum: int


@dataclass(frozen=True, slots=True)
class AnnotationPlan:
    """``config/annotation.toml``, parsed. The single source of truth for the split."""

    annotators: tuple[Annotator, ...]
    adjudicator: str
    phase1_series: tuple[str, ...]
    phase2_series: tuple[str, ...]
    recall_sample: RecallSampleAssignment
    question_bank: QuestionBankAssignment

    def annotator(self, initials: str) -> Annotator:
        """Look up a person by initials.

        Raises:
            UnknownAnnotatorError: with the valid initials listed, in Spanish -- an
                annotator who mistypes their own initials should be told what the
                alternatives are, not handed a KeyError.
        """
        for person in self.annotators:
            if person.initials == initials:
                return person
        known = ", ".join(person.initials for person in self.annotators)
        raise UnknownAnnotatorError(
            f"No existe el anotador {initials!r} en config/annotation.toml. "
            f"Iniciales válidas: {known}."
        )

    @property
    def double_annotated_series(self) -> tuple[str, ...]:
        """Phase 1 plus phase 2: the five series that produce a kappa and an adjudication."""
        return self.phase1_series + self.phase2_series


def load_annotation_plan(raw: Mapping[str, Any] | None = None) -> AnnotationPlan:
    """Parse ``config/annotation.toml`` into an :class:`AnnotationPlan`.

    ``raw`` is the already-loaded TOML mapping; omitted, the shipped file is read. Phase 1
    and phase 2 are declared once at the top level and apply to every annotator -- both
    people annotate those series independently, which is the whole point of them.
    """
    data = dict(raw if raw is not None else load_annotation_config())
    section = data["annotation"]
    phase1 = tuple(section["phase1_series"])
    phase2 = tuple(section["phase2_series"])

    annotators: list[Annotator] = []
    for entry in section["annotators"]:
        role = entry.get("role", "annotator")
        annotates = role == "annotator"
        annotators.append(
            Annotator(
                initials=entry["initials"],
                name=entry["name"],
                role=role,
                github=entry["github"],
                phase1_series=phase1 if annotates else (),
                phase2_series=phase2 if annotates else (),
                phase3_series=tuple(entry.get("phase3_series", ())),
            )
        )

    recall = section["recall_sample"]
    bank = section["question_bank"]
    return AnnotationPlan(
        annotators=tuple(annotators),
        adjudicator=section["adjudicator"],
        phase1_series=phase1,
        phase2_series=phase2,
        recall_sample=RecallSampleAssignment(
            owner=recall["owner"],
            series_id=recall["series"],
            n=int(recall["n"]),
            seed=int(recall["seed"]),
        ),
        question_bank=QuestionBankAssignment(
            author=bank["author"],
            validator=bank["validator"],
            total_questions=int(bank["total_questions"]),
            questions_per_stratum=int(bank["questions_per_stratum"]),
        ),
    )


# --- paths --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WorkspacePaths:
    """The three directories this module reads and writes.

    Injected rather than imported at use site so the whole test suite runs against
    ``tmp_path`` and never needs the AMI corpus or the real ``data/`` tree.
    """

    decisions_dir: Path = GOLD_DECISIONS_DIR
    relations_dir: Path = GOLD_RELATIONS_DIR
    questions_dir: Path = QUESTIONS_DIR

    def directory_for(self, kind: TaskKind) -> Path:
        return self.decisions_dir if kind is TaskKind.DECISIONS else self.relations_dir

    def source(self, kind: TaskKind, series_id: str) -> Path:
        """The machine-generated base file: ``<series>.<kind>.csv``, never hand-edited."""
        return self.directory_for(kind) / f"{series_id}.{kind.value}.csv"

    def target(self, kind: TaskKind, series_id: str, initials: str) -> Path:
        """One person's copy: ``<series>.<kind>.<initials>.csv``."""
        return self.directory_for(kind) / f"{series_id}.{kind.value}.{initials}.csv"

    def adjudication(self, series_id: str) -> Path:
        return self.relations_dir / f"{series_id}.adjudication.md"

    @property
    def question_bank(self) -> Path:
        return self.questions_dir / "banco-preguntas.csv"


@dataclass(frozen=True, slots=True)
class WorkspaceFile:
    """One file an annotator is expected to fill, and where it comes from."""

    kind: TaskKind
    series_id: str
    phase: int
    source: Path
    target: Path


# --- CSV helpers --------------------------------------------------------------------------


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV as ``(fieldnames, rows)``; missing cells normalise to ``""``."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or ())
        rows = [{name: (row.get(name) or "") for name in fieldnames} for row in reader]
    return fieldnames, rows


def _write_rows(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, str]]) -> Path:
    """Write rows through :func:`afg.shared.csvio.open_csv_writer` (LF, always)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open_csv_writer(path, encoding="utf-8") as writer:
        writer.writerow(list(fieldnames))
        for row in rows:
            writer.writerow([row.get(name, "") for name in fieldnames])
    return path


def _human_columns_for(kind: TaskKind) -> tuple[str, ...]:
    return _DECISION_HUMAN_COLUMNS if kind is TaskKind.DECISIONS else _CANDIDATE_HUMAN_COLUMNS


def _row_id_column_for(kind: TaskKind) -> str:
    return _DECISION_ID_COLUMN if kind is TaskKind.DECISIONS else _PAIR_ID_COLUMN


def _machine_columns_for(kind: TaskKind) -> tuple[str, ...]:
    return _DECISION_MACHINE_COLUMNS if kind is TaskKind.DECISIONS else _CANDIDATE_MACHINE_COLUMNS


def file_contains_annotation(path: Path, kind: TaskKind) -> bool:
    """Whether ``path`` holds any human annotation at all.

    ``annotator`` is excluded on purpose: ``prepare`` writes it itself, so counting it
    would make every prepared file look annotated and permanently jam a re-run.
    """
    if not path.exists():
        return False
    _, rows = _read_rows(path)
    columns = [c for c in _human_columns_for(kind) if c != _IDENTITY_COLUMN]
    return any(row.get(column, "").strip() for row in rows for column in columns)


def series_has_annotated_work(
    series_id: str, *, paths: WorkspacePaths | None = None
) -> tuple[Path, ...]:
    """Every derived per-annotator file for ``series_id``, across Task A and Task B, that
    already holds human annotation.

    Guards ``afg gold build`` and ``afg gold candidates``, which regenerate the machine-
    generated base file (``<series>.<kind>.csv``) from scratch by re-reading the AMI
    abstractive summary. The base itself never carries annotation -- annotators work on
    their own ``<series>.<kind>.<initials>.csv`` copy -- so this checks those derived files
    instead, the same files :func:`file_contains_annotation` already knows how to inspect.

    A non-empty result means regenerating the base would, silently:

    1. Discard any ``compuesta`` split already recorded in a derived file (manual de
       anotacion section 2) -- one summary sentence found to host several decisions, split
       into child rows, rebuilt from the original sentence the moment the base regenerates.
    2. Desynchronise that file's machine columns from the new base. ``afg gold validate``
       compares every machine column cell-for-cell against the base, so this would make
       every annotator's file fail validation for drift, through no fault of theirs.

    Returns an empty tuple, never an error, when ``series_id`` has no derived files at all
    -- the normal state before anyone has run ``afg gold prepare`` for it.
    """
    paths = paths or WorkspacePaths()
    found: list[Path] = []
    for kind in (TaskKind.DECISIONS, TaskKind.CANDIDATES):
        directory = paths.directory_for(kind)
        pattern = f"{series_id}.{kind.value}.*.csv"
        for candidate in sorted(directory.glob(pattern)):
            if file_contains_annotation(candidate, kind):
                found.append(candidate)
    return tuple(found)


# --- prepare --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PrepareOutcome:
    """What ``afg gold prepare`` did, split by what happened to each file."""

    initials: str
    is_maintainer: bool
    created: tuple[WorkspaceFile, ...]
    skipped_annotated: tuple[WorkspaceFile, ...]
    overwritten: tuple[WorkspaceFile, ...]
    missing_sources: tuple[WorkspaceFile, ...]


def expected_files(
    plan: AnnotationPlan, annotator: Annotator, paths: WorkspacePaths
) -> list[WorkspaceFile]:
    """Every file this person must fill, in execution order: phase 1 before phase 2 before
    phase 3, and within one series Task A (decisions) before Task B (candidates).

    Both Task A and Task B files carry the initials in every phase, including phase 3
    where only one person annotates: the filename should always answer "who labelled
    this", and a name whose shape depends on the phase is a name somebody will get wrong.

    Public because :func:`afg.annotation.setup.run_setup` reuses this exact order to name
    the first file an annotator should open -- computing it a second, slightly different
    way would be a second place for that order to drift from ``prepare``'s.
    """
    files: list[WorkspaceFile] = []
    for assignment in annotator.assignments:
        for kind in (TaskKind.DECISIONS, TaskKind.CANDIDATES):
            files.append(
                WorkspaceFile(
                    kind=kind,
                    series_id=assignment.series_id,
                    phase=assignment.phase,
                    source=paths.source(kind, assignment.series_id),
                    target=paths.target(kind, assignment.series_id, annotator.initials),
                )
            )
    recall = plan.recall_sample
    if recall.owner == annotator.initials:
        files.append(
            WorkspaceFile(
                kind=TaskKind.RECALL_SAMPLE,
                series_id=recall.series_id,
                phase=3,
                source=paths.source(TaskKind.RECALL_SAMPLE, recall.series_id),
                target=paths.target(TaskKind.RECALL_SAMPLE, recall.series_id, annotator.initials),
            )
        )
    return files


def prepare_annotator_workspace(
    plan: AnnotationPlan,
    initials: str,
    *,
    paths: WorkspacePaths | None = None,
    force: bool = False,
) -> PrepareOutcome:
    """Create every file ``initials`` must fill: correctly named, machine columns intact,
    human columns empty.

    A target that already contains annotation is left byte-for-byte alone and reported in
    ``skipped_annotated`` -- unless ``force``, which is the only way to lose work here and
    exists for the case where a base file was regenerated and the copy is genuinely stale.
    A missing source is reported in ``missing_sources``; the remaining files are still
    prepared, because one ungenerated series should not block the other four.

    Raises:
        UnknownAnnotatorError: if ``initials`` is not in the plan.
    """
    paths = paths or WorkspacePaths()
    annotator = plan.annotator(initials)
    if not annotator.annotates:
        return PrepareOutcome(
            initials=initials,
            is_maintainer=True,
            created=(),
            skipped_annotated=(),
            overwritten=(),
            missing_sources=(),
        )

    created: list[WorkspaceFile] = []
    skipped: list[WorkspaceFile] = []
    overwritten: list[WorkspaceFile] = []
    missing: list[WorkspaceFile] = []

    for workspace_file in expected_files(plan, annotator, paths):
        if not workspace_file.source.exists():
            missing.append(workspace_file)
            continue
        had_annotation = file_contains_annotation(workspace_file.target, workspace_file.kind)
        if had_annotation and not force:
            skipped.append(workspace_file)
            continue

        fieldnames, rows = _read_rows(workspace_file.source)
        human = _human_columns_for(workspace_file.kind)
        for row in rows:
            for column in human:
                row[column] = initials if column == _IDENTITY_COLUMN else ""
        _write_rows(workspace_file.target, fieldnames, rows)
        (overwritten if had_annotation else created).append(workspace_file)

    return PrepareOutcome(
        initials=initials,
        is_maintainer=False,
        created=tuple(created),
        skipped_annotated=tuple(skipped),
        overwritten=tuple(overwritten),
        missing_sources=tuple(missing),
    )


# --- validate -------------------------------------------------------------------------------


class IssueKind(StrEnum):
    """Why an issue was raised. Lets the status table tell "not started" from "broken"."""

    MISSING_FILE = "missing_file"
    """The workspace file (or its base) is not there at all -- nobody ran `prepare` yet."""

    CONTENT = "content"
    """The file exists and something in it is wrong."""


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One thing wrong, located precisely enough to fix without searching."""

    path: Path
    row_id: str
    column: str
    value: str
    message: str
    kind: IssueKind = IssueKind.CONTENT


@dataclass(frozen=True, slots=True)
class SeriesProgress:
    """How far one person is through one series, and what is wrong with it."""

    series_id: str
    phase: int
    decisions_filled: int
    decisions_total: int
    candidates_filled: int
    candidates_total: int
    issues: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues

    @property
    def not_started(self) -> bool:
        """Nothing is wrong except that the files do not exist yet.

        Distinct from ``ok``: `validate` must still fail, because an annotator cannot open
        a pull request for files that are not there. But the maintainer's status table
        should say "sin preparar", not accuse someone of two errors for not having started.
        """
        return bool(self.issues) and all(
            issue.kind is IssueKind.MISSING_FILE for issue in self.issues
        )

    @property
    def complete(self) -> bool:
        return (
            self.decisions_total > 0
            and self.decisions_filled == self.decisions_total
            and self.candidates_filled == self.candidates_total
        )


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """The gate an annotator runs before opening a pull request."""

    initials: str
    series: tuple[SeriesProgress, ...]

    @property
    def issues(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for progress in self.series for issue in progress.issues)

    @property
    def ok(self) -> bool:
        return not self.issues


_CLOSED_SETS: dict[str, type[StrEnum]] = {
    "status": AnnotationStatus,
    "relation": RelationType,
    "direction_ok": DirectionOk,
    "confidence": Confidence,
}


def _legal_values(column: str) -> list[str]:
    return [member.value for member in _CLOSED_SETS[column]]


def _check_closed_set(path: Path, row_id: str, column: str, value: str) -> ValidationIssue | None:
    if not value or value in _legal_values(column):
        return None
    return ValidationIssue(
        path=path,
        row_id=row_id,
        column=column,
        value=value,
        message=(
            f"{path.name}, fila {row_id}: {column}={value!r} no pertenece al conjunto "
            f"cerrado. Valores permitidos: {', '.join(_legal_values(column))}."
        ),
    )


def _parent_decision_id(decision_id: str) -> str:
    """The parent of a ``compuesta`` child row, e.g. ``ES2015a.d01-2`` -> ``ES2015a.d01``.

    Returns ``decision_id`` unchanged when it carries no ``-N`` suffix.
    """
    head, separator, tail = decision_id.rpartition("-")
    if separator and tail.isdigit() and head:
        return head
    return decision_id


def _check_machine_columns(
    path: Path,
    kind: TaskKind,
    rows: Sequence[Mapping[str, str]],
    reference: Mapping[str, Mapping[str, str]],
) -> list[ValidationIssue]:
    """Compare every machine column against the generated base file.

    This is the check that matters most: a hand-edited ``earlier_text`` or
    ``evidence_text`` leaves a row that still reads plausibly but no longer describes the
    corpus, so nothing downstream can notice. ``compuesta`` child rows (``-1``, ``-2``)
    are matched against their PARENT, since they are legitimately new ids that must still
    inherit the parent's machine columns verbatim.
    """
    id_column = _row_id_column_for(kind)
    machine = _machine_columns_for(kind)
    issues: list[ValidationIssue] = []
    seen: set[str] = set()

    for row in rows:
        row_id = row.get(id_column, "").strip()
        if not row_id:
            issues.append(
                ValidationIssue(
                    path=path,
                    row_id="(sin id)",
                    column=id_column,
                    value="",
                    message=f"{path.name}: hay una fila sin {id_column}. No se puede validar.",
                )
            )
            continue

        lookup_id = row_id if row_id in reference else _parent_decision_id(row_id)
        expected = reference.get(lookup_id)
        if expected is None:
            issues.append(
                ValidationIssue(
                    path=path,
                    row_id=row_id,
                    column=id_column,
                    value=row_id,
                    message=(
                        f"{path.name}, fila {row_id}: ese id no existe en el archivo base "
                        f"{path.name.replace(f'.{kind.value}.', f'.{kind.value}.')}. "
                        "Las filas nuevas solo son válidas como hijas de una fila "
                        "`compuesta`, con el sufijo -1, -2, ..."
                    ),
                )
            )
            continue

        seen.add(lookup_id)
        for column in machine:
            actual_value = row.get(column, "")
            expected_value = expected.get(column, "")
            if actual_value != expected_value:
                issues.append(
                    ValidationIssue(
                        path=path,
                        row_id=row_id,
                        column=column,
                        value=actual_value,
                        message=(
                            f"{path.name}, fila {row_id}: la columna de máquina {column!r} "
                            f"fue modificada. Valor esperado: {expected_value!r}; valor "
                            f"encontrado: {actual_value!r}. Restaura el valor original: "
                            "editar una columna de máquina corrompe el conjunto de "
                            "referencia sin dejar rastro."
                        ),
                    )
                )

    for missing_id in reference:
        if missing_id not in seen:
            issues.append(
                ValidationIssue(
                    path=path,
                    row_id=missing_id,
                    column=id_column,
                    value="",
                    message=(
                        f"{path.name}: falta la fila {missing_id}, que sí está en el "
                        "archivo base. No se borra ninguna fila: las `no_decision` se "
                        "conservan porque miden falsos positivos."
                    ),
                )
            )
    return issues


def _check_decision_row(path: Path, row: Mapping[str, str]) -> tuple[bool, list[ValidationIssue]]:
    """Validate one Task-A row. Returns ``(is_filled, issues)``."""
    row_id = row.get(_DECISION_ID_COLUMN, "").strip()
    status = row.get("status", "").strip()
    decision_object = row.get("decision_object", "").strip()
    decision_content = row.get("decision_content", "").strip()
    annotator = row.get("annotator", "").strip()
    notes = row.get("notes", "").strip()
    issues: list[ValidationIssue] = []

    closed_set_issue = _check_closed_set(path, row_id, "status", status)
    if closed_set_issue is not None:
        issues.append(closed_set_issue)

    if not status:
        if decision_object or decision_content or notes:
            issues.append(
                ValidationIssue(
                    path=path,
                    row_id=row_id,
                    column="status",
                    value="",
                    message=(
                        f"{path.name}, fila {row_id}: la fila está a medio llenar -- tiene "
                        "contenido humano pero `status` vacío. Toda fila anotada necesita "
                        "`status`."
                    ),
                )
            )
        return False, issues

    if status == AnnotationStatus.DECISION.value:
        for column, value in (
            ("decision_object", decision_object),
            ("decision_content", decision_content),
        ):
            if not value:
                issues.append(
                    ValidationIssue(
                        path=path,
                        row_id=row_id,
                        column=column,
                        value="",
                        message=(
                            f"{path.name}, fila {row_id}: `status = decision` exige "
                            f"`{column}` (manual §7). Está vacía."
                        ),
                    )
                )

    if status == AnnotationStatus.SIN_SOPORTE.value and not notes:
        issues.append(
            ValidationIssue(
                path=path,
                row_id=row_id,
                column="notes",
                value="",
                message=(
                    f"{path.name}, fila {row_id}: `status = sin_soporte` exige que `notes` "
                    "explique qué dice realmente la evidencia (manual §7)."
                ),
            )
        )

    if not annotator:
        issues.append(
            ValidationIssue(
                path=path,
                row_id=row_id,
                column="annotator",
                value="",
                message=(
                    f"{path.name}, fila {row_id}: `annotator` está vacío en una fila "
                    "anotada. Sin él, la fila no dice quién puso la etiqueta."
                ),
            )
        )

    return True, issues


def _check_candidate_row(path: Path, row: Mapping[str, str]) -> tuple[bool, list[ValidationIssue]]:
    """Validate one Task-B/C row. Returns ``(is_filled, issues)``."""
    row_id = row.get(_PAIR_ID_COLUMN, "").strip()
    values = {
        column: row.get(column, "").strip() for column in ("relation", "direction_ok", "confidence")
    }
    annotator = row.get("annotator", "").strip()
    issues: list[ValidationIssue] = []

    for column, value in values.items():
        closed_set_issue = _check_closed_set(path, row_id, column, value)
        if closed_set_issue is not None:
            issues.append(closed_set_issue)

    filled = [column for column, value in values.items() if value]
    if not filled:
        return False, issues

    for column, value in values.items():
        if not value:
            issues.append(
                ValidationIssue(
                    path=path,
                    row_id=row_id,
                    column=column,
                    value="",
                    message=(
                        f"{path.name}, fila {row_id}: la fila está a medio llenar -- "
                        f"`{column}` está vacía. `relation`, `direction_ok` y `confidence` "
                        "van juntas en toda fila adjudicada (manual §7)."
                    ),
                )
            )

    if not annotator:
        issues.append(
            ValidationIssue(
                path=path,
                row_id=row_id,
                column="annotator",
                value="",
                message=(
                    f"{path.name}, fila {row_id}: `annotator` está vacío en una fila adjudicada."
                ),
            )
        )

    return len(filled) == len(values), issues


def _validate_file(
    path: Path, source: Path, kind: TaskKind
) -> tuple[int, int, list[ValidationIssue]]:
    """Validate one workspace file. Returns ``(filled, total, issues)``."""
    if not path.exists():
        return (
            0,
            0,
            [
                ValidationIssue(
                    path=path,
                    row_id="-",
                    column="-",
                    value="",
                    kind=IssueKind.MISSING_FILE,
                    message=(
                        f"Falta {path.name}. Ejecuta `uv run afg gold prepare "
                        f"--annotator {path.stem.rsplit('.', 1)[-1]}` para crearlo."
                    ),
                )
            ],
        )
    if not source.exists():
        return (
            0,
            0,
            [
                ValidationIssue(
                    path=path,
                    row_id="-",
                    column="-",
                    value="",
                    kind=IssueKind.MISSING_FILE,
                    message=(
                        f"Falta el archivo base {source.name}, así que no se pueden "
                        "verificar las columnas de máquina. Regenéralo con "
                        f"`uv run afg gold {kind.value} --series {source.name.split('.')[0]}`."
                    ),
                )
            ],
        )

    _, rows = _read_rows(path)
    _, reference_rows = _read_rows(source)
    id_column = _row_id_column_for(kind)
    reference = {row[id_column]: row for row in reference_rows if row.get(id_column, "").strip()}

    issues = _check_machine_columns(path, kind, rows, reference)
    check_row = _check_decision_row if kind is TaskKind.DECISIONS else _check_candidate_row
    filled = 0
    for row in rows:
        is_filled, row_issues = check_row(path, row)
        filled += int(is_filled)
        issues.extend(row_issues)
    return filled, len(rows), issues


def validate_annotator(
    plan: AnnotationPlan,
    initials: str,
    *,
    paths: WorkspacePaths | None = None,
    series: str | None = None,
) -> ValidationReport:
    """Validate one person's whole workspace, or one series of it.

    Three kinds of check, per file: closed-set legality, half-filled rows, and machine
    columns against the generated base file. The recall sample, when this person owns it,
    is validated with the Task-B rules -- the manual adjudicates it by the same rules.

    Raises:
        UnknownAnnotatorError: if ``initials`` is not in the plan.
        ValueError: if ``series`` is not assigned to this person, in Spanish -- silently
            reporting an empty result for a mistyped series would read as "all clear".
    """
    paths = paths or WorkspacePaths()
    annotator = plan.annotator(initials)
    assignments = annotator.assignments
    if series is not None:
        assignments = tuple(a for a in assignments if a.series_id == series)
        if not assignments:
            assigned = ", ".join(a.series_id for a in annotator.assignments) or "(ninguna)"
            raise ValueError(
                f"La serie {series!r} no está asignada a {initials!r}. "
                f"Series asignadas: {assigned}."
            )

    recall = plan.recall_sample
    progresses: list[SeriesProgress] = []
    for assignment in assignments:
        decisions_filled, decisions_total, issues = _validate_file(
            paths.target(TaskKind.DECISIONS, assignment.series_id, initials),
            paths.source(TaskKind.DECISIONS, assignment.series_id),
            TaskKind.DECISIONS,
        )
        candidates_filled, candidates_total, candidate_issues = _validate_file(
            paths.target(TaskKind.CANDIDATES, assignment.series_id, initials),
            paths.source(TaskKind.CANDIDATES, assignment.series_id),
            TaskKind.CANDIDATES,
        )
        issues = [*issues, *candidate_issues]

        if recall.owner == initials and recall.series_id == assignment.series_id:
            _, _, recall_issues = _validate_file(
                paths.target(TaskKind.RECALL_SAMPLE, recall.series_id, initials),
                paths.source(TaskKind.RECALL_SAMPLE, recall.series_id),
                TaskKind.RECALL_SAMPLE,
            )
            issues.extend(recall_issues)

        progresses.append(
            SeriesProgress(
                series_id=assignment.series_id,
                phase=assignment.phase,
                decisions_filled=decisions_filled,
                decisions_total=decisions_total,
                candidates_filled=candidates_filled,
                candidates_total=candidates_total,
                issues=tuple(issues),
            )
        )

    return ValidationReport(initials=initials, series=tuple(progresses))


# --- adjudicate -------------------------------------------------------------------------


def adjudication_has_resolutions(path: Path) -> bool:
    """Whether an adjudication log already carries human resolutions.

    A generated log has exactly two unresolved placeholders per disagreement row ("etiqueta
    final" and "razón"). If any table row that names a pair or decision id has lost a
    placeholder, a human has filled something in and the file must not be regenerated.
    """
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or ADJUDICATION_UNRESOLVED in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 5 and cells[0].startswith("`") and not cells[0].startswith("`<"):
            return True
    return False


def _disagreement_rows(entries: Sequence[AdjudicationEntry]) -> list[str]:
    return [
        f"| `{entry.item_id}` | `{entry.label_a or '(vacío)'}` | `{entry.label_b or '(vacío)'}` "
        f"| {ADJUDICATION_UNRESOLVED} | {ADJUDICATION_UNRESOLVED} |"
        for entry in entries
    ]


def _kappa_cell(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def write_adjudication_log(
    plan: AnnotationPlan,
    series_id: str,
    *,
    paths: WorkspacePaths | None = None,
    force: bool = False,
    today: date | None = None,
) -> Path:
    """Write ``<series>.adjudication.md`` pre-filled from the two annotator files.

    Computes the three independent kappas (:func:`~afg.annotation.agreement.
    compute_series_agreement`) and wires :func:`~afg.annotation.agreement.
    build_adjudication_log`, which existed with tests but had no caller. Every column the
    machine can know is filled: series, annotators, adjudicator, the three kappas, and one
    table row per disagreement with both labels already in place. The human fills exactly
    two cells per row -- "etiqueta final" and "razón" -- and the latter is the point: a
    list of verdicts without criteria cannot be applied to the next series.

    Follows ``docs/anotacion/plantilla-adjudicacion.md``. The Task-A ``status`` table is
    emitted empty, because ``afg gold agreement`` does not compute that axis
    (``asignacion/README.md`` §5.2) and inventing rows for it would be a lie.

    Raises:
        FileNotFoundError: fewer than two annotator files for this series.
        FileExistsError: the log already has resolutions and ``force`` is not set.
    """
    paths = paths or WorkspacePaths()
    out_path = paths.adjudication(series_id)
    if not force and adjudication_has_resolutions(out_path):
        raise FileExistsError(
            f"{out_path.name} ya tiene resoluciones escritas a mano. No se regenera: "
            f"perderías el criterio registrado de la serie {series_id}. Usa --force solo "
            "si de verdad quieres descartarlo."
        )

    annotator_paths = sorted(paths.relations_dir.glob(f"{series_id}.candidates.*.csv"))
    if len(annotator_paths) < 2:
        raise FileNotFoundError(
            f"Se necesitan al menos 2 archivos "
            f"data/processed/relations/{series_id}.candidates.<iniciales>.csv para "
            f"adjudicar la serie {series_id} (hay {len(annotator_paths)}). Cada anotador "
            "crea el suyo con `uv run afg gold prepare --annotator <iniciales>`."
        )

    result = compute_series_agreement(annotator_paths)
    rows_by_annotator = {}
    for path in annotator_paths[:2]:
        _, rows = _read_rows(path)
        rows_by_annotator[path.name.removesuffix(".csv").rsplit(".", 1)[-1]] = {
            row[_PAIR_ID_COLUMN]: row for row in rows if row.get(_PAIR_ID_COLUMN, "").strip()
        }

    rows_a = rows_by_annotator[result.annotator_a]
    rows_b = rows_by_annotator[result.annotator_b]
    common_ids = sorted(set(rows_a) & set(rows_b))

    relation_entries = build_adjudication_log(
        common_ids,
        [rows_a[pair_id].get("relation", "").strip() for pair_id in common_ids],
        [rows_b[pair_id].get("relation", "").strip() for pair_id in common_ids],
        annotator_a=result.annotator_a,
        annotator_b=result.annotator_b,
    )
    direction_entries = build_adjudication_log(
        common_ids,
        [rows_a[pair_id].get("direction_ok", "").strip() for pair_id in common_ids],
        [rows_b[pair_id].get("direction_ok", "").strip() for pair_id in common_ids],
        annotator_a=result.annotator_a,
        annotator_b=result.annotator_b,
    )

    names = {person.initials: person.name for person in plan.annotators}
    phase = 1 if series_id in plan.phase1_series else 2
    reported = "no — la calibración es diagnóstica" if phase == 1 else "sí"
    empty_row = (
        f"| {ADJUDICATION_UNRESOLVED} | {ADJUDICATION_UNRESOLVED} | "
        f"{ADJUDICATION_UNRESOLVED} | {ADJUDICATION_UNRESOLVED} | "
        f"{ADJUDICATION_UNRESOLVED} |"
    )

    lines = [
        f"# Adjudicación — `{series_id}`",
        "",
        "> Generado por `uv run afg gold adjudicate --series "
        f"{series_id}`. Las cabeceras y los desacuerdos ya están puestos; solo faltan las "
        "columnas **etiqueta final** y **razón**, que son decisión humana.",
        "",
        "| | |",
        "|---|---|",
        f"| **Serie** | `{series_id}` |",
        f"| **Fecha de la sesión** | `{(today or date.today()).isoformat()}` |",
        "| **Anotadores** | "
        f"`{result.annotator_a}` ({names.get(result.annotator_a, '?')}), "
        f"`{result.annotator_b}` ({names.get(result.annotator_b, '?')}) |",
        f"| **Adjudicador** | `{plan.adjudicator}` ({names.get(plan.adjudicator, '?')}) |",
        f"| **Fase** | `{phase}` |",
        f"| **¿Se reporta en la tesis?** | `{reported}` |",
        "",
        "## Kappas",
        "",
        f"Salida de `uv run afg gold agreement --series {series_id}`. Los tres ejes van "
        "**por separado, nunca combinados**: `existence` y `direction` pueden ser perfectos "
        "mientras `type` no lo es, y colapsarlos escondería el modo de falla de H3 que la "
        "tesis mide.",
        "",
        "| Eje | κ | Ítems | Desacuerdos |",
        "|---|---:|---:|---:|",
        f"| Existencia del enlace | {_kappa_cell(result.existence_kappa)} | "
        f"{result.n_items} | {len(result.existence_disagreements)} |",
        f"| Tipo de relación | {_kappa_cell(result.type_kappa)} | "
        f"{result.n_type_items} | {len(result.type_disagreements)} |",
        f"| Dirección | {_kappa_cell(result.direction_kappa)} | "
        f"{result.n_items} | {len(result.direction_disagreements)} |",
        "",
        "El kappa se reporta **tal como salga**. Un kappa bajo es el resultado que OE1 se "
        "propuso medir, no un fracaso a esconder (manual §6).",
        "",
        "## Desacuerdos de la Tarea B — relaciones",
        "",
        "La columna **Razón** es el contenido real del registro: sin ella queda una lista "
        "de veredictos sin criterio, y el criterio es lo que hay que poder aplicar igual en "
        "la serie siguiente.",
        "",
        f"| Par | Etiqueta de `{result.annotator_a}` | Etiqueta de `{result.annotator_b}` "
        "| Etiqueta final | Razón |",
        "|---|---|---|---|---|",
        *(_disagreement_rows(relation_entries) or [empty_row]),
        "",
        "### Desacuerdos de dirección",
        "",
        "Una dirección invertida es una falla distinta de una etiqueta equivocada, y la "
        "tesis las puntúa por separado (H3).",
        "",
        f"| Par | `direction_ok` de `{result.annotator_a}` | `direction_ok` de "
        f"`{result.annotator_b}` | Final | Razón |",
        "|---|---|---|---|---|",
        *(_disagreement_rows(direction_entries) or [empty_row]),
        "",
        "## Desacuerdos de la Tarea A — `status` de las decisiones",
        "",
        "**`afg gold agreement` no cubre esta tabla** (`asignacion/README.md` §5.2): sus "
        "tres kappas son todos de la Tarea B. El acuerdo sobre `status` se adjudica "
        f"leyendo a mano `{series_id}.decisions.{result.annotator_a}.csv` y "
        f"`{series_id}.decisions.{result.annotator_b}.csv`, alineados por `decision_id`. "
        "Esta tabla se llena a mano por esa razón, no por olvido.",
        "",
        f"| Decisión | `status` de `{result.annotator_a}` | `status` de "
        f"`{result.annotator_b}` | `status` final | Razón |",
        "|---|---|---|---|---|",
        empty_row,
        "",
        "### Divisiones de filas `compuesta`",
        "",
        "Cuando una persona dividió una frase en N hijas y la otra en M, los `decision_id` "
        "hijos no coinciden y no hay nada que alinear. Se resuelve sobre la fila **madre**.",
        "",
        "| Decisión madre | División de "
        f"`{result.annotator_a}` | División de `{result.annotator_b}` | División final | "
        "Razón |",
        "|---|---|---|---|---|",
        empty_row,
        "",
        "## Cierre — ¿revela esto un vacío de la guía?",
        "",
        "Si dos personas competentes discreparon, la primera hipótesis es que **la guía no "
        "decidía el caso**, no que una de las dos se equivocó (tesis §1.4).",
        "",
        "1. **¿Hay un patrón?** Un desacuerdo aislado es ruido; tres en el mismo borde son "
        "un vacío.",
        "   > `<respuesta>`",
        "",
        "2. **¿Qué corrección concreta hace falta?** Cita el documento y la sección.",
        '   > `<respuesta, o "ninguna">`',
        "",
        "3. **¿Se corrigió antes de abrir la serie siguiente?**",
        "   > `<sí / no aplica — enlace al PR de corrección>`",
        "",
        "## Artefactos de esta sesión",
        "",
        f"- [ ] `data/processed/relations/{series_id}.adjudication.md` (este archivo)",
        f"- [ ] `reports/tables/{series_id}.agreement.csv`",
        '- [ ] PR de corrección de la guía, si el cierre lo pidió: `<enlace o "no aplica">`',
        "",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# --- question bank ---------------------------------------------------------------------


def question_bank_is_empty(path: Path) -> bool:
    """Whether the bank holds no written question yet.

    ``id``, ``stratum`` and ``author`` are machine-written, so only the columns a human
    types -- question text, reference answer, evidence, validation -- count as content.
    """
    if not path.exists():
        return True
    _, rows = _read_rows(path)
    human = ("text", "reference_answer", "reference_evidence", "validated_by", "series_id")
    return not any(row.get(column, "").strip() for row in rows for column in human)


def write_question_bank_template(
    out_path: Path,
    *,
    total: int = 100,
    per_stratum: int = 25,
    author: str = "",
    force: bool = False,
) -> Path:
    """Write the question bank pre-numbered and pre-stratified, with every text empty.

    ``total`` rows, ``per_stratum`` of each :class:`~afg.domain.question.QuestionStratum`,
    in thesis-table order (E1, E2, E3, E4). The author types question text into rows that
    already exist; he never invents an id and never types a stratum, which is what used to
    make an under-filled stratum discoverable only by counting at the end.

    ``id`` is ``q001``..``q<total>`` and carries NO series prefix, unlike the worked
    examples in ``_plantilla-banco-preguntas.csv`` (``ES2015.q001``). The series is not
    knowable at init time -- it is the author's choice per question -- so ``series_id`` is
    left empty for him to fill and the id stays bank-global rather than encoding a series
    that may turn out to be a different one.

    Raises:
        QuestionBankNotEmptyError: the bank already holds written questions and ``force``
            is not set.
        ValueError: ``total`` is not ``per_stratum`` times the number of strata.
    """
    expected_total = per_stratum * len(QuestionStratum)
    if total != expected_total:
        raise ValueError(
            f"total={total} no cuadra con {per_stratum} preguntas por cada uno de los "
            f"{len(QuestionStratum)} estratos (serían {expected_total})."
        )
    if not force and not question_bank_is_empty(out_path):
        raise QuestionBankNotEmptyError(
            f"{out_path.name} ya tiene preguntas escritas. No se regenera: perderías el "
            "banco. Usa --force solo si de verdad quieres descartarlo."
        )

    rows: list[dict[str, str]] = []
    number = 0
    for stratum in QuestionStratum:
        for _ in range(per_stratum):
            number += 1
            rows.append(
                {
                    "id": f"q{number:03d}",
                    "series_id": "",
                    "stratum": stratum.value,
                    "text": "",
                    "reference_answer": "",
                    "reference_evidence": "",
                    "author": author,
                    "validated_by": "",
                }
            )
    return _write_rows(out_path, _QUESTION_COLUMNS, rows)
