"""Question sources for Experiment B.

Three shapes are accepted, detected from the header: the real question bank
(``banco-preguntas.csv``, loaded by :mod:`afg.experiments.question_bank`, which runs only
the validated rows), the selected rows of the ES2015 calibration worksheet
(``ES2015.preguntas.csv``) or the English question CSV of
:mod:`afg.evaluation.judge_calibration_generation`. The two calibration shapes pass through
the guards of the calibration set, so only development series (ADR 0005) can be loaded.
"""

from __future__ import annotations

import csv
from pathlib import Path

from afg.domain.question import Question
from afg.evaluation.judge_calibration_generation import (
    CalibrationQuestion,
    load_calibration_questions,
)
from afg.evaluation.judge_calibration_worksheet import load_worksheet, worksheet_questions
from afg.experiments.question_bank import (
    QuestionBankReport,
    format_issue,
    is_question_bank,
    load_configured_question_bank,
)
from afg.shared.csvio import open_csv_reader


def _to_question(item: CalibrationQuestion) -> Question:
    return Question(
        id=item.id,
        series_id=item.series_id,
        stratum=item.stratum,
        text=item.question,
        reference_answer=item.reference_answer,
        reference_evidence=item.reference_evidence,
    )


class QuestionBankError(ValueError):
    """The question bank has blocking errors or no validated question to run."""


def bank_questions(report: QuestionBankReport) -> list[Question]:
    """The usable questions of ``report``, refusing a bank that cannot run.

    Raises:
        QuestionBankError: on any blocking error, or when no row is validated yet.
    """
    if report.has_errors:
        shown = [format_issue(i) for i in report.errors[:20]]
        extra = len(report.errors) - len(shown)
        lines = [f"El banco tiene {len(report.errors)} error(es) bloqueante(s):", *shown]
        if extra > 0:
            lines.append(f"... y {extra} más (`afg gold questions-check` los lista todos).")
        raise QuestionBankError("\n".join(lines))
    if not report.usable:
        raise QuestionBankError(
            f"El banco no tiene preguntas validadas: {len(report.pending_ids)} pendiente(s)."
        )
    return list(report.usable)


def _is_worksheet(path: Path) -> bool:
    with open_csv_reader(path) as handle:
        header = next(csv.reader(handle), [])
    return "pregunta" in header


def load_experiment_questions(path: Path, *, limit: int | None = None) -> list[Question]:
    """The questions of ``path`` (worksheet or question CSV), at most ``limit`` of them.

    Raises:
        CalibrationSetError: on a malformed file or a series outside the calibration series.
        WorksheetError: if a worksheet selection does not validate.
        FileNotFoundError: if ``path`` does not exist.
    """
    if is_question_bank(path):
        questions = bank_questions(load_configured_question_bank(path, strict=True))
        return questions if limit is None else questions[:limit]
    if _is_worksheet(path):
        items = worksheet_questions(load_worksheet(path))
    else:
        items = load_calibration_questions(path)
    questions = [_to_question(item) for item in items]
    return questions if limit is None else questions[:limit]
