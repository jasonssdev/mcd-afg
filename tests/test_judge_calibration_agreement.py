"""Tests for the human-human agreement on the judge calibration set (issue #82)."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import pytest

from afg.evaluation.judge_calibration_agreement import (
    SECOND_SHEET_COLUMNS,
    AgreementError,
    SecondSheetLabeledError,
    compute_human_agreement,
    load_agreement,
    read_label_rows,
    save_agreement,
    select_second_sheet_rows,
    write_second_sheet,
)


def _row(item_id: str, correct: str, supported: str) -> dict[str, str]:
    return {
        "id": item_id,
        "stratum": "E1_point_fact",
        "question": f"q {item_id}",
        "reference_answer": "ref",
        "answer_text": "ans",
        "pasaje_transcripcion": "pasaje",
        "archivos_transcripcion": "file",
        "series_id": "ES2015",
        "correct": correct,
        "evidence_supported": supported,
    }


PRIMARY = [
    _row("a", "si", "si"),
    _row("b", "no", "no"),
    _row("c", "si", "no"),
    _row("d", "no", "si"),
    _row("e", "si", "si"),
    _row("f", "no", "no"),
]


def test_perfect_agreement() -> None:
    second = [_row(r["id"], r["correct"], r["evidence_supported"]) for r in PRIMARY[:4]]
    result = compute_human_agreement(PRIMARY, second, min_kappa=0.70)
    by_column = {c.column: c for c in result}
    assert set(by_column) == {"correct", "evidence_supported"}
    for column in by_column.values():
        assert column.n_items == 4
        assert column.n_agree == 4
        assert column.kappa == pytest.approx(1.0)
        assert column.disagreements == ()
        assert column.passes


def test_disagreement_lists_ids_and_fails_threshold() -> None:
    second = [
        _row("a", "si", "no"),  # supported differs
        _row("b", "si", "no"),  # correct differs
        _row("c", "si", "no"),
        _row("d", "no", "si"),
    ]
    by_column = {c.column: c for c in compute_human_agreement(PRIMARY, second, min_kappa=0.70)}
    assert by_column["correct"].disagreements == ("b",)
    assert by_column["correct"].n_agree == 3
    assert by_column["evidence_supported"].disagreements == ("a",)
    assert by_column["evidence_supported"].kappa == pytest.approx(0.5)
    assert not by_column["evidence_supported"].passes


def test_accepts_spanish_and_boolean_spellings() -> None:
    primary = [_row("a", "sí", "TRUE"), _row("b", "no", "0")]
    second = [_row("a", "si", "1"), _row("b", "false", "no")]
    by_column = {c.column: c for c in compute_human_agreement(primary, second, min_kappa=0.7)}
    assert by_column["correct"].n_agree == 2


def test_unknown_second_labeler_id_is_an_error() -> None:
    with pytest.raises(AgreementError, match="zzz"):
        compute_human_agreement(PRIMARY, [_row("zzz", "si", "si")], min_kappa=0.7)


@pytest.mark.parametrize("bad", ["", "  ", "quizá"])
def test_empty_or_invalid_label_names_id_and_column(bad: str) -> None:
    second = [_row("a", "si", bad)]
    with pytest.raises(AgreementError, match=r"'a'.*evidence_supported"):
        compute_human_agreement(PRIMARY, second, min_kappa=0.7)


def test_empty_primary_label_names_id_and_column() -> None:
    primary = [_row("a", "", "si")]
    with pytest.raises(AgreementError, match=r"'a'.*correct"):
        compute_human_agreement(primary, [_row("a", "si", "si")], min_kappa=0.7)


def test_no_second_labeler_rows_is_an_error() -> None:
    with pytest.raises(AgreementError):
        compute_human_agreement(PRIMARY, [], min_kappa=0.7)


def test_select_is_deterministic_blank_and_in_second_sheet_columns() -> None:
    rows = [_row(f"id{n:02d}", "si", "no") for n in range(30)]
    chosen = select_second_sheet_rows(rows, n=5, seed=42)
    ids = sorted(r["id"] for r in rows)
    random.Random(42).shuffle(ids)
    assert [r["id"] for r in chosen] == ids[:5]
    assert select_second_sheet_rows(list(reversed(rows)), n=5, seed=42) == chosen
    for row in chosen:
        assert tuple(row) == SECOND_SHEET_COLUMNS
        assert row["correct"] == ""
        assert row["evidence_supported"] == ""


def test_select_more_than_available_is_an_error() -> None:
    with pytest.raises(AgreementError):
        select_second_sheet_rows(PRIMARY, n=10, seed=42)


def test_write_second_sheet_roundtrip_and_overwrite_guard(tmp_path: Path) -> None:
    path = tmp_path / "second.csv"
    rows = select_second_sheet_rows(PRIMARY, n=3, seed=42)
    write_second_sheet(path, rows)
    write_second_sheet(path, rows)  # unlabeled sheet may be regenerated
    assert [r["id"] for r in read_label_rows(path)] == [r["id"] for r in rows]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SECOND_SHEET_COLUMNS)
        writer.writeheader()
        writer.writerow({**rows[0], "correct": "si"})
    with pytest.raises(SecondSheetLabeledError):
        write_second_sheet(path, rows)
    write_second_sheet(path, rows, force=True)
    assert read_label_rows(path)[0]["correct"] == ""


def test_save_and_load_agreement_roundtrip(tmp_path: Path) -> None:
    second = [_row(r["id"], r["correct"], r["evidence_supported"]) for r in PRIMARY[:4]]
    result = compute_human_agreement(PRIMARY, second, min_kappa=0.7)
    path = tmp_path / "out" / "acuerdo.json"
    save_agreement(path, result, min_kappa=0.7, labelers=("jss", "gm"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["min_kappa"] == 0.7
    assert payload["labelers"] == ["jss", "gm"]
    assert load_agreement(path) == (result, 0.7, ("jss", "gm"))
