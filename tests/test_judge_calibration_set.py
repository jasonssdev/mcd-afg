"""Tests for the judge calibration set schema and loader (thesis section 5.7, ADR 0005)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from afg.domain.decision import EvidenceSpan
from afg.domain.question import QuestionStratum
from afg.evaluation.judge_calibration_set import (
    COLUMNS,
    TEMPLATE_PATH,
    CalibrationItem,
    CalibrationSetError,
    DevelopmentSplitError,
    calibration_series,
    load_calibration_items,
    summarize_calibration_set,
    variants_path,
)

HEADER = (
    "id,series_id,stratum,question,reference_answer,reference_evidence,"
    "answer_text,answer_abstained,correct,evidence_supported,citation_correct,"
    "labeler_a,labeler_b,adjudicated\n"
)


def _write(tmp_path: Path, *rows: str, variants: dict[str, str] | None = None) -> Path:
    path = tmp_path / "set.csv"
    path.write_text(HEADER + "".join(row + "\n" for row in rows), encoding="utf-8")
    if variants is not None:
        variants_path(path).write_text(
            "id,answer_variant\n" + "".join(f"{k},{v}\n" for k, v in variants.items()),
            encoding="utf-8",
        )
    return path


E1 = (
    "c1,ES2015,E1_point_fact,¿Precio?,25 euros,ES2015a:ES2015a.A.dialog-act.x.1,"
    "25 euros,false,true,true,,gm,gv,true"
)
E4 = "c2,ES2015,E4_unanswerable,¿Garantía?,,,No hay información.,true,true,true,,gm,gv,false"


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
        variants = {"c1": "grounded", "c2": "no_context"}
        items = load_calibration_items(_write(tmp_path, E1, E4, variants=variants))
        assert [i.id for i in items] == ["c1", "c2"]
        assert items[0].correct is True and items[0].citation_correct is None
        assert items[0].adjudicated is True and items[1].adjudicated is False
        assert items[1].reference_answer is None and items[1].answer_abstained is True
        assert items[0].labelers == ("gm", "gv")
        assert items[0].answer_variant == "grounded"
        assert items[1].answer_variant == "no_context"
        assert items[0].reference_evidence == (
            EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("ES2015a.A.dialog-act.x.1",)),
        )
        assert items[1].reference_evidence == ()

    def test_rejects_evaluation_series(self, tmp_path: Path) -> None:
        row = "c3,ES2016,E1_point_fact,q,r,,a,false,true,true,,gm,gv,true"
        with pytest.raises(DevelopmentSplitError, match="ES2016"):
            load_calibration_items(_write(tmp_path, E1, row))

    def test_rejects_development_series_outside_the_calibration_config(
        self, tmp_path: Path
    ) -> None:
        # IS1004 is a development series, but its annotations are still pending (issue #82),
        # so the calibration set may not touch it.
        row = "c3,IS1004,E1_point_fact,q,r,,a,false,true,true,,gm,gv,true"
        with pytest.raises(DevelopmentSplitError, match="IS1004"):
            load_calibration_items(_write(tmp_path, E1, row))

    def test_reads_a_file_with_bom(self, tmp_path: Path) -> None:
        path = _write(tmp_path, E1)
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        assert len(load_calibration_items(path)) == 1

    def test_unlabeled_rows_load_by_default_but_fail_when_labels_required(
        self, tmp_path: Path
    ) -> None:
        row = "c4,ES2015,E1_point_fact,q,r,,a,false,,,,,,false"
        path = _write(tmp_path, row)
        assert load_calibration_items(path)[0].correct is None
        with pytest.raises(CalibrationSetError, match="c4"):
            load_calibration_items(path, require_labels=True)

    def test_malformed_evidence_names_the_row(self, tmp_path: Path) -> None:
        row = "c6,ES2015,E1_point_fact,q,r,no-colon-here,a,false,,,,,,false"
        with pytest.raises(CalibrationSetError, match="c6"):
            load_calibration_items(_write(tmp_path, row))

    def test_bad_boolean_names_the_row(self, tmp_path: Path) -> None:
        row = "c5,ES2015,E1_point_fact,q,r,,a,maybe,true,true,,gm,gv,true"
        with pytest.raises(CalibrationSetError, match="c5"):
            load_calibration_items(_write(tmp_path, row))

    @pytest.mark.parametrize(
        ("cell", "expected"),
        [("si", True), ("Sí", True), ("SI", True), ("no", False), ("No", False), ("TRUE", True)],
    )
    def test_spreadsheet_friendly_booleans(self, tmp_path: Path, cell: str, expected: bool) -> None:
        row = (
            "c7,ES2015,E1_point_fact,q,r,ES2015a:ES2015a.A.dialog-act.x.1,a,false,"
            f"{cell},{cell},,gm,,false"
        )
        (item,) = load_calibration_items(_write(tmp_path, row))
        assert item.correct is expected
        assert item.evidence_supported is expected

    def test_variant_is_not_a_column_of_the_labeling_file(self) -> None:
        assert "answer_variant" not in COLUMNS

    def test_items_without_a_sidecar_have_no_variant(self, tmp_path: Path) -> None:
        (item,) = load_calibration_items(_write(tmp_path, E1))
        assert item.answer_variant is None

    def test_variants_path_sits_next_to_the_calibration_file(self, tmp_path: Path) -> None:
        assert variants_path(tmp_path / "calibracion-juez.csv") == (
            tmp_path / "calibracion-juez.variantes.csv"
        )

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


class TestCalibrationSeries:
    def test_shipped_config_restricts_to_es2015(self) -> None:
        assert calibration_series() == frozenset({"ES2015"})

    def test_config_listing_a_non_development_series_fails_loudly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "afg.evaluation.judge_calibration_set.load_experiments_config",
            lambda: {"judge": {"calibration": {"series": ["ES2015", "ES2016"]}}},
        )
        with pytest.raises(DevelopmentSplitError, match="ES2016"):
            calibration_series()

    def test_empty_series_list_fails_loudly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "afg.evaluation.judge_calibration_set.load_experiments_config",
            lambda: {"judge": {"calibration": {"series": []}}},
        )
        with pytest.raises(CalibrationSetError, match="series"):
            calibration_series()


class TestSummary:
    def test_empty_set_is_not_ready(self) -> None:
        summary = summarize_calibration_set([])
        assert (summary.n_items, summary.n_labeled, summary.ready) == (0, 0, False)

    def test_counts_labels_variants_and_strata(self, tmp_path: Path) -> None:
        unlabeled = "c4,ES2015,E1_point_fact,q,r,,a,false,,,,,,false"
        variants = {"c1": "grounded", "c2": "no_context", "c4": "ungrounded"}
        items = load_calibration_items(_write(tmp_path, E1, E4, unlabeled, variants=variants))
        summary = summarize_calibration_set(items)
        assert (summary.n_items, summary.n_labeled) == (3, 2)
        assert summary.by_variant == {"grounded": 1, "no_context": 1, "ungrounded": 1}
        assert summary.by_stratum == {"E1_point_fact": 2, "E4_unanswerable": 1}
        assert summary.ready is False  # one item still lacks its human labels

    def test_fully_labeled_set_is_ready(self, tmp_path: Path) -> None:
        items = load_calibration_items(_write(tmp_path, E1, E4))
        assert summarize_calibration_set(items).ready is True
