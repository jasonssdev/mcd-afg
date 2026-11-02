"""Tests for the final report tables and figures (issue #243). No network, no model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.evaluation.scoring import DevelopmentResultError
from afg.experiments.final_tables import (
    STAMP,
    BRun,
    FinalInputs,
    a_headline_table,
    a_relations_table,
    b_cells_table,
    b_paired_table,
    build_final_tables,
    cost_tables,
    oe4_table,
    write_final_tables,
)


def _pooled(base: float) -> dict[str, Any]:
    figures: dict[str, Any] = {"tp": 3, "fp": 1, "fn": 2, "n_clusters": 4}
    for i, name in enumerate(("precision", "recall", "f1")):
        figures[name] = base + 0.1 * i
    figures["intervals"] = {n: [figures[n] - 0.05, figures[n] + 0.05] for n in figures_names()}
    return {"pooled": figures}


def figures_names() -> tuple[str, ...]:
    return ("precision", "recall", "f1")


def _prop(k: int, n: int) -> dict[str, Any]:
    if not n:
        return {"successes": 0, "trials": 0, "rate": None, "lower": None, "upper": None}
    return {"successes": k, "trials": n, "rate": k / n, "lower": 0.1, "upper": 0.9}


def a_report(*, reportable: bool = True) -> dict[str, Any]:
    def entry(tau: float, role: str | None, base: float) -> dict[str, Any]:
        return {
            "tau": tau,
            "role": role,
            "null_coverage": 0.2,
            "origin_meetings": _pooled(base),
            "series": _pooled(base - 0.1),
        }

    existence = {
        "tp": 1,
        "fp": 2,
        "fn": 3,
        "precision": _prop(1, 3),
        "recall": _prop(1, 4),
        "f1": 0.4,
        "fp_breakdown": {},
    }
    accuracy = {
        "end_to_end": _prop(1, 4),
        "conditional": _prop(0, 0),
        "among_detected": _prop(1, 1),
    }
    return {
        "run_name": "a-run",
        "partition": "evaluation" if reportable else "development",
        "reportable": reportable,
        "curve": [
            entry(0.5, None, 0.2),
            entry(0.7, "principal", 0.5),
            entry(0.75, "sensitivity", 0.4),
            entry(0.8, "sensitivity", 0.3),
        ],
        "relations": {
            "tau": 0.7,
            "pooled": {
                "existence_end_to_end": existence,
                "existence_conditional": existence,
                "type_principal": accuracy,
                "type_strict": accuracy,
                "direction_principal": accuracy,
                "direction_unknown_excluded": accuracy,
            },
        },
    }


def _est(point: float) -> dict[str, Any]:
    return {
        "point": point,
        "lower": point - 0.1,
        "upper": point + 0.1,
        "n_questions": 5,
        "n_records": 15,
    }


def b_analysis(*, reportable: bool = True) -> dict[str, Any]:
    def cell(condition: str, stratum: str, base: float) -> dict[str, Any]:
        return {
            "condition": condition,
            "stratum": stratum,
            "records": 15,
            "questions": 5,
            "judge_failures": 1,
            "errors": 0,
            "below_minimum": False,
            "metrics": {
                "correct": _est(base),
                "evidence_supported": _est(base - 0.1),
                "abstention_correct": None,
                "citation_correct": _est(0.5),
                "outdated_among_answered": _est(0.2) if stratum == "E3" else None,
                "wrong_among_answered": _est(0.3) if stratum == "E3" else None,
            },
        }

    return {
        "partition": "evaluation" if reportable else "development",
        "reportable": reportable,
        "cells": [
            cell("C1", "E3", 0.3),
            cell("C2", "E3", 0.6),
            cell("C1", "ALL", 0.4),
            cell("C2", "ALL", 0.5),
        ],
        "comparisons": [
            {
                "primary": True,
                "condition_a": "C2",
                "condition_b": "C1",
                "stratum": "E3",
                "metric": "correct",
                "n_pairs": 5,
                "difference": 0.3,
                "difference_lower": 0.1,
                "difference_upper": 0.5,
                "criterion": "supported",
                "nonoverlap_criterion": "inconclusive",
            },
            {
                "primary": False,
                "condition_a": "C1",
                "condition_b": "C2",
                "stratum": "E3",
                "metric": "outdated_among_answered",
                "n_pairs": 4,
                "difference": 0.2,
                "difference_lower": -0.1,
                "difference_upper": 0.4,
                "criterion": "inconclusive",
                "nonoverlap_criterion": "inconclusive",
            },
        ],
    }


def _record(condition: str, answer: float | None, judge: float | None) -> dict[str, Any]:
    return {
        "condition": condition,
        "answer_seconds": answer,
        "judge_seconds": judge,
        "generative_model": "gen",
        "judge": {"model": "jdg"},
    }


def b_run(
    name: str,
    condition: str,
    answer: float,
    *,
    partition: str = "evaluation",
    a_run: str | None = None,
    oe4: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
) -> BRun:
    return BRun(
        name=name,
        manifest={"partition": partition, "conditions": [condition], "c2_extraction": a_run},
        records=[_record(condition, answer, 2.0), _record(condition, answer * 2, 4.0)],
        analysis=analysis if analysis is not None else b_analysis(),
        oe4=oe4,
    )


A_MANIFEST = {
    "runs": 2,
    "series": "ES2015",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:10:00+00:00",
    "openkos": {"generative_model": "gen", "versions": ["0.7.0"]},
}
OE4 = {
    "condition": "C2",
    "n_failures": 4,
    "stages": {
        "extraccion": {"cases": 1, "share": 0.25},
        "recuperacion": {"cases": 3, "share": 0.75},
    },
}


def test_a_headline_has_principal_and_sensitivities_with_intervals() -> None:
    table = a_headline_table(a_report())
    principal = table[(table["tau"] == 0.7) & (table["scope"] == "origin_meetings")].iloc[0]
    assert principal["reading"] == "principal"
    assert principal["f1"] == pytest.approx(0.7)
    assert principal["f1_lower"] == pytest.approx(0.65)
    assert set(table["tau"]) == {0.7, 0.75, 0.8}  # the unmarked grid point is not headline
    assert set(table["scope"]) == {"origin_meetings", "series"}


def test_a_relations_table_flattens_pooled_relations_and_tolerates_none() -> None:
    table = a_relations_table(a_report())
    row = table[(table["metric"] == "existence_end_to_end") & (table["view"] == "precision")]
    assert row.iloc[0]["successes"] == 1 and row.iloc[0]["trials"] == 3
    empty = table[(table["metric"] == "type_principal") & (table["view"] == "conditional")]
    assert pd.isna(empty.iloc[0]["rate"])
    assert a_relations_table({**a_report(), "relations": None}).empty


def test_b_cells_and_paired_tables_carry_the_stored_figures() -> None:
    cells = b_cells_table([("run-x", b_analysis())])
    c2 = cells[(cells["condition"] == "C2") & (cells["stratum"] == "E3")].iloc[0]
    assert c2["correct"] == pytest.approx(0.6) and c2["correct_lower"] == pytest.approx(0.5)
    assert pd.isna(c2["abstention_correct"])
    assert c2["wrong_among_answered"] == pytest.approx(0.3)  # H4 upper bound
    paired = b_paired_table([("run-x", b_analysis())])
    primary = paired[paired["primary"]].iloc[0]
    assert (primary["condition_a"], primary["condition_b"]) == ("C2", "C1")
    assert primary["criterion"] == "supported"
    assert set(paired["metric"]) == {"correct", "outdated_among_answered"}


def test_cost_tables_time_per_condition_extraction_and_break_even() -> None:
    runs = [
        b_run("c1", "C1", 10.0),  # mean answer 15 s
        b_run("c2", "C2", 2.0, a_run="a-run"),  # mean answer 3 s
    ]
    tables = cost_tables(runs, {"a-run": A_MANIFEST})
    cost = tables["cost_latency"]
    answers = cost[cost["role"] == "answer"].set_index("activity")
    assert answers.loc["c2 / C2", "mean_seconds"] == pytest.approx(3.0)
    assert set(cost["role"]) == {"answer", "judge", "extraction"}
    extraction = cost[cost["role"] == "extraction"].iloc[0]
    assert extraction["total_seconds"] == pytest.approx(600.0)
    be = tables["break_even"].iloc[0]
    assert be["structured_condition"] == "C2"
    assert be["compile_seconds"] == pytest.approx(300.0)  # 600 s over 2 runs
    assert be["break_even_queries"] == pytest.approx(300.0 / 12.0)


def test_break_even_is_none_when_structured_query_is_not_cheaper() -> None:
    runs = [b_run("c1", "C1", 2.0), b_run("c2", "C2", 10.0, a_run="a-run")]
    be = cost_tables(runs, {"a-run": A_MANIFEST})["break_even"].iloc[0]
    assert be["break_even_queries"] is None or pd.isna(be["break_even_queries"])
    assert "no existe" in be["reading"]


def test_cost_without_c1_or_manifest_has_no_break_even_rows() -> None:
    tables = cost_tables([b_run("c2", "C2", 2.0, a_run="missing")], {})
    assert tables["break_even"].empty
    assert (tables["cost_latency"]["role"] != "extraction").all()


def test_oe4_table_lists_stage_shares() -> None:
    table = oe4_table([("run-x", OE4)])
    assert list(table["stage"]) == ["extraccion", "recuperacion"]
    assert table["share"].tolist() == [0.25, 0.75]
    assert set(table["condition"]) == {"C2"}


def test_development_input_is_refused_without_the_descriptive_flag() -> None:
    inputs = FinalInputs(a_report=a_report(reportable=False), b_runs=[], a_manifests={})
    with pytest.raises(DevelopmentResultError):
        build_final_tables(inputs, descriptive=False)
    dev_b = b_run("r", "C1", 1.0, partition="development")
    with pytest.raises(DevelopmentResultError):
        build_final_tables(FinalInputs(None, [dev_b], {}), descriptive=False)


def test_descriptive_stamps_every_table_and_figure(tmp_path: Path) -> None:
    runs = [
        b_run("c1", "C1", 10.0, partition="development", analysis=b_analysis(reportable=False)),
        b_run(
            "c2",
            "C2",
            2.0,
            partition="development",
            a_run="a-run",
            oe4=OE4,
            analysis=b_analysis(reportable=False),
        ),
    ]
    inputs = FinalInputs(a_report(reportable=False), runs, {"a-run": A_MANIFEST})
    final = build_final_tables(inputs, descriptive=True)
    assert final.stamped
    assert set(final.tables) >= {
        "a-headline",
        "a-relations",
        "b-cells",
        "b-paired",
        "cost-latency",
        "break-even",
        "oe4-stages",
    }
    for frame in final.tables.values():
        if not frame.empty:
            assert (frame["status"] == STAMP).all()
    files = write_final_tables(final, "demo", tables_dir=tmp_path / "t", figures_dir=tmp_path / "f")
    names = {p.name for p in files}
    assert "demo-a-headline.csv" in names and "demo-a-headline.md" in names
    pngs = [p for p in files if p.suffix == ".png"]
    assert len(pngs) == 4
    assert all(p.read_bytes().startswith(b"\x89PNG") for p in pngs)
    assert STAMP in (tmp_path / "t" / "demo-b-cells.md").read_text(encoding="utf-8")


def test_reportable_inputs_are_not_stamped(tmp_path: Path) -> None:
    runs = [b_run("c1", "C1", 10.0), b_run("c2", "C2", 2.0, a_run="a-run", oe4=OE4)]
    final = build_final_tables(
        FinalInputs(a_report(), runs, {"a-run": A_MANIFEST}), descriptive=False
    )
    assert not final.stamped
    assert "status" not in final.tables["b-cells"].columns
    files = write_final_tables(final, "ok", tables_dir=tmp_path, figures_dir=tmp_path)
    assert STAMP not in (tmp_path / "ok-b-cells.md").read_text(encoding="utf-8")
    assert files


def _write_run_dirs(root: Path, *, partition: str) -> None:
    a_dir = root / "experiment-a" / "a-run"
    a_dir.mkdir(parents=True)
    (a_dir / "manifest.json").write_text(json.dumps(A_MANIFEST), encoding="utf-8")
    suffix = "informe.json" if partition == "evaluation" else "informe-descriptivo.json"
    reportable = partition == "evaluation"
    (a_dir / suffix).write_text(json.dumps(a_report(reportable=reportable)), encoding="utf-8")
    for name, condition in (("b-c1", "C1"), ("b-c2", "C2")):
        run = b_run(name, condition, 3.0, partition=partition, a_run="a-run", oe4=OE4)
        b_dir = root / "experiment-b" / name
        b_dir.mkdir(parents=True)
        (b_dir / "manifest.json").write_text(json.dumps(run.manifest), encoding="utf-8")
        (b_dir / "respuestas.jsonl").write_text(
            "\n".join(json.dumps(r) for r in run.records) + "\n", encoding="utf-8"
        )
        analysis_name = "analisis.json" if reportable else "analisis-descriptivo.json"
        (b_dir / analysis_name).write_text(
            json.dumps(b_analysis(reportable=reportable)), encoding="utf-8"
        )
        (b_dir / "oe4-resumen.json").write_text(json.dumps(OE4), encoding="utf-8")


def _args(out: Path) -> list[str]:
    return [
        "experiment",
        "final-tables",
        "--name",
        "demo",
        "--a-run",
        "a-run",
        "--b-run",
        "b-c1",
        "--b-run",
        "b-c2",
        "--out-dir",
        str(out),
    ]


def test_cli_writes_the_files_for_development_runs_with_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_run_dirs(tmp_path / "reports", partition="development")
    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", tmp_path / "reports" / "experiment-a")
    monkeypatch.setattr(afg_cli, "EXPERIMENT_B_DIR", tmp_path / "reports" / "experiment-b")
    out = tmp_path / "out"
    refused = CliRunner().invoke(afg_cli.app, _args(out))
    assert refused.exit_code == 1 and not out.exists()
    result = CliRunner().invoke(afg_cli.app, [*_args(out), "--descriptive"])
    assert result.exit_code == 0, result.output
    assert (out / "demo-cost-latency.csv").is_file()
    assert (out / "demo-cost-latency.png").is_file()
    assert STAMP in (out / "demo-a-headline.md").read_text(encoding="utf-8")


def test_cli_reports_a_missing_stored_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_run_dirs(tmp_path / "reports", partition="development")
    (tmp_path / "reports" / "experiment-b" / "b-c1" / "analisis-descriptivo.json").unlink()
    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", tmp_path / "reports" / "experiment-a")
    monkeypatch.setattr(afg_cli, "EXPERIMENT_B_DIR", tmp_path / "reports" / "experiment-b")
    result = CliRunner().invoke(afg_cli.app, [*_args(tmp_path / "o"), "--descriptive"])
    assert result.exit_code == 1
    assert "b-report" in result.output
