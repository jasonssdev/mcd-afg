"""Tests for the OE1 Task-D series agreement computation (manual de anotacion section 6).

All synthetic, small two-annotator CSVs built in ``tmp_path`` -- no dependency on the real
corpus, per the manual's requirement that existence/type/direction kappa are reported
independently rather than collapsed into one number.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from afg.annotation.agreement import (
    AgreementInputError,
    SeriesAgreementResult,
    compute_series_agreement,
    write_agreement_csv,
)

_CANDIDATE_COLUMNS = (
    "pair_id",
    "earlier_decision_id",
    "later_decision_id",
    "earlier_text",
    "later_text",
    "blocker_score",
    "relation",
    "direction_ok",
    "confidence",
    "annotator",
    "notes",
)


def _write_candidates_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CANDIDATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in _CANDIDATE_COLUMNS})
    return path


def _row(pair_id: str, relation: str, direction_ok: str) -> dict[str, str]:
    return {
        "pair_id": pair_id,
        "earlier_decision_id": f"{pair_id}.earlier",
        "later_decision_id": f"{pair_id}.later",
        "earlier_text": "x",
        "later_text": "y",
        "blocker_score": "0.40",
        "relation": relation,
        "direction_ok": direction_ok,
        "confidence": "alta",
    }


class TestComputeSeriesAgreementInputErrors:
    def test_fewer_than_two_files_raises(self, tmp_path: Path) -> None:
        path = _write_candidates_csv(
            tmp_path / "IS1004.candidates.jd.csv", [_row("p1", "revierte", "si")]
        )
        with pytest.raises(AgreementInputError, match="at least 2"):
            compute_series_agreement([path])

    def test_no_common_pair_ids_raises(self, tmp_path: Path) -> None:
        path_a = _write_candidates_csv(
            tmp_path / "IS1004.candidates.aa.csv", [_row("p1", "revierte", "si")]
        )
        path_b = _write_candidates_csv(
            tmp_path / "IS1004.candidates.bb.csv", [_row("p2", "revierte", "si")]
        )
        with pytest.raises(AgreementInputError, match="no pair_id in common"):
            compute_series_agreement([path_a, path_b])


class TestComputeSeriesAgreementIndependence:
    """The core Task-D claim: existence, type, and direction are independent numbers."""

    def test_perfect_existence_imperfect_direction(self, tmp_path: Path) -> None:
        # Both annotators agree, on every pair, on whether a link exists (perfect existence
        # agreement -- including one pair they both mark as no_relacionada, so existence
        # kappa has both classes represented and is not degenerate), but disagree on
        # direction for one pair -- proving direction is not derived from, or collapsed
        # with, existence.
        rows_a = [
            _row("p1", "revierte", "si"),
            _row("p2", "refina", "si"),
            _row("p3", "reemplaza", "no"),
            _row("p4", "no_relacionada", "si"),
        ]
        rows_b = [
            _row("p1", "revierte", "si"),
            _row("p2", "refina", "si"),
            _row("p3", "reemplaza", "si"),  # direction disagreement only
            _row("p4", "no_relacionada", "si"),
        ]
        path_a = _write_candidates_csv(tmp_path / "IS1004.candidates.aa.csv", rows_a)
        path_b = _write_candidates_csv(tmp_path / "IS1004.candidates.bb.csv", rows_b)

        result = compute_series_agreement([path_a, path_b])

        assert result.existence_kappa == pytest.approx(1.0)
        assert result.existence_disagreements == ()
        assert result.direction_kappa != pytest.approx(1.0)
        assert result.direction_disagreements == ("p3",)

    def test_existence_derived_from_no_relacionada(self, tmp_path: Path) -> None:
        rows_a = [
            _row("p1", "no_relacionada", "si"),
            _row("p2", "introduce", "si"),
        ]
        rows_b = [
            _row("p1", "introduce", "si"),
            _row("p2", "introduce", "si"),
        ]
        path_a = _write_candidates_csv(tmp_path / "IS1004.candidates.aa.csv", rows_a)
        path_b = _write_candidates_csv(tmp_path / "IS1004.candidates.bb.csv", rows_b)

        result = compute_series_agreement([path_a, path_b])

        assert result.existence_disagreements == ("p1",)

    def test_type_kappa_only_over_both_existing_links(self, tmp_path: Path) -> None:
        rows_a = [
            _row("p1", "no_relacionada", "si"),  # A says no link: excluded from type kappa
            _row("p2", "revierte", "si"),
            _row("p3", "refina", "si"),
        ]
        rows_b = [
            _row("p1", "reemplaza", "si"),
            _row("p2", "revierte", "si"),
            _row("p3", "reemplaza", "si"),
        ]
        path_a = _write_candidates_csv(tmp_path / "IS1004.candidates.aa.csv", rows_a)
        path_b = _write_candidates_csv(tmp_path / "IS1004.candidates.bb.csv", rows_b)

        result = compute_series_agreement([path_a, path_b])

        # p1 excluded (only B thinks it's an existing link); p2 and p3 both exist for both.
        assert result.n_type_items == 2
        assert result.type_disagreements == ("p3",)

    def test_type_kappa_none_when_no_shared_existing_link(self, tmp_path: Path) -> None:
        rows_a = [_row("p1", "no_relacionada", "si")]
        rows_b = [_row("p1", "no_relacionada", "si")]
        path_a = _write_candidates_csv(tmp_path / "IS1004.candidates.aa.csv", rows_a)
        path_b = _write_candidates_csv(tmp_path / "IS1004.candidates.bb.csv", rows_b)

        result = compute_series_agreement([path_a, path_b])

        assert result.type_kappa is None
        assert result.n_type_items == 0

    def test_uses_two_lexicographically_first_files_when_more_present(
        self, tmp_path: Path
    ) -> None:
        rows = [_row("p1", "revierte", "si")]
        path_aa = _write_candidates_csv(tmp_path / "IS1004.candidates.aa.csv", rows)
        path_bb = _write_candidates_csv(tmp_path / "IS1004.candidates.bb.csv", rows)
        path_zz = _write_candidates_csv(tmp_path / "IS1004.candidates.zz.csv", rows)

        result = compute_series_agreement([path_zz, path_bb, path_aa])

        assert {result.annotator_a, result.annotator_b} == {"aa", "bb"}


class TestWriteAgreementCsv:
    def test_writes_three_independent_rows(self, tmp_path: Path) -> None:
        result = SeriesAgreementResult(
            series_id="IS1004",
            annotator_a="aa",
            annotator_b="bb",
            n_items=3,
            existence_kappa=1.0,
            existence_disagreements=(),
            n_type_items=2,
            type_kappa=0.5,
            type_disagreements=("p3",),
            direction_kappa=0.0,
            direction_disagreements=("p3",),
        )
        out_path = write_agreement_csv(result, tmp_path / "IS1004.agreement.csv")

        with out_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        assert [row["axis"] for row in rows] == ["existence", "type", "direction"]
        by_axis = {row["axis"]: row for row in rows}
        assert by_axis["existence"]["kappa"] == "1.0"
        assert by_axis["type"]["disagreeing_pair_ids"] == "p3"
        assert by_axis["direction"]["disagreeing_pair_ids"] == "p3"
