"""Tests for ``afg experiment b-report | b-sample | b-human-check`` (synthetic records)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli


def _record(q: int, condition: str, run: int, *, partition: str) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "question_id": f"ES2015.q{q:03d}",
        "condition": condition,
        "run": run,
        "stratum": "E3_evolution",
        "partition": partition,
        "trace": {"question": f"Question {q}?"},
        "answer": {"text": f"answer {q}", "abstained": False},
        "verdict": {"correct": q % 2 == 0, "evidence_supported": True},
        "judge_failure": None,
        "citation_correct": True,
        "citation_precision": 1.0,
        "error": None,
    }


def _bank() -> list[Any]:
    from afg.domain.decision import EvidenceSpan
    from afg.domain.question import Question, QuestionStratum

    return [
        Question(
            id=f"ES2015.q{q:03d}",
            series_id="ES2015",
            stratum=QuestionStratum.E3_EVOLUTION,
            text="t",
            reference_answer=f"ref {q}",
            reference_evidence=(EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("d",)),),
        )
        for q in range(10)
    ]


@pytest.fixture
def out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(afg_cli, "EXPERIMENT_B_DIR", tmp_path)
    monkeypatch.setattr(afg_cli, "load_experiment_questions", lambda path: _bank())
    monkeypatch.setattr("afg.experiments.runner.default_excerpt_for", lambda q: f"P-{q.id}")
    monkeypatch.setattr(
        "afg.evaluation.passage.transcript_files_text", lambda spans: "t/ES2015a.md"
    )
    return tmp_path


def _write_run(out: Path, name: str, partition: str) -> Path:
    run = out / name
    run.mkdir()
    lines = [
        json.dumps(_record(q, c, r, partition=partition))
        for c in ("C1", "C2")
        for q in range(10)
        for r in range(3)
    ]
    (run / "respuestas.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run


def _invoke(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["experiment", *args])


def test_report_refuses_development_records(out: Path) -> None:
    _write_run(out, "dev", "development")
    result = _invoke("b-report", "--run-name", "dev")
    assert result.exit_code == 1
    assert "descriptive" in result.output
    assert not (out / "dev" / "analisis.json").exists()


def test_descriptive_report_is_written_apart_and_marked(out: Path) -> None:
    run = _write_run(out, "dev", "development")
    result = _invoke("b-report", "--run-name", "dev", "--descriptive")
    assert result.exit_code == 0, result.output
    payload = json.loads((run / "analisis-descriptivo.json").read_text(encoding="utf-8"))
    assert payload["reportable"] is False
    assert not (run / "analisis.json").exists()


def test_report_on_evaluation_records_writes_reportable_file(out: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    result = _invoke("b-report", "--run-name", "ev")
    assert result.exit_code == 0, result.output
    payload = json.loads((run / "analisis.json").read_text(encoding="utf-8"))
    assert payload["reportable"] is True


def test_unknown_run_is_an_error(out: Path) -> None:
    result = _invoke("b-report", "--run-name", "nada")
    assert result.exit_code == 1


def test_sample_then_human_check_roundtrip(out: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    sampled = _invoke("b-sample", "--run-name", "ev", "--questions", "q.csv")
    assert sampled.exit_code == 0, sampled.output
    sheet, key = run / "muestra-juez.csv", run / "muestra-juez.clave.csv"
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    keys = {k["id"]: k for k in csv.DictReader(key.open(encoding="utf-8"))}
    assert len(rows) == 12  # ceil(0.2 * 30) per condition
    for row in rows:
        row["correct"] = keys[row["id"]]["judge_correct"]
        row["evidence_supported"] = keys[row["id"]]["judge_evidence_supported"]
    with sheet.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    checked = _invoke("b-human-check", "--run-name", "ev")
    assert checked.exit_code == 0, checked.output
    payload = json.loads((run / "juez-humano.json").read_text(encoding="utf-8"))
    assert payload["keep_automatic_judging"] is True

    again = _invoke("b-sample", "--run-name", "ev", "--questions", "q.csv")
    assert again.exit_code == 1  # would erase labels


def test_human_check_with_empty_sheet_is_an_error(out: Path) -> None:
    _write_run(out, "ev", "evaluation")
    _invoke("b-sample", "--run-name", "ev", "--questions", "q.csv")
    result = _invoke("b-human-check", "--run-name", "ev")
    assert result.exit_code == 1


def test_sample_requires_questions_so_passages_are_never_blank(out: Path) -> None:
    _write_run(out, "ev", "evaluation")
    result = CliRunner().invoke(afg_cli.app, ["experiment", "b-sample", "--run-name", "ev"])
    assert result.exit_code != 0
    assert not (out / "ev" / "muestra-juez.csv").exists()


def test_sample_passes_the_judge_passage_for_each_question(out: Path, tmp_path: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    q = tmp_path / "q.csv"
    q.write_text("x", encoding="utf-8")
    result = _invoke("b-sample", "--run-name", "ev", "--questions", str(q))
    assert result.exit_code == 0, result.output
    rows = list(csv.DictReader((run / "muestra-juez.csv").open(encoding="utf-8")))
    keys = {
        k["id"]: k for k in csv.DictReader((run / "muestra-juez.clave.csv").open(encoding="utf-8"))
    }
    for row in rows:
        assert row["pasaje_transcripcion"] == f"P-{keys[row['id']]['question_id']}"
        assert row["archivos_transcripcion"] == "t/ES2015a.md"
        assert row["reference_answer"].startswith("ref ")
