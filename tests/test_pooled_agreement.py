"""Tests for the pooled inter-annotator agreement (``afg.annotation.pooled``).

Fixtures are synthetic under ``tmp_path``; the pooled kappa is one kappa over the concatenated
items of several series, never the mean of per-series kappas.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from afg.annotation.agreement import annotator_csvs, compute_series_agreement
from afg.annotation.pooled import (
    PooledAgreement,
    pooled_agreement,
    pooled_agreement_report,
    write_pooled_csv,
)
from afg.annotation.workspace import AnnotationPlan, WorkspacePaths
from afg.evaluation.metrics import cohen_kappa

_PAIR_COLUMNS = ("pair_id", "relation", "direction_ok")
_DECISION_COLUMNS = ("decision_id", "gm_status", "gv_status", "acuerdo", "final_status")


def _write(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def _pairs(workspace: WorkspacePaths, series: str, gm: list[tuple[str, str]], gv: list) -> None:
    for initials, labels in (("gm", gm), ("gv", gv)):
        _write(
            workspace.relations_dir / f"{series}.candidates.{initials}.csv",
            _PAIR_COLUMNS,
            [
                {"pair_id": f"{series}.p{i:03d}", "relation": rel, "direction_ok": direction}
                for i, (rel, direction) in enumerate(labels, start=1)
            ],
        )


def _decisions(workspace: WorkspacePaths, series: str, labels: list[tuple[str, str]]) -> None:
    _write(
        workspace.decisions_dir / f"{series}.decisions.adjudicated.csv",
        _DECISION_COLUMNS,
        [
            {
                "decision_id": f"{series}a.d{i:02d}",
                "gm_status": gm,
                "gv_status": gv,
                "acuerdo": "si" if gm == gv else "no",
                "final_status": gm,
            }
            for i, (gm, gv) in enumerate(labels, start=1)
        ]
        # A child row of a compuesta base row must not enter Task A.
        + [{"decision_id": f"{series}a.d01-1", "final_status": "decision"}],
    )


@pytest.fixture
def workspace(tmp_path: Path) -> WorkspacePaths:
    ws = WorkspacePaths(decisions_dir=tmp_path / "decisions", relations_dir=tmp_path / "relations")
    # Series S1: 4 pairs; the annotators agree on existence of 3, differ on one type.
    _pairs(
        ws,
        "S1",
        gm=[("refina", "si"), ("reafirma", "si"), ("no_relacionada", "si"), ("refina", "si")],
        gv=[("refina", "si"), ("refina", "si"), ("no_relacionada", "si"), ("no_relacionada", "no")],
    )
    _decisions(ws, "S1", [("decision", "decision"), ("decision", "no_decision")])
    # Series S2: 3 pairs.
    _pairs(
        ws,
        "S2",
        gm=[("revierte", "si"), ("no_relacionada", "si"), ("refina", "si")],
        gv=[("revierte", "si"), ("refina", "si"), ("refina", "si")],
    )
    _decisions(ws, "S2", [("decision", "decision"), ("sin_soporte", "decision")])
    return ws


class TestPooledAgreement:
    def test_pools_items_instead_of_averaging_series_kappas(
        self, workspace: WorkspacePaths
    ) -> None:
        result = pooled_agreement(["S1", "S2"], paths=workspace)

        # S1 then S2, as derived from the fixture labels above.
        e, n = "exists", "no_relation"
        existence_a = [e, e, n, e, e, n, e]
        existence_b = [e, e, n, n, e, e, e]
        axis = result.axis("existence")
        assert axis.n_items == 7
        assert axis.n_disagreements == 2
        assert axis.percent_agreement == pytest.approx(5 / 7)
        assert axis.kappa == pytest.approx(cohen_kappa(existence_a, existence_b))
        per_series = [
            compute_series_agreement(annotator_csvs(workspace.relations_dir, s, "candidates"))
            for s in ("S1", "S2")
        ]
        mean = sum(r.existence_kappa for r in per_series) / 2
        assert axis.kappa != pytest.approx(mean)

    def test_type_axis_uses_only_pairs_both_marked_as_existing(
        self, workspace: WorkspacePaths
    ) -> None:
        axis = pooled_agreement(["S1", "S2"], paths=workspace).axis("type")
        # S1: p1, p2 (gv no_relacionada on p4 drops it); S2: p1, p3.
        assert axis.n_items == 4
        assert axis.n_disagreements == 1
        assert axis.percent_agreement == pytest.approx(0.75)

    def test_status_axis_uses_base_rows_of_each_annotator_not_the_verdict(
        self, workspace: WorkspacePaths
    ) -> None:
        axis = pooled_agreement(["S1", "S2"], paths=workspace).axis("status")
        assert axis.n_items == 4  # the child row is excluded
        assert axis.n_disagreements == 2
        assert axis.percent_agreement == pytest.approx(0.5)

    def test_undefined_kappa_stays_nan_with_raw_agreement(self, workspace: WorkspacePaths) -> None:
        axis = pooled_agreement(["S2"], paths=workspace).axis("direction")
        assert axis.n_items == 3
        assert math.isnan(axis.kappa)
        assert axis.percent_agreement == 1.0

    def test_records_scope_and_series(self, workspace: WorkspacePaths) -> None:
        result = pooled_agreement(["S1", "S2"], scope="overall", paths=workspace)
        assert (result.scope, result.series) == ("overall", ("S1", "S2"))
        assert [a.axis for a in result.axes] == ["status", "existence", "type", "direction"]

    def test_empty_series_list_is_an_error(self, workspace: WorkspacePaths) -> None:
        with pytest.raises(ValueError, match="at least one series"):
            pooled_agreement([], paths=workspace)


def _plan() -> AnnotationPlan:
    return AnnotationPlan(
        annotators=(),
        adjudicator="jss",
        phase1_series=("S1",),
        phase2_series=("S2", "S3"),
        recall_sample=None,  # type: ignore[arg-type]
        question_bank=None,  # type: ignore[arg-type]
    )


class TestPooledReport:
    def test_overall_then_phases_only_with_complete_series(self, workspace: WorkspacePaths) -> None:
        report = pooled_agreement_report(_plan(), paths=workspace, is_complete=lambda s: s != "S3")
        assert [r.scope for r in report] == ["overall", "phase 1", "phase 2"]
        assert [r.series for r in report] == [("S1", "S2"), ("S1",), ("S2",)]

    def test_default_completeness_excludes_series_without_adjudication(
        self, workspace: WorkspacePaths
    ) -> None:
        # No adjudicated candidates file exists in the fixture, so nothing is complete.
        report = pooled_agreement_report(_plan(), paths=workspace)
        assert report == ()

    def test_phase_without_complete_series_is_omitted(self, workspace: WorkspacePaths) -> None:
        report = pooled_agreement_report(_plan(), paths=workspace, is_complete=lambda s: s == "S1")
        assert [r.scope for r in report] == ["overall", "phase 1"]


class TestWritePooledCsv:
    def test_one_row_per_scope_and_axis(self, workspace: WorkspacePaths, tmp_path: Path) -> None:
        result: PooledAgreement = pooled_agreement(["S1"], scope="phase 1", paths=workspace)
        out = write_pooled_csv((result,), tmp_path / "out" / "agreement-pooled.csv")
        with out.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert [(r["scope"], r["axis"]) for r in rows] == [
            ("phase 1", "status"),
            ("phase 1", "existence"),
            ("phase 1", "type"),
            ("phase 1", "direction"),
        ]
        assert rows[1]["series"] == "S1"
        assert rows[1]["n_items"] == "4"
