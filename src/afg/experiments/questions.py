"""Question sources for Experiment B.

The real question bank loader does not exist yet (thesis section 5.5). Until it does, the
runner reads the ES2015 calibration questions, in either of the two shapes they have:
the selected rows of the human worksheet (``ES2015.preguntas.csv``) or the English question
CSV of :mod:`afg.evaluation.judge_calibration_generation`. Both pass through the guards
of the calibration set, so only development series (ADR 0005) can be loaded.
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


def _to_question(item: CalibrationQuestion) -> Question:
    return Question(
        id=item.id,
        series_id=item.series_id,
        stratum=item.stratum,
        text=item.question,
        reference_answer=item.reference_answer,
        reference_evidence=item.reference_evidence,
    )


def _is_worksheet(path: Path) -> bool:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle), [])
    return "pregunta" in header


def load_experiment_questions(path: Path, *, limit: int | None = None) -> list[Question]:
    """The questions of ``path`` (worksheet or question CSV), at most ``limit`` of them.

    Raises:
        CalibrationSetError: on a malformed file or a series outside the calibration series.
        WorksheetError: if a worksheet selection does not validate.
        FileNotFoundError: if ``path`` does not exist.
    """
    if _is_worksheet(path):
        items = worksheet_questions(load_worksheet(path))
    else:
        items = load_calibration_questions(path)
    questions = [_to_question(item) for item in items]
    return questions if limit is None else questions[:limit]
