"""Tests for the judge calibration set schema and loader (thesis section 5.7, ADR 0005)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from afg.domain.question import QuestionStratum
from afg.evaluation.judge_calibration_set import (
    TEMPLATE_PATH,
    CalibrationItem,
    CalibrationSetError,
    DevelopmentSplitError,
    load_calibration_items,
)

HEADER = (
    "id,series_id,stratum,question,reference_answer,answer_text,answer_abstained,"
    "correct,evidence_supported,citation_correct,labeler_a,labeler_b,adjudicated\n"
)


def _write(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "set.csv"
    path.write_text(HEADER + "".join(row + "\n" for row in rows), encoding="utf-8")
    return path


E1 = "c1,ES2015,E1_point_fact,¿Precio?,25 euros,25 euros,false,true,true,,gm,gv,true"
E4 = "c2,IS1004,E4_unanswerable,¿Garantía?,,No hay información.,true,true,true,,gm,gv,false"


class TestSchema:
    def test_e4_must_not_carry_a_reference(self) -> None:
        with pytest.raises(ValidationError):
            CalibrationItem(
                id="x",
                series_id="ES2015",
                stratum=QuestionStratum.E4_UNANSWERABLE,
                question="q",
                reference_answer="something",
                answer_text="a",
            )

    def test_answerable_strata_need_a_reference(self) -> None:
        with pytest.raises(ValidationError):
            CalibrationItem(
                id="x",
                series_id="ES2015",
                stratum=QuestionStratum.E1_POINT_FACT,
                question="q",
                reference_answer=None,
                answer_text="a",
            )


class TestLoader:
    def test_reads_rows_and_parses_types(self, tmp_path: Path) -> None:
        items = load_calibration_items(_write(tmp_path, E1, E4))
        assert [i.id for i in items] == ["c1", "c2"]
        assert items[0].correct is True and items[0].citation_correct is None
        assert items[0].adjudicated is True and items[1].adjudicated is False
        assert items[1].reference_answer is None and items[1].answer_abstained is True
        assert items[0].labelers == ("gm", "gv")

    def test_rejects_evaluation_series(self, tmp_path: Path) -> None:
        row = "c3,ES2016,E1_point_fact,q,r,a,false,true,true,,gm,gv,true"
        with pytest.raises(DevelopmentSplitError, match="ES2016"):
            load_calibration_items(_write(tmp_path, E1, row))

    def test_reads_a_file_with_bom(self, tmp_path: Path) -> None:
        path = _write(tmp_path, E1)
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        assert len(load_calibration_items(path)) == 1

    def test_unlabeled_rows_load_by_default_but_fail_when_labels_required(
        self, tmp_path: Path
    ) -> None:
        row = "c4,ES2015,E1_point_fact,q,r,a,false,,,,,,false"
        path = _write(tmp_path, row)
        assert load_calibration_items(path)[0].correct is None
        with pytest.raises(CalibrationSetError, match="c4"):
            load_calibration_items(path, require_labels=True)

    def test_bad_boolean_names_the_row(self, tmp_path: Path) -> None:
        row = "c5,ES2015,E1_point_fact,q,r,a,maybe,true,true,,gm,gv,true"
        with pytest.raises(CalibrationSetError, match="c5"):
            load_calibration_items(_write(tmp_path, row))

    def test_duplicate_ids_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(CalibrationSetError, match="duplicate"):
            load_calibration_items(_write(tmp_path, E1, E1))

    def test_missing_columns_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.csv"
        path.write_text("id,series_id\nc1,ES2015\n", encoding="utf-8")
        with pytest.raises(CalibrationSetError, match="columns"):
            load_calibration_items(path)


def test_shipped_template_is_header_only_and_loadable() -> None:
    assert load_calibration_items(TEMPLATE_PATH) == []
