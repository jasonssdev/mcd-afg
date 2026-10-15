"""Loader and validator of the real question bank (thesis section 5.5).

The bank is ``data/processed/questions/banco-preguntas.csv``: 115 rows pre-numbered
(``q001``..``q115``; E3 has room for 40 questions, the other strata for 25) and pre-stratified,
written by one person and validated by another (CONTRIBUTING.md section 1). While it is
being written most rows are *pending*; the loader therefore works on partial banks: only rows
validated by someone other than the author become :class:`~afg.domain.question.Question`
objects, and the rest are reported, not loaded.

Rows beyond a stratum's minimum that are still completely blank (no text, answer, evidence,
series or notes, and no validator) are *optional*: they are reported as unused, never block,
and are ignored by the Experiment B loader.

Validation never stops at the first problem. It returns a :class:`QuestionBankReport` with
one :class:`QuestionBankIssue` per problem and row. Blocking errors make a bank unfit to run;
warnings only inform. Messages are Spanish because the annotation team reads them.

Question ids stay bank-global (``q001``); nothing downstream parses them (the runner, the
judge and the records treat ids as opaque keys), so no series prefix is added.
"""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Collection
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question, QuestionStratum, parse_reference_evidence
from afg.shared.config import load_corpus_config, load_experiments_config
from afg.shared.csvio import CsvFormatError, open_csv_reader, semicolon_hint

BANK_COLUMNS = (
    "id",
    "series_id",
    "stratum",
    "text",
    "reference_answer",
    "reference_evidence",
    "author",
    "validated_by",
    "validation_notes",
)


