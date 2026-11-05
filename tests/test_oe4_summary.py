"""Tests for the OE4 summary of the human stage labels (issue #244). No network, no model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.experiments.c2_base_evidence import WORKSHEET_COLUMNS, write_oe4_worksheet
from afg.experiments.oe4_summary import (
    HINT_ALL_TERMS_RETRIEVED,
    HINT_ALL_TERMS_UNRETRIEVED,
    HINT_NO_TERMS,
    HINT_ONLY_RAW_SOURCE,
    OE4_SUMMARY_FILE,
    suggested_stage,
    summarize_oe4_sheet,
)

HINT_RETRIEVED = HINT_ALL_TERMS_RETRIEVED
HINT_UNRETRIEVED = HINT_ALL_TERMS_UNRETRIEVED


def _row(qid: str, hint: str, label: str) -> dict[str, str]:
    return {
        **dict.fromkeys(WORKSHEET_COLUMNS, ""),
        "pregunta_id": qid,
        "pista_automatica": hint,
        "etapa_humana": label,
    }


def test_suggested_stage_maps_each_hint_and_leaves_the_ambiguous_one_open() -> None:
    assert suggested_stage(HINT_RETRIEVED) == "sintesis"
    assert suggested_stage(HINT_UNRETRIEVED) == "recuperacion"
    assert suggested_stage(HINT_ONLY_RAW_SOURCE) == "extraccion"
    assert suggested_stage(HINT_NO_TERMS) is None
    assert suggested_stage("texto desconocido") is None


def test_summary_counts_stages_and_disagreement_with_the_rule() -> None:
    rows = [
        _row("ES2015.q1", HINT_RETRIEVED, "recuperacion"),  # rule: sintesis -> disagrees
        _row("ES2015.q2", HINT_ONLY_RAW_SOURCE, " extraccion "),  # agrees
        _row("ES2015.q3", HINT_NO_TERMS, "sintesis"),  # no suggestion
        _row("ES2015.q4", HINT_UNRETRIEVED, "recuperacion"),  # agrees
    ]
    summary = summarize_oe4_sheet(rows, condition="C2")
    assert summary.condition == "C2"
    assert summary.n_failures == 4
    assert summary.stages == {"extraccion": 1, "recuperacion": 2, "sintesis": 1}
    assert summary.shares["recuperacion"] == pytest.approx(0.5)
    assert (summary.with_suggestion, summary.agree, summary.disagree) == (3, 2, 1)
    assert summary.without_suggestion == 1
    assert [(d.question_id, d.rule_stage, d.human_stage) for d in summary.disagreements] == [
        ("ES2015.q1", "sintesis", "recuperacion")
    ]


@pytest.mark.parametrize("label", ["", "otra"])
def test_summary_rejects_unlabeled_or_unknown_labels(label: str) -> None:
    with pytest.raises(ValueError, match=r"ES2015\.q1"):
        summarize_oe4_sheet([_row("ES2015.q1", HINT_NO_TERMS, label)], condition="C2")


def test_summary_rejects_duplicated_questions() -> None:
    rows = [_row("ES2015.q1", HINT_NO_TERMS, "sintesis")] * 2
    with pytest.raises(ValueError, match="duplicad"):
        summarize_oe4_sheet(rows, condition="C2")


def test_summary_accepts_the_same_question_in_different_runs() -> None:
    rows = [
        {**_row("ES2015.q1", HINT_NO_TERMS, "sintesis"), "corrida": "0"},
        {**_row("ES2015.q1", HINT_NO_TERMS, "extraccion"), "corrida": "1"},
    ]
    summary = summarize_oe4_sheet(rows, condition="C2")
    assert summary.n_failures == 2 and summary.stages["sintesis"] == 1
    repeated = [{**rows[0]}, {**rows[0]}]
    with pytest.raises(ValueError, match="duplicad"):
        summarize_oe4_sheet(repeated, condition="C2")


def test_summary_of_an_empty_sheet_is_all_zero() -> None:
    summary = summarize_oe4_sheet([], condition="C3")
    assert summary.n_failures == 0
    assert summary.stages == {"extraccion": 0, "recuperacion": 0, "sintesis": 0}
    assert summary.agreement_rate is None


@pytest.fixture
def out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(afg_cli, "EXPERIMENT_B_DIR", tmp_path)
    return tmp_path


def _make_run(out: Path, label: str, conditions: list[str] | None = None) -> Path:
    run = out / "r1"
    run.mkdir()
    manifest: dict[str, Any] = {"conditions": conditions or ["C2"]}
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    write_oe4_worksheet(
        run / afg_cli.OE4_SHEET_FILE,
        [_row("ES2015.q1", HINT_RETRIEVED, label), _row("ES2015.q2", HINT_NO_TERMS, "sintesis")],
    )
    return run


def _invoke(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["experiment", *args], env={"COLUMNS": "200"})


def test_cli_writes_the_json_and_prints_the_table(out: Path) -> None:
    run = _make_run(out, "recuperacion")
    result = _invoke("b-oe4-summary", "--run-name", "r1")
    assert result.exit_code == 0, result.output
    data = json.loads((run / OE4_SUMMARY_FILE).read_text(encoding="utf-8"))
    assert data["condition"] == "C2"
    assert data["n_failures"] == 2
    assert data["stages"]["recuperacion"] == {"cases": 1, "share": 0.5}
    assert data["rule_agreement"]["disagree"] == 1
    assert data["disagreements"][0]["question_id"] == "ES2015.q1"
    assert "recuperacion" in result.output


def test_cli_refuses_a_half_labelled_sheet_and_writes_nothing(out: Path) -> None:
    run = _make_run(out, "")
    result = _invoke("b-oe4-summary", "--run-name", "r1")
    assert result.exit_code == 1
    assert "ES2015.q1" in result.output
    assert not (run / OE4_SUMMARY_FILE).exists()


def test_cli_reads_the_c2_sheet_of_a_multi_condition_run(out: Path) -> None:
    run = _make_run(out, "recuperacion", ["C0", "C1", "C2", "C3"])
    assert _invoke("b-oe4-summary", "--run-name", "r1").exit_code == 0
    data = json.loads((run / OE4_SUMMARY_FILE).read_text(encoding="utf-8"))
    assert data["condition"] == "C2"


def test_cli_needs_c2_in_the_manifest(out: Path) -> None:
    _make_run(out, "recuperacion", ["C1", "C3"])
    assert _invoke("b-oe4-summary", "--run-name", "r1").exit_code == 1
