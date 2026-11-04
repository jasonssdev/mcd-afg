"""Tests for the E3 minimum derived from the available evolution relations (ADR 0021, D25)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from afg.domain.question import QuestionStratum
from afg.evaluation.relations import (
    available_evolution_relations,
    count_evolution_relations,
    load_gold_pair_labels,
)
from afg.experiments.question_bank import (
    Severity,
    evolution_minimum,
    load_question_bank,
    stratum_minimums,
)

HEADER = (
    "id,series_id,stratum,text,reference_answer,reference_evidence,author,validated_by,"
    "validation_notes,superseded_answer\n"
)
SERIES = frozenset({"ES2016"})
E1, E2, E3, E4 = (
    QuestionStratum.E1_POINT_FACT,
    QuestionStratum.E2_CURRENT_STATE,
    QuestionStratum.E3_EVOLUTION,
    QuestionStratum.E4_UNANSWERABLE,
)


class TestCountRule:
    def test_counts_the_three_evolution_labels(self) -> None:
        rows = [("S.p1", "refina"), ("S.p2", "revierte"), ("S.p3", "reemplaza")]
        assert count_evolution_relations(rows) == 3

    def test_other_labels_and_empty_are_excluded(self) -> None:
        rows = [
            ("S.p1", "no_relacionada"),
            ("S.p2", "introduce"),
            ("S.p3", "reafirma"),
            ("S.p4", ""),
            ("S.p5", "refina"),
        ]
        assert count_evolution_relations(rows) == 1

    def test_a_pair_id_is_counted_once(self) -> None:
        rows = [("S.p1", "refina"), ("S.p1", "refina"), ("S.p2", "revierte")]
        assert count_evolution_relations(rows) == 2

    def test_labels_are_trimmed(self) -> None:
        assert count_evolution_relations([("S.p1", " refina ")]) == 1

    def test_no_rows_is_zero(self) -> None:
        assert count_evolution_relations([]) == 0


class TestMinimum:
    def test_capped_by_the_available_relations(self) -> None:
        assert evolution_minimum(25, 24) == 24

    def test_never_above_the_base_minimum(self) -> None:
        assert evolution_minimum(25, 40) == 25
        assert evolution_minimum(25, 25) == 25

    def test_stratum_minimums_change_only_e3(self) -> None:
        assert stratum_minimums(25, 24) == {E1: 25, E2: 25, E3: 24, E4: 25}


def _write_candidates(
    directory: Path, name: str, columns: tuple[str, str], rows: list[tuple[str, str]]
) -> None:
    with (directory / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("pair_id", "earlier_decision_id", "later_decision_id", *columns))
        for pair_id, label in rows:
            writer.writerow((pair_id, "a", "b", label, "si"))


class TestConfiguredReading:
    def test_adjudicated_file_uses_final_relation(self, tmp_path: Path) -> None:
        _write_candidates(
            tmp_path,
            "AA1.candidates.adjudicated.csv",
            ("final_relation", "final_direction_ok"),
            [("AA1.p001", "refina"), ("AA1.p002", "no_relacionada")],
        )
        assert load_gold_pair_labels("AA1", relations_dir=tmp_path) == (
            ("AA1.p001", "refina"),
            ("AA1.p002", "no_relacionada"),
        )

    def test_single_annotator_file_uses_relation(self, tmp_path: Path) -> None:
        _write_candidates(
            tmp_path,
            "BB1.candidates.gm.csv",
            ("relation", "direction_ok"),
            [("BB1.p001", "revierte")],
        )
        assert load_gold_pair_labels("BB1", relations_dir=tmp_path) == (("BB1.p001", "revierte"),)

    def test_series_are_pooled_with_their_own_reference_kind(self, tmp_path: Path) -> None:
        _write_candidates(
            tmp_path,
            "AA1.candidates.adjudicated.csv",
            ("final_relation", "final_direction_ok"),
            [("AA1.p001", "refina"), ("AA1.p002", "reemplaza")],
        )
        _write_candidates(
            tmp_path,
            "BB1.candidates.gv.csv",
            ("relation", "direction_ok"),
            [("BB1.p001", "revierte"), ("BB1.p002", "introduce")],
        )
        assert available_evolution_relations(["AA1", "BB1"], relations_dir=tmp_path) == 3

    def test_series_outside_the_list_are_not_counted(self, tmp_path: Path) -> None:
        _write_candidates(
            tmp_path,
            "AA1.candidates.gm.csv",
            ("relation", "direction_ok"),
            [("AA1.p001", "refina")],
        )
        _write_candidates(
            tmp_path,
            "DEV.candidates.gm.csv",
            ("relation", "direction_ok"),
            [("DEV.p001", "refina"), ("DEV.p002", "refina")],
        )
        assert available_evolution_relations(["AA1"], relations_dir=tmp_path) == 1


def _row(number: int, stratum: QuestionStratum) -> str:
    superseded = "Old" if stratum is E3 else ""
    answer = "" if stratum is E4 else "A"
    evidence = "" if stratum is E4 else "ES2016a:d1"
    return (
        f"q{number:03d},ES2016,{stratum.value},Q{number}?,{answer},{evidence},gm,gv,,{superseded}"
    )


def _bank(tmp_path: Path, counts: dict[QuestionStratum, int], blank_e3: int = 0) -> Path:
    rows: list[str] = []
    for stratum, count in counts.items():
        start = len(rows) + 1
        rows.extend([_row(start + i, stratum) for i in range(count)])
    rows.extend(f"q{900 + i},,{E3.value},,,,gm,,," for i in range(blank_e3))
    path = tmp_path / "banco.csv"
    path.write_text(HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
    return path


def _complete(path: Path, minimums: dict[QuestionStratum, int]):  # type: ignore[no-untyped-def]
    return load_question_bank(
        path,
        study_series=SERIES,
        meeting_letters=("a",),
        min_per_stratum=minimums,
        require_complete=True,
    )


class TestPerStratumMinimumInTheLoader:
    def test_complete_passes_with_24_e3_when_24_are_available(self, tmp_path: Path) -> None:
        path = _bank(tmp_path, {E1: 25, E2: 25, E3: 24, E4: 25}, blank_e3=16)
        report = _complete(path, stratum_minimums(25, 24))
        assert not report.has_errors
        assert len(report.optional_ids) == 16

    def test_complete_fails_with_23_e3_when_24_are_available(self, tmp_path: Path) -> None:
        path = _bank(tmp_path, {E1: 25, E2: 25, E3: 23, E4: 25})
        report = _complete(path, stratum_minimums(25, 24))
        assert any(
            i.severity is Severity.ERROR and "E3_evolution" in i.message and "24" in i.message
            for i in report.issues
        )

    def test_other_strata_still_need_25(self, tmp_path: Path) -> None:
        path = _bank(tmp_path, {E1: 24, E2: 25, E3: 24, E4: 25})
        report = _complete(path, stratum_minimums(25, 24))
        assert any(
            i.severity is Severity.ERROR and "E1_point_fact" in i.message for i in report.issues
        )

    def test_blank_e3_rows_from_the_minimum_on_are_optional_not_pending(
        self, tmp_path: Path
    ) -> None:
        path = _bank(tmp_path, {E3: 2}, blank_e3=1)
        report = _complete(path, {E1: 0, E2: 0, E3: 2, E4: 0})
        assert report.optional_ids == ("q900",)
        assert report.pending_ids == ()

    def test_an_int_still_applies_to_every_stratum(self, tmp_path: Path) -> None:
        path = _bank(tmp_path, {E1: 1})
        report = load_question_bank(
            path, study_series=SERIES, meeting_letters=("a",), min_per_stratum=1
        )
        assert sum(i.severity is Severity.WARNING for i in report.issues) == 3


@pytest.mark.parametrize(("base", "available", "expected"), [(25, 0, 0), (3, 2, 2), (3, 9, 3)])
def test_evolution_minimum_table(base: int, available: int, expected: int) -> None:
    assert evolution_minimum(base, available) == expected


def test_status_progress_reports_the_per_stratum_minimum(tmp_path: Path) -> None:
    from afg.experiments.question_bank import question_bank_progress

    path = _bank(tmp_path, {E1: 1, E3: 1})
    progress = question_bank_progress(
        path, minimum=25, rows_per_stratum={}, minimums=stratum_minimums(25, 24)
    )
    assert progress is not None
    by_stratum = {s.stratum: s.minimum for s in progress.strata}
    assert by_stratum == {E1: 25, E2: 25, E3: 24, E4: 25}
    assert progress.missing_for_minimum == 24 + 25 + 23 + 25