class Severity(StrEnum):
    """``ERROR`` blocks running the bank; ``WARNING`` only informs."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class QuestionBankIssue:
    """One problem found in one row (``row_id`` is ``"-"`` for bank-wide problems)."""

    row_id: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class QuestionBankReport:
    """Outcome of loading a bank: usable questions, pending rows and every problem."""

    usable: tuple[Question, ...]
    pending_ids: tuple[str, ...]
    optional_ids: tuple[str, ...]
    issues: tuple[QuestionBankIssue, ...]
    usable_per_stratum: dict[QuestionStratum, int]
    total_rows: int

    @property
    def errors(self) -> tuple[QuestionBankIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[QuestionBankIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.WARNING)

    @property
    def has_errors(self) -> bool:
        return any(i.severity is Severity.ERROR for i in self.issues)


def is_question_bank(path: Path) -> bool:
    """Whether ``path`` has the question bank header (``text`` and ``validated_by``)."""
    with open_csv_reader(path) as handle:
        header = next(csv.reader(handle), [])
    hint = semicolon_hint(path, header)
    if hint:
        raise CsvFormatError(hint)
    return "text" in header and "validated_by" in header


_HUMAN_COLUMNS = ("text", "reference_answer", "reference_evidence", "series_id", "validation_notes")


def _is_blank(row: dict[str, str]) -> bool:
    """Whether no human has typed anything in the row (machine columns aside)."""
    return not any(row[column].strip() for column in _HUMAN_COLUMNS)


def _meeting_belongs(meeting_id: str, series: str, letters: Collection[str]) -> bool:
    return (
        meeting_id.startswith(series)
        and len(meeting_id) == len(series) + 1
        and meeting_id[len(series)] in letters
    )


def _check_content(
    row: dict[str, str],
    stratum: QuestionStratum | None,
    study_series: Collection[str],
    letters: Collection[str],
) -> tuple[list[str], tuple[EvidenceSpan, ...]]:
    """Content problems of a validated row, and its parsed evidence."""
    problems: list[str] = []
    series = row["series_id"].strip()
    if not row["text"].strip():
        problems.append("texto de la pregunta vacío.")
    if not series:
        problems.append("serie vacía.")
    elif series not in study_series:
        problems.append(f"la serie {series!r} no es una de las series del estudio.")

    spans: tuple[EvidenceSpan, ...] = ()
    try:
        spans = parse_reference_evidence(row["reference_evidence"])
    except ValueError as exc:
        problems.append(f"evidencia mal formada: {exc}")
    if series:
        for span in spans:
            if not _meeting_belongs(span.meeting_id, series, letters):
                problems.append(
                    f"evidencia: la reunión {span.meeting_id!r} no pertenece a la serie {series!r}."
                )

    answer = row["reference_answer"].strip()
    has_evidence = bool(row["reference_evidence"].strip())
    if stratum is QuestionStratum.E4_UNANSWERABLE:
        if answer:
            problems.append("una E4 (incontestable) no lleva respuesta de referencia.")
        if has_evidence:
            problems.append("una E4 (incontestable) no lleva evidencia de referencia.")
    elif stratum is not None:
        if not answer:
            problems.append("falta la respuesta de referencia.")
        if not has_evidence:
            problems.append("falta la evidencia de referencia.")
    return problems, spans


def load_question_bank(
    path: Path,
    *,
    study_series: Collection[str],
    meeting_letters: Collection[str],
    min_per_stratum: int = 0,
    require_complete: bool = False,
) -> QuestionBankReport:
    """Load ``path`` and validate it row by row.

    Structural problems (empty or duplicate id, unknown stratum, missing author) block on
    every row, pending or not, because those columns are machine-written. Content checks
    run on rows that carry a ``validated_by``. A row whose validator equals its author is a
    blocking error and is never usable. A row without validator is *pending*; with
    ``require_complete`` it is a blocking error instead.

    The per-stratum minimum counts validated rows: a warning on a partial bank (the bank is
    still being written), a blocking error with ``require_complete``.

    With a positive ``min_per_stratum``, a completely blank unvalidated row of a stratum that
    already reached the minimum is *optional* (an unused extra row): it is listed in
    ``optional_ids``, is neither pending nor an error, and is never loaded. Below the minimum
    the same row stays pending (or a blocking error with ``require_complete``).

    Raises:
        ValueError: if the file lacks a bank column.
        FileNotFoundError: if ``path`` does not exist.
    """
    with open_csv_reader(path) as handle:
        reader = csv.DictReader(handle)
        hint = semicolon_hint(path, reader.fieldnames or [])
        if hint:
            raise CsvFormatError(hint)
        missing = [c for c in BANK_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: faltan columnas del banco: {missing}.")
        rows = [{c: (r.get(c) or "") for c in BANK_COLUMNS} for r in reader]

    issues: list[QuestionBankIssue] = []
    usable: list[Question] = []
    pending: list[str] = []
    blank_rows: list[tuple[str, str, QuestionStratum]] = []
    seen: set[str] = set()
    counts: Counter[QuestionStratum] = Counter()

    for number, row in enumerate(rows, start=2):
        row_id = row["id"].strip()
        label = row_id or f"(línea {number})"
        found: list[tuple[Severity, str]] = []

        if not row_id:
            found.append((Severity.ERROR, "id vacío."))
        elif row_id in seen:
            found.append((Severity.ERROR, "id duplicado."))
        seen.add(row_id)

        stratum: QuestionStratum | None
        try:
            stratum = QuestionStratum(row["stratum"].strip())
        except ValueError:
            stratum = None
            found.append((Severity.ERROR, f"estrato desconocido {row['stratum']!r}."))

        author = row["author"].strip()
        validator = row["validated_by"].strip()
        notes = row["validation_notes"].strip()
        if not author:
            found.append((Severity.ERROR, "falta el autor."))

        is_pending = not validator
        spans: tuple[EvidenceSpan, ...] = ()
        if is_pending:
            if min_per_stratum > 0 and stratum is not None and _is_blank(row) and not found:
                blank_rows.append((row_id, label, stratum))
                continue
            if require_complete:
                found.append((Severity.ERROR, "sin validar (falta validated_by)."))
            else:
                pending.append(row_id)
        else:
            if validator == author:
                found.append((Severity.ERROR, "el validador no puede ser el autor."))
            content, spans = _check_content(row, stratum, study_series, meeting_letters)
            found.extend((Severity.ERROR, message) for message in content)
            if notes:
                found.append(
                    (
                        Severity.WARNING,
                        "validada pero conserva validation_notes; el autor la limpia.",
                    )
                )

        issues.extend(QuestionBankIssue(label, sev, msg) for sev, msg in found)
        if (
            not is_pending
            and stratum is not None
            and not any(sev is Severity.ERROR for sev, _ in found)
        ):
            counts[stratum] += 1
            usable.append(
                Question(
                    id=row_id,
                    series_id=row["series_id"].strip(),
                    stratum=stratum,
                    text=row["text"].strip(),
                    reference_answer=row["reference_answer"].strip() or None,
                    reference_evidence=spans,
                    author=author,
                    validated_by=validator,
                    validation_notes=notes or None,
                )
            )

    per_stratum = {s: counts.get(s, 0) for s in QuestionStratum}
    optional: list[str] = []
    for row_id, label, row_stratum in blank_rows:
        if per_stratum[row_stratum] >= min_per_stratum:
            optional.append(row_id)
        elif require_complete:
            issues.append(
                QuestionBankIssue(label, Severity.ERROR, "sin validar (falta validated_by).")
            )
        else:
            pending.append(row_id)
    severity = Severity.ERROR if require_complete else Severity.WARNING
    for stratum_value, count in per_stratum.items():
        if count < min_per_stratum:
            issues.append(
                QuestionBankIssue(
                    "-",
                    severity,
                    f"{stratum_value.value}: {count} validadas, por debajo del mínimo "
                    f"de {min_per_stratum}.",
                )
            )
    return QuestionBankReport(
        usable=tuple(usable),
        pending_ids=tuple(pending),
        optional_ids=tuple(optional),
        issues=tuple(issues),
        usable_per_stratum=per_stratum,
        total_rows=len(rows),
    )


def load_configured_question_bank(
    path: Path, *, require_complete: bool = False
) -> QuestionBankReport:
    """:func:`load_question_bank` with the series and minimum from ``config/``."""
    corpus = load_corpus_config()
    return load_question_bank(
        path,
        study_series=frozenset(corpus["oe1"]["series"]),
        meeting_letters=tuple(corpus["corpus"]["series"]["meeting_letters"]),
        min_per_stratum=int(load_experiments_config()["question_bank"]["min_questions"]),
        require_complete=require_complete,
    )


def format_issue(issue: QuestionBankIssue) -> str:
    """One-line, human-readable form of an issue."""
    return f"{issue.row_id}: {issue.message}"


@dataclass(frozen=True)
class StratumProgress:
    """How far one stratum of the bank is: rows written, rows validated, and the targets."""

    stratum: QuestionStratum
    written: int
    validated: int
    minimum: int
    rows: int
    """Rows the bank holds for the stratum (above ``minimum`` they are optional)."""


@dataclass(frozen=True)
class QuestionBankProgress:
    """Per-stratum progress of the bank, for ``afg gold status``."""

    strata: tuple[StratumProgress, ...]

    @property
    def written(self) -> int:
        return sum(s.written for s in self.strata)

    @property
    def validated(self) -> int:
        return sum(s.validated for s in self.strata)

    @property
    def missing_for_minimum(self) -> int:
        return sum(max(0, s.minimum - s.written) for s in self.strata)

    @property
    def awaiting_validation(self) -> int:
        """Written rows nobody has validated yet."""
        return sum(s.written - s.validated for s in self.strata)


def question_bank_progress(
    path: Path, *, minimum: int, rows_per_stratum: dict[QuestionStratum, int]
) -> QuestionBankProgress | None:
    """Count written (``text`` filled) and validated rows per stratum, or ``None`` when the
    bank file does not exist.

    Never raises on content: this is a progress count, not a validation (``questions-check``
    validates). Rows with an unknown stratum are ignored.
    """
    if not path.is_file():
        return None
    written: Counter[QuestionStratum] = Counter()
    validated: Counter[QuestionStratum] = Counter()
    with open_csv_reader(path) as handle:
        for row in csv.DictReader(handle):
            try:
                stratum = QuestionStratum((row.get("stratum") or "").strip())
            except ValueError:
                continue
            if (row.get("text") or "").strip():
                written[stratum] += 1
                if (row.get("validated_by") or "").strip():
                    validated[stratum] += 1
    return QuestionBankProgress(
        strata=tuple(
            StratumProgress(
                stratum=s,
                written=written[s],
                validated=validated[s],
                minimum=minimum,
                rows=rows_per_stratum.get(s, minimum),
            )
            for s in QuestionStratum
        )
    )
