"""Tests for the calibration summaries (``afg.annotation.calibration``).

They read the adjudication CSVs (both annotators side by side plus the adjudicator's
verdict) and summarise them for the phase notebooks. All fixtures are synthetic under
``tmp_path``; no corpus and no real ``data/`` tree is needed.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from afg.annotation.calibration import (
    adjudicated_pairs,
    compuesta_children,
    decision_agreement,
    final_rows,
    final_status_counts,
    resolved_disagreements,
    side_taken_counts,
    status_contingency,
)
from afg.annotation.workspace import WorkspacePaths

_DECISION_COLUMNS = (
    "decision_id",
    "sentence_text",
    "gm_status",
    "gm_object",
    "gm_content",
    "gv_status",
    "gv_object",
    "gv_content",
    "acuerdo",
    "final_status",
    "final_object",
    "final_content",
    "razon",
    "adjudicator",
)
_PAIR_COLUMNS = (
    "pair_id",
    "earlier_decision_id",
    "later_decision_id",
    "gm_relation",
    "gm_direction_ok",
    "gv_relation",
    "gv_direction_ok",
    "acuerdo",
    "final_relation",
    "final_direction_ok",
    "razon",
    "adjudicator",
)


def _write(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def _d(decision_id: str, gm: str, gv: str, final: str, **extra: str) -> dict[str, str]:
    agree = "si" if gm and gm == gv else "no"
    row = {
        "decision_id": decision_id,
        "gm_status": gm,
        "gv_status": gv,
        "acuerdo": agree,
        "final_status": final,
        "adjudicator": "jss",
    }
    row.update(extra)
    return row


@pytest.fixture
def paths(tmp_path: Path) -> WorkspacePaths:
    workspace = WorkspacePaths(
        decisions_dir=tmp_path / "decisions", relations_dir=tmp_path / "relations"
    )
    _write(
        workspace.decisions_dir / "ES2015.decisions.adjudicated.csv",
        _DECISION_COLUMNS,
        [
            _d("ES2015a.d01", "decision", "decision", "decision"),
            _d("ES2015a.d02", "decision", "no_decision", "no_decision", razon="solo opinion"),
            _d("ES2015a.d03", "no_decision", "sin_soporte", "sin_soporte", razon="no consta"),
            _d("ES2015b.d01", "decision", "decision", "decision"),
            _d("ES2015b.d02", "compuesta", "decision", "compuesta", razon="dos objetos"),
            _d("ES2015b.d02-1", "", "", "decision", final_object="LCD", razon="una"),
            _d("ES2015b.d02-2", "", "", "descartar", razon="Duplica ES2015b.d01"),
        ],
    )
    _write(
        workspace.relations_dir / "ES2015.candidates.adjudicated.csv",
        _PAIR_COLUMNS,
        [
            {
                "pair_id": "ES2015.p001",
                "earlier_decision_id": "ES2015a.d01",
                "later_decision_id": "ES2015b.d01",
                "gm_relation": "refina",
                "gv_relation": "refina",
                "acuerdo": "si",
                "final_relation": "refina",
                "adjudicator": "jss",
            },
            {
                "pair_id": "ES2015.p002",
                "earlier_decision_id": "ES2015a.d01",
                "later_decision_id": "ES2015b.d01",
                "gm_relation": "reafirma",
                "gv_relation": "refina",
                "acuerdo": "no",
                "final_relation": "reafirma",
                "razon": "repite",
                "adjudicator": "jss",
            },
        ],
    )
    return workspace


class TestDecisionAgreement:
    def test_counts_base_rows_only_and_compares_raw_status(self, paths: WorkspacePaths) -> None:
        result = decision_agreement("ES2015", paths=paths)
        assert (result.annotator_a, result.annotator_b) == ("gm", "gv")
        assert result.n_items == 5  # children of ES2015b.d02 are not base rows
        assert result.n_status_agree == 2
        assert result.n_acuerdo == 2
        assert result.percent_agreement == pytest.approx(0.4)

    def test_status_kappa_comes_from_the_shared_implementation(self, paths: WorkspacePaths) -> None:
        from afg.annotation.agreement import compute_agreement

        result = decision_agreement("ES2015", paths=paths)
        expected = compute_agreement(
            ["decision", "decision", "no_decision", "decision", "compuesta"],
            ["decision", "no_decision", "sin_soporte", "decision", "decision"],
        )
        assert result.status_kappa == pytest.approx(expected)


class TestStatusContingency:
    def test_records_are_sorted_pairs_with_counts(self, paths: WorkspacePaths) -> None:
        records = status_contingency("ES2015", paths=paths)
        assert ("decision", "decision", 2) in records
        assert ("compuesta", "decision", 1) in records
        assert sum(n for _, _, n in records) == 5


class TestFinalStatusCounts:
    def test_base_and_children_are_counted_apart(self, paths: WorkspacePaths) -> None:
        counts = final_status_counts("ES2015", paths=paths)
        assert counts.base == {
            "compuesta": 1,
            "decision": 2,
            "no_decision": 1,
            "sin_soporte": 1,
        }
        assert counts.children == {"decision": 1, "descartar": 1}


class TestResolvedDisagreements:
    def test_lists_only_disagreements_with_side_taken(self, paths: WorkspacePaths) -> None:
        rows = {r["decision_id"]: r for r in resolved_disagreements("ES2015", paths=paths)}
        assert set(rows) == {"ES2015a.d02", "ES2015a.d03", "ES2015b.d02"}
        assert rows["ES2015a.d02"]["sided_with"] == "gv"
        assert rows["ES2015a.d03"]["sided_with"] == "gv"
        assert rows["ES2015b.d02"]["sided_with"] == "gm"
        assert rows["ES2015a.d02"]["razon"] == "solo opinion"

    def test_neither_when_the_verdict_matches_no_annotator(self, paths: WorkspacePaths) -> None:
        _write(
            paths.decisions_dir / "ES2015.decisions.adjudicated.csv",
            _DECISION_COLUMNS,
            [_d("ES2015a.d09", "decision", "no_decision", "descartar", razon="truncada")],
        )
        (row,) = resolved_disagreements("ES2015", paths=paths)
        assert row["sided_with"] == "ninguno"


class TestCompuestaChildren:
    def test_children_carry_their_parent_and_verdict(self, paths: WorkspacePaths) -> None:
        rows = compuesta_children("ES2015", paths=paths)
        assert [r["decision_id"] for r in rows] == ["ES2015b.d02-1", "ES2015b.d02-2"]
        assert {r["parent_id"] for r in rows} == {"ES2015b.d02"}
        assert rows[0]["final_object"] == "LCD"


class TestFinalRows:
    def test_filters_base_and_children_by_final_status(self, paths: WorkspacePaths) -> None:
        rows = final_rows("ES2015", "descartar", paths=paths)
        assert [r["decision_id"] for r in rows] == ["ES2015b.d02-2"]
        assert rows[0]["razon"] == "Duplica ES2015b.d01"
        assert [r["decision_id"] for r in final_rows("ES2015", "sin_soporte", paths=paths)] == [
            "ES2015a.d03"
        ]


class TestAdjudicatedPairs:
    def test_pairs_show_both_labels_final_and_side(self, paths: WorkspacePaths) -> None:
        rows = adjudicated_pairs("ES2015", paths=paths)
        assert [r["pair_id"] for r in rows] == ["ES2015.p001", "ES2015.p002"]
        assert rows[0]["sided_with"] == "gm+gv"
        assert rows[1]["sided_with"] == "gm"
        assert rows[1]["razon"] == "repite"


class TestSideTakenCounts:
    def test_tallies_who_the_verdict_agreed_with(self, paths: WorkspacePaths) -> None:
        assert side_taken_counts("ES2015", paths=paths) == {"gm": 1, "gv": 2}
