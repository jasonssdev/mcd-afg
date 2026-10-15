"""Tests for the question sources of Experiment B."""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.domain.question import Question, QuestionStratum
from afg.evaluation.judge_calibration_set import CalibrationSetError
from afg.evaluation.judge_calibration_worksheet import WORKSHEET_PATH
from afg.experiments.questions import load_experiment_questions

_HEADER = "id,series_id,stratum,question,reference_answer,reference_evidence\n"


def test_loads_the_calibration_question_csv(tmp_path: Path) -> None:
    path = tmp_path / "q.csv"
    path.write_text(
        _HEADER
        + "ES2015.q001,ES2015,E1_point_fact,How much?,Twelve,ES2015a:d1;d2\n"
        + "ES2015.q002,ES2015,E4_unanswerable,Weather?,,\n",
        encoding="utf-8",
    )
    questions = load_experiment_questions(path)
    assert [q.id for q in questions] == ["ES2015.q001", "ES2015.q002"]
    first = questions[0]
    assert isinstance(first, Question)
    assert first.text == "How much?" and first.reference_answer == "Twelve"
    assert first.reference_evidence[0].dialogue_act_ids == ("d1", "d2")
    assert questions[1].stratum is QuestionStratum.E4_UNANSWERABLE


def test_series_outside_the_calibration_split_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "q.csv"
    path.write_text(_HEADER + "x.q1,ES2002,E1_point_fact,Q?,A,ES2002a:d1\n", encoding="utf-8")
    with pytest.raises(CalibrationSetError):
        load_experiment_questions(path)


def test_limit_keeps_the_first_questions(tmp_path: Path) -> None:
    path = tmp_path / "q.csv"
    path.write_text(
        _HEADER + "".join(f"q{i},ES2015,E1_point_fact,Q{i}?,A,ES2015a:d{i}\n" for i in range(5)),
        encoding="utf-8",
    )
    assert [q.id for q in load_experiment_questions(path, limit=2)] == ["q0", "q1"]


def test_loads_the_tracked_worksheet() -> None:
    questions = load_experiment_questions(WORKSHEET_PATH)
    assert len(questions) >= 16
    assert all(q.id.startswith("ES2015.q") for q in questions)
