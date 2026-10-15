"""Tests for the 20 % human verification of the judge (T2): sample, blind sheet, kappa."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pytest

from afg.evaluation.judge_calibration_agreement import AgreementError, SecondSheetLabeledError
from afg.evaluation.judge_human_check import (
    SHEET_COLUMNS,
    check_judge_against_humans,
    read_csv_rows,
    select_human_sample,
    write_human_sample,
)


def _record(
    q: int,
    condition: str,
    run: int,
    *,
    stratum: str = "E3_evolution",
    correct: bool = True,
    supported: bool = True,
    judge_failure: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    judged = judge_failure is None and error is None
    return {
        "question_id": f"ES2015.q{q:03d}",
        "condition": condition,
        "run": run,
        "stratum": stratum,
        "trace": {"question": f"Question {q}?"},
        "answer": {"text": f"answer {condition} {q} {run}", "abstained": False},
        "verdict": {"correct": correct, "evidence_supported": supported} if judged else None,
        "judge_failure": judge_failure,
        "error": error,
    }


def _records() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for condition in ("C1", "C2"):
        for stratum, offset in (("E1_point_fact", 0), ("E3_evolution", 100)):
            for q in range(10):
                for run in range(3):
                    out.append(
                        _record(offset + q, condition, run, stratum=stratum, correct=q % 2 == 0)
                    )
    return out  # 4 cells x 30 records


def test_sample_is_stratified_by_condition_and_stratum() -> None:
    sample = select_human_sample(_records(), fraction=0.2, seed=42)
    assert len(sample.sheet_rows) == 24  # ceil(0.2 * 30) = 6 per cell, 4 cells
    assert sample.per_cell == {
        ("C1", "E1"): (30, 6),
        ("C1", "E3"): (30, 6),
        ("C2", "E1"): (30, 6),
        ("C2", "E3"): (30, 6),
    }


def test_sample_is_deterministic_and_seed_dependent() -> None:
    a = select_human_sample(_records(), fraction=0.2, seed=42)
    b = select_human_sample(list(reversed(_records())), fraction=0.2, seed=42)
    c = select_human_sample(_records(), fraction=0.2, seed=43)
    assert a.key_rows == b.key_rows
    assert a.key_rows != c.key_rows


def test_failures_and_errors_are_not_sampled() -> None:
    records = [_record(1, "C1", r) for r in range(5)]
    records += [_record(2, "C1", 0, judge_failure="bad"), _record(3, "C1", 0, error="boom")]
    sample = select_human_sample(records, fraction=1.0, seed=1)
    assert len(sample.sheet_rows) == 5
    assert {row["question_id"] for row in sample.key_rows} == {"ES2015.q001"}


def test_sheet_hides_condition_and_judge_verdict() -> None:
    sample = select_human_sample(_records(), fraction=0.2, seed=42)
    for row in sample.sheet_rows:
        assert tuple(row) == SHEET_COLUMNS
        assert row["correct"] == "" and row["evidence_supported"] == ""
        assert row["id"].startswith("h")
        assert "C1" not in row["id"] + row["answer_text"].split(" ")[0]
    text = " ".join(" ".join(r.values()) for r in sample.sheet_rows)
    assert "ES2015.q" not in text  # the sheet never carries the question id either


def test_sheet_ids_do_not_reveal_condition_through_order() -> None:
    sample = select_human_sample(_records(), fraction=0.2, seed=42)
    conditions = [row["condition"] for row in sample.key_rows]
    assert conditions != sorted(conditions)  # shuffled, not grouped by condition


def test_reference_answers_are_included_when_given() -> None:
    sample = select_human_sample(
        _records(), fraction=0.2, seed=42, reference_answers={"ES2015.q000": "ref zero"}
    )
    by_key = {k["id"]: s for k, s in zip(sample.key_rows, sample.sheet_rows, strict=True)}
    for key in sample.key_rows:
        expected = "ref zero" if key["question_id"] == "ES2015.q000" else ""
        assert by_key[key["id"]]["reference_answer"] == expected


def test_fraction_validation() -> None:
    with pytest.raises(ValueError):
        select_human_sample(_records(), fraction=0.0, seed=1)
    with pytest.raises(ValueError):
        select_human_sample([], fraction=0.2, seed=1)


def test_write_and_read_back_and_refuse_to_overwrite_labels(tmp_path: Path) -> None:
    sample = select_human_sample(_records(), fraction=0.2, seed=42)
    sheet, key = tmp_path / "hoja.csv", tmp_path / "clave.csv"
    write_human_sample(sheet, key, sample)
    assert len(read_csv_rows(sheet)) == 24
    assert read_csv_rows(key)[0]["condition"] in {"C1", "C2"}
    rows = read_csv_rows(sheet)
    rows[0]["correct"] = "si"
    with sheet.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(SecondSheetLabeledError):
        write_human_sample(sheet, key, sample)
    write_human_sample(sheet, key, sample, force=True)


def _labelled(sample_key: list[dict[str, str]], human: dict[str, tuple[str, str]]):
    sheet = [
        {"id": k["id"], "correct": human[k["id"]][0], "evidence_supported": human[k["id"]][1]}
        for k in sample_key
    ]
    return sheet


def _key(n: int, judge: list[tuple[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "id": f"h{i:03d}",
            "question_id": f"q{i}",
            "condition": "C1",
            "run": "0",
            "stratum": "E3",
            "judge_correct": judge[i][0],
            "judge_evidence_supported": judge[i][1],
        }
        for i in range(n)
    ]


def test_high_agreement_keeps_automatic_judging() -> None:
    pattern = [("si", "si"), ("no", "si")] * 10
    key = _key(20, pattern)
    sheet = _labelled(
        key, {k["id"]: (k["judge_correct"], k["judge_evidence_supported"]) for k in key}
    )
    check = check_judge_against_humans(key, sheet, min_kappa=0.70)
    assert check.keep_automatic_judging is True
    assert check.n_items == 20
    assert check.columns[0].kappa == pytest.approx(1.0)


def test_low_agreement_falls_back_to_human_only() -> None:
    key = _key(20, [("si", "si"), ("no", "si")] * 10)
    human = {k["id"]: ("si", "si") for k in key}  # human says always correct
    check = check_judge_against_humans(key, _labelled(key, human), min_kappa=0.70)
    assert check.keep_automatic_judging is False
    assert "evaluación humana" in check.decision


def test_verdict_is_gated_on_correct_and_flags_evidence_supported() -> None:
    key = _key(20, [("si", "si"), ("no", "no")] * 10)
    human = {k["id"]: (k["judge_correct"], "si") for k in key}  # agrees on correct only
    check = check_judge_against_humans(key, _labelled(key, human), min_kappa=0.70)
    assert check.keep_automatic_judging is True
    by_name = {c.column: c for c in check.columns}
    assert by_name["correct"].passes is True
    assert by_name["evidence_supported"].passes is False


def test_unlabelled_or_missing_rows_are_errors() -> None:
    key = _key(4, [("si", "si")] * 4)
    sheet = _labelled(key, {k["id"]: ("si", "si") for k in key})
    sheet[1]["correct"] = ""
    with pytest.raises(AgreementError, match="h001"):
        check_judge_against_humans(key, sheet, min_kappa=0.7)
    with pytest.raises(AgreementError, match="h003"):
        check_judge_against_humans(key, sheet[:3], min_kappa=0.7)
    with pytest.raises(AgreementError, match="zzz"):
        check_judge_against_humans(
            key, [*sheet, {"id": "zzz", "correct": "si", "evidence_supported": "si"}], min_kappa=0.7
        )


def test_undefined_kappa_does_not_pass() -> None:
    key = _key(4, [("si", "si")] * 4)
    check = check_judge_against_humans(
        key, _labelled(key, {k["id"]: ("si", "si") for k in key}), min_kappa=0.7
    )
    assert check.columns[0].kappa is None
    assert check.keep_automatic_judging is False


def _question(qid: str, stratum: str = "E1_point_fact", evidence: bool = True):
    from afg.domain.decision import EvidenceSpan
    from afg.domain.question import Question, QuestionStratum

    spans = (EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("d1",)),) if evidence else ()
    return Question(
        id=qid,
        series_id="ES2015",
        stratum=QuestionStratum(stratum),
        text="t",
        reference_answer="ref" if evidence else None,
        reference_evidence=spans,
    )


def test_question_context_uses_the_judge_excerpt_and_transcript_files() -> None:
    from afg.evaluation.judge_human_check import question_context_for

    seen: list[str] = []

    def excerpt(question: Any) -> str:
        seen.append(question.id)
        return f"passage of {question.id}"

    context_for = question_context_for(
        [_question("ES2015.q001")],
        excerpt_for=excerpt,
        files_for=lambda spans: "transcripts/ES2015a.md",
    )
    assert context_for(_record(1, "C1", 0)) == ("passage of ES2015.q001", "transcripts/ES2015a.md")
    assert seen == ["ES2015.q001"]


def test_question_context_for_e4_is_blank_like_the_calibration_worksheet() -> None:
    from afg.evaluation.judge_human_check import question_context_for

    context_for = question_context_for(
        [_question("ES2015.q001", "E4_unanswerable", evidence=False)]
    )
    assert context_for(_record(1, "C1", 0, stratum="E4_unanswerable")) == ("", "")


def test_question_context_for_unknown_question_is_an_error() -> None:
    from afg.evaluation.judge_human_check import question_context_for

    with pytest.raises(ValueError, match=r"ES2015\.q009"):
        question_context_for([_question("ES2015.q001")])(_record(9, "C1", 0))


def test_sample_fills_passage_columns_from_context_for() -> None:
    sample = select_human_sample(
        _records(),
        fraction=0.2,
        seed=42,
        context_for=lambda record: ("PASSAGE", "files.md"),
    )
    assert all(r["pasaje_transcripcion"] == "PASSAGE" for r in sample.sheet_rows)
    assert all(r["archivos_transcripcion"] == "files.md" for r in sample.sheet_rows)
