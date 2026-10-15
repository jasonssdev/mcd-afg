"""Tests for the question bank loader and its validation report."""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.domain.question import QuestionStratum
from afg.experiments.question_bank import (
    Severity,
    is_question_bank,
    load_question_bank,
)
from afg.experiments.questions import QuestionBankError, load_experiment_questions

HEADER = (
    "id,series_id,stratum,text,reference_answer,reference_evidence,author,validated_by,"
    "validation_notes\n"
)
SERIES = frozenset({"ES2015", "IS1004"})
LETTERS = ("a", "b", "c", "d")


def write(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "banco.csv"
    path.write_text(HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
    return path


def load(path: Path, *, minimum: int = 0, complete: bool = False):  # type: ignore[no-untyped-def]
    return load_question_bank(
        path,
        study_series=SERIES,
        meeting_letters=LETTERS,
        min_per_stratum=minimum,
        require_complete=complete,
    )


GOOD_E1 = "q001,ES2015,E1_point_fact,How much?,Twelve,ES2015a:d1;d2,gm,gv,"
GOOD_E4 = "q002,IS1004,E4_unanswerable,Weather?,,,gm,gv,"


def problems(report) -> list[tuple[str, Severity, str]]:  # type: ignore[no-untyped-def]
    return [(i.row_id, i.severity, i.message) for i in report.issues]


def test_valid_rows_become_questions(tmp_path: Path) -> None:
    report = load(write(tmp_path, GOOD_E1, GOOD_E4))
    assert report.issues == ()
    assert [q.id for q in report.usable] == ["q001", "q002"]
    first = report.usable[0]
    assert first.stratum is QuestionStratum.E1_POINT_FACT
    assert first.reference_evidence[0].dialogue_act_ids == ("d1", "d2")
    assert first.author == "gm" and first.validated_by == "gv"
    assert report.usable[1].reference_answer is None
    assert report.pending_ids == ()


def test_unvalidated_rows_are_pending_not_errors(tmp_path: Path) -> None:
    report = load(write(tmp_path, GOOD_E1, "q003,,E2_current_state,,,,gm,,"))
    assert [q.id for q in report.usable] == ["q001"]
    assert report.pending_ids == ("q003",)
    assert not report.has_errors


def test_complete_mode_makes_pending_rows_blocking(tmp_path: Path) -> None:
    report = load(write(tmp_path, GOOD_E1, "q003,,E2_current_state,,,,gm,,"), complete=True)
    assert report.has_errors
    assert any(row == "q003" and sev is Severity.ERROR for row, sev, _ in problems(report))


def test_validator_equal_to_author_is_blocking_and_not_usable(tmp_path: Path) -> None:
    report = load(write(tmp_path, "q001,ES2015,E1_point_fact,Q?,A,ES2015a:d1,gm,gm,"))
    assert report.usable == ()
    assert report.has_errors
    assert report.pending_ids == ()


def test_returned_row_with_notes_is_pending(tmp_path: Path) -> None:
    report = load(write(tmp_path, "q001,ES2015,E1_point_fact,Q?,A,ES2015a:d1,gm,,fix the answer"))
    assert report.pending_ids == ("q001",)
    assert report.usable == ()


def test_stale_validation_notes_on_validated_row_is_a_warning(tmp_path: Path) -> None:
    report = load(write(tmp_path, "q001,ES2015,E1_point_fact,Q?,A,ES2015a:d1,gm,gv,old note"))
    assert len(report.usable) == 1
    assert not report.has_errors
    assert [s for _, s, _ in problems(report)] == [Severity.WARNING]


@pytest.mark.parametrize(
    ("row", "fragment"),
    [
        ("q001,ES2015,E9_bogus,Q?,A,ES2015a:d1,gm,gv,", "estrato"),
        ("q001,ES2015,E1_point_fact,,A,ES2015a:d1,gm,gv,", "texto"),
        ("q001,ES2002,E1_point_fact,Q?,A,ES2002a:d1,gm,gv,", "serie"),
        ("q001,,E1_point_fact,Q?,A,ES2015a:d1,gm,gv,", "serie"),
        ("q001,ES2015,E1_point_fact,Q?,A,garbage,gm,gv,", "evidencia"),
        ("q001,ES2015,E1_point_fact,Q?,A,IS1004a:d1,gm,gv,", "evidencia"),
        ("q001,ES2015,E1_point_fact,Q?,A,ES2015z:d1,gm,gv,", "evidencia"),
        ("q001,ES2015,E1_point_fact,Q?,,ES2015a:d1,gm,gv,", "respuesta"),
        ("q001,ES2015,E2_current_state,Q?,A,,gm,gv,", "evidencia"),
        ("q001,ES2015,E3_evolution,Q?,,,gm,gv,", "respuesta"),
        ("q001,ES2015,E4_unanswerable,Q?,An answer,,gm,gv,", "E4"),
        ("q001,ES2015,E4_unanswerable,Q?,,ES2015a:d1,gm,gv,", "E4"),
        ("q001,ES2015,E1_point_fact,Q?,A,ES2015a:d1,,gv,", "autor"),
    ],
)
def test_blocking_row_problems(tmp_path: Path, row: str, fragment: str) -> None:
    report = load(write(tmp_path, row))
    assert report.usable == ()
    errors = [m for r, s, m in problems(report) if s is Severity.ERROR and r == "q001"]
    assert any(fragment in m for m in errors), errors


def test_all_problems_of_a_row_are_reported_not_just_the_first(tmp_path: Path) -> None:
    report = load(write(tmp_path, "q001,ES2002,E1_point_fact,,,,gm,gv,"))
    assert len([p for p in problems(report) if p[0] == "q001"]) >= 3


def test_errors_in_one_row_do_not_hide_other_rows(tmp_path: Path) -> None:
    report = load(write(tmp_path, "q001,ES2015,E1_point_fact,,A,ES2015a:d1,gm,gv,", GOOD_E4))
    assert [q.id for q in report.usable] == ["q002"]
    assert report.has_errors


def test_duplicate_ids_are_blocking(tmp_path: Path) -> None:
    report = load(write(tmp_path, GOOD_E1, GOOD_E1))
    assert any("duplicad" in m for _, s, m in problems(report) if s is Severity.ERROR)


def test_unknown_stratum_on_pending_row_is_still_blocking(tmp_path: Path) -> None:
    report = load(write(tmp_path, "q001,,E9,,,,gm,,"))
    assert report.has_errors


def test_stratum_below_minimum_is_warning_when_partial_and_error_when_complete(
    tmp_path: Path,
) -> None:
    path = write(tmp_path, GOOD_E1, GOOD_E4)
    partial = load(path, minimum=2)
    assert not partial.has_errors
    assert any(s is Severity.WARNING and "mínimo" in m for _, s, m in problems(partial))
    complete = load(path, minimum=2, complete=True)
    assert any(s is Severity.ERROR and "mínimo" in m for _, s, m in problems(complete))


def test_counts_per_stratum_cover_usable_rows(tmp_path: Path) -> None:
    report = load(write(tmp_path, GOOD_E1, GOOD_E4))
    assert report.usable_per_stratum[QuestionStratum.E1_POINT_FACT] == 1
    assert report.usable_per_stratum[QuestionStratum.E2_CURRENT_STATE] == 0


def test_missing_columns_raise(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    path.write_text("id,text\nq1,hi\n", encoding="utf-8")
    with pytest.raises(ValueError, match="columnas"):
        load(path)


def test_is_question_bank_detects_format(tmp_path: Path) -> None:
    assert is_question_bank(write(tmp_path, GOOD_E1))
    other = tmp_path / "o.csv"
    other.write_text("id,series_id,stratum,question\n", encoding="utf-8")
    assert not is_question_bank(other)


def test_real_empty_bank_is_all_pending() -> None:
    from afg.experiments.question_bank import load_configured_question_bank

    path = Path("data/processed/questions/banco-preguntas.csv")
    report = load_configured_question_bank(path)
    assert len(report.pending_ids) == 115
    assert report.usable == ()
    assert not report.has_errors


def test_load_experiment_questions_accepts_the_bank(tmp_path: Path) -> None:
    path = write(tmp_path, GOOD_E1, "q003,,E2_current_state,,,,gm,,")
    # Configured series do not include the fixture series, so use a real one.
    path.write_text(
        HEADER + "q001,ES2015,E1_point_fact,How much?,Twelve,ES2015a:d1,gm,gv,\n",
        encoding="utf-8",
    )
    questions = load_experiment_questions(path)
    assert [q.id for q in questions] == ["q001"]
    assert load_experiment_questions(path, limit=1)[0].id == "q001"


def test_load_experiment_questions_refuses_blocking_errors(tmp_path: Path) -> None:
    path = write(tmp_path, "q001,ES2015,E1_point_fact,,A,ES2015a:d1,gm,gv,")
    with pytest.raises(QuestionBankError, match="q001"):
        load_experiment_questions(path)


def test_load_experiment_questions_refuses_a_bank_with_nothing_usable(tmp_path: Path) -> None:
    path = write(tmp_path, "q001,,E1_point_fact,,,,gm,,")
    with pytest.raises(QuestionBankError, match="pendiente"):
        load_experiment_questions(path)


def test_blank_rows_beyond_the_minimum_are_optional_and_do_not_block_complete(
    tmp_path: Path,
) -> None:
    path = write(
        tmp_path,
        GOOD_E1,
        "q002,ES2015,E2_current_state,Now?,A,ES2015a:d1,gm,gv,",
        "q003,ES2015,E3_evolution,Changed?,A,ES2015a:d1;d2,gm,gv,",
        "q004,IS1004,E4_unanswerable,Weather?,,,gm,gv,",
        "q005,,E3_evolution,,,,gm,,",
    )
    report = load(path, minimum=1, complete=True)
    assert not report.has_errors
    assert report.optional_ids == ("q005",)
    assert report.pending_ids == ()
    assert [q.id for q in report.usable] == ["q001", "q002", "q003", "q004"]


def test_blank_rows_are_pending_while_the_stratum_is_below_its_minimum(tmp_path: Path) -> None:
    path = write(tmp_path, GOOD_E1, "q003,,E1_point_fact,,,,gm,,")
    report = load(path, minimum=2, complete=True)
    assert report.optional_ids == ()
    assert report.pending_ids == ()  # complete mode reports them as errors instead
    assert any(r == "q003" and s is Severity.ERROR for r, s, _ in problems(report))
    assert any("mínimo" in m for _, s, m in problems(report) if s is Severity.ERROR)


def test_a_written_but_unvalidated_row_is_never_optional(tmp_path: Path) -> None:
    path = write(tmp_path, GOOD_E1, "q003,ES2015,E1_point_fact,Drafted?,,,gm,,")
    partial = load(path, minimum=1)
    assert partial.pending_ids == ("q003",)
    assert partial.optional_ids == ()
    complete = load(path, minimum=1, complete=True)
    assert any(r == "q003" and s is Severity.ERROR for r, s, _ in problems(complete))


def test_optional_rows_are_ignored_by_the_experiment_loader(tmp_path: Path) -> None:
    path = tmp_path / "banco.csv"
    path.write_text(
        HEADER
        + "q001,ES2015,E1_point_fact,How much?,Twelve,ES2015a:d1,gm,gv,\n"
        + "q002,,E1_point_fact,,,,gm,,\n",
        encoding="utf-8",
    )
    assert [q.id for q in load_experiment_questions(path)] == ["q001"]
